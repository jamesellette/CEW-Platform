from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta

from auth import (
    User, Token, LoginRequest, UserCreate, UserRole,
    authenticate_user, create_access_token, get_current_user,
    require_role, create_user, list_users, delete_user, ACCESS_TOKEN_EXPIRE_MINUTES,
    get_user_from_token
)
from audit import (
    AuditLog, AuditAction, log_action, get_audit_logs
)
from orchestrator import orchestrator
from websocket_manager import (
    connection_manager, lab_monitor, handle_lab_websocket
)
from session_recording import session_recorder, EventType, RecordingState
from progress_tracking import progress_tracker
from marketplace import (
    marketplace, TemplateCategory, DifficultyLevel, TemplateStatus
)
from multi_user_sessions import (
    multi_user_manager, TeamRole, SessionType
)
from scheduling import (
    exercise_scheduler, ScheduleStatus, RecurrenceType, RecurrenceSettings
)
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    await lab_monitor.start()
    yield
    # Shutdown
    await lab_monitor.stop()


app = FastAPI(title="CEW Training Backend (prototype)", lifespan=lifespan)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to topology templates
TOPOLOGIES_DIR = Path(__file__).parent / "topologies"


class Scenario(BaseModel):
    id: Optional[str] = None
    name: str
    description: str = ""
    topology: dict = {}
    constraints: dict = {}
    created_by: Optional[str] = None


class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    topology: Optional[dict] = None
    constraints: Optional[dict] = None


class TopologyTemplate(BaseModel):
    filename: str
    name: str
    description: str
    node_count: int
    networks: List[str]


db: dict[str, Scenario] = {}  # in-memory store for initial prototype


def validate_air_gap(constraints: dict) -> None:
    """Validate that air-gap constraints are respected."""
    if constraints.get("allow_external_network", False):
        raise HTTPException(
            status_code=400,
            detail="External network access disabled in prototype"
        )
    if constraints.get("allow_real_rf", False):
        raise HTTPException(
            status_code=400,
            detail="Real RF transmission disabled in prototype"
        )


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/system/status")
async def system_status(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get system status overview (admin/instructor only)."""
    active_labs = orchestrator.get_active_labs()
    all_labs = orchestrator.get_all_labs()

    return {
        "status": "operational",
        "docker": {
            "available": orchestrator.docker_available,
            "mode": "docker" if orchestrator.docker_available else "simulation"
        },
        "scenarios": {
            "total": len(db),
            "active": len(active_scenarios)
        },
        "labs": {
            "total": len(all_labs),
            "active": len(active_labs),
            "total_containers": sum(len(lab.containers) for lab in active_labs),
            "total_networks": sum(len(lab.networks) for lab in active_labs)
        },
        "safety": {
            "air_gap_enforced": True,
            "external_network_blocked": True,
            "real_rf_blocked": True
        }
    }


# ============ Authentication Endpoints ============

@app.post("/auth/login", response_model=Token)
def login(login_data: LoginRequest, request: Request):
    """Authenticate user and return JWT token."""
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        log_action(
            action=AuditAction.FAILED_LOGIN,
            username=login_data.username,
            ip_address=request.client.host if request.client else None,
            success=False,
            details="Invalid credentials"
        )
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )

    log_action(
        action=AuditAction.LOGIN,
        username=user.username,
        ip_address=request.client.host if request.client else None
    )

    return Token(access_token=access_token)


@app.get("/auth/me", response_model=User)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return current_user


@app.post("/auth/register", response_model=User)
def register_user(
    user_data: UserCreate,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Register a new user (admin only)."""
    new_user = create_user(user_data)
    log_action(
        action=AuditAction.CREATE_USER,
        username=current_user.username,
        resource_type="user",
        resource_id=new_user.username,
        details=f"Created user with role: {new_user.role}"
    )
    return new_user


@app.get("/auth/users", response_model=List[User])
def get_all_users(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """List all users (admin only)."""
    return list_users()


@app.delete("/auth/users/{username}")
def remove_user(
    username: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Delete a user (admin only)."""
    if username == current_user.username:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account"
        )

    if not delete_user(username):
        raise HTTPException(status_code=404, detail="User not found")

    log_action(
        action=AuditAction.DELETE_USER,
        username=current_user.username,
        resource_type="user",
        resource_id=username,
        details=f"Deleted user: {username}"
    )
    return {"message": f"User {username} deleted successfully"}


# ============ Audit Log Endpoints ============

@app.get("/audit/logs", response_model=List[AuditLog])
def list_audit_logs(
    username: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
):
    """Get audit logs (admin/instructor only)."""
    return get_audit_logs(username=username, action=action, limit=limit)


# ============ Topology Template Endpoints ============

@app.get("/topologies", response_model=List[TopologyTemplate])
def list_topologies() -> List[TopologyTemplate]:
    """List available topology templates."""
    templates = []
    if TOPOLOGIES_DIR.exists():
        for filepath in TOPOLOGIES_DIR.glob("*.json"):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                templates.append(TopologyTemplate(
                    filename=filepath.name,
                    name=data.get("name", filepath.stem),
                    description=data.get("description", ""),
                    node_count=len(data.get("nodes", [])),
                    networks=[n.get("name", "") for n in data.get("networks", [])]
                ))
            except (json.JSONDecodeError, KeyError):
                continue
    return templates


@app.get("/topologies/{filename}")
def get_topology(filename: str) -> dict:
    """Get a specific topology template."""
    # Prevent path traversal attacks
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = TOPOLOGIES_DIR / filename
    if not filepath.exists() or not filepath.suffix == ".json":
        raise HTTPException(status_code=404, detail="Topology not found")

    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid topology file")


# ============ Scenario Endpoints ============

@app.post("/scenarios", response_model=Scenario)
def create_scenario(s: Scenario) -> Scenario:
    s.id = str(uuid.uuid4())
    validate_air_gap(s.constraints)
    db[s.id] = s
    return s


@app.get("/scenarios", response_model=List[Scenario])
def list_scenarios() -> List[Scenario]:
    return list(db.values())


@app.get("/scenarios/active")
def list_active_scenarios(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> List[dict]:
    """List all currently active scenarios (instructor/admin only)."""
    return list(active_scenarios.values())


@app.get("/scenarios/{scenario_id}", response_model=Scenario)
def get_scenario(scenario_id: str) -> Scenario:
    s = db.get(scenario_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return s


@app.put("/scenarios/{scenario_id}", response_model=Scenario)
def update_scenario(scenario_id: str, update: ScenarioUpdate) -> Scenario:
    """Update an existing scenario."""
    s = db.get(scenario_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Check for air-gap constraints
    if update.constraints:
        validate_air_gap(update.constraints)

    # Update fields if provided
    if update.name is not None:
        s.name = update.name
    if update.description is not None:
        s.description = update.description
    if update.topology is not None:
        s.topology = update.topology
    if update.constraints is not None:
        s.constraints = update.constraints

    db[scenario_id] = s
    return s


@app.delete("/scenarios/{scenario_id}")
def delete_scenario(scenario_id: str) -> dict:
    """Delete a scenario."""
    if scenario_id not in db:
        raise HTTPException(status_code=404, detail="Scenario not found")
    del db[scenario_id]
    return {"message": "Scenario deleted successfully"}


# ============ Scenario Export/Import Endpoints ============

@app.get("/scenarios/{scenario_id}/export")
def export_scenario(
    scenario_id: str,
    format: str = "json"
) -> Response:
    """Export a scenario as JSON or YAML."""
    s = db.get(scenario_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")

    scenario_data = s.model_dump()

    if format.lower() == "yaml":
        content = yaml.dump(scenario_data, default_flow_style=False, allow_unicode=True)
        return Response(
            content=content,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": f'attachment; filename="{s.name}.yaml"'
            }
        )
    else:
        content = json.dumps(scenario_data, indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{s.name}.json"'
            }
        )


class ScenarioImport(BaseModel):
    content: str
    format: str = "json"


@app.post("/scenarios/import", response_model=Scenario)
def import_scenario(import_data: ScenarioImport) -> Scenario:
    """Import a scenario from JSON or YAML content."""
    try:
        if import_data.format.lower() == "yaml":
            scenario_data = yaml.safe_load(import_data.content)
        else:
            scenario_data = json.loads(import_data.content)
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {import_data.format.upper()} format: {str(e)}"
        )

    # Validate required fields
    if "name" not in scenario_data:
        raise HTTPException(status_code=400, detail="Scenario must have a name")

    # Create new scenario with fresh ID
    s = Scenario(
        id=str(uuid.uuid4()),
        name=scenario_data.get("name"),
        description=scenario_data.get("description", ""),
        topology=scenario_data.get("topology", {}),
        constraints=scenario_data.get("constraints", {}),
        created_by=scenario_data.get("created_by")
    )

    # Validate air-gap constraints
    validate_air_gap(s.constraints)

    db[s.id] = s
    return s


# ============ Kill Switch / Emergency Controls ============

# Track active scenarios (in production, this would be in Redis or similar)
active_scenarios: dict[str, dict] = {}
# Reverse mapping from lab_id to scenario_id for O(1) lookup
lab_to_scenario: dict[str, str] = {}


class ScenarioActivation(BaseModel):
    scenario_id: str
    activated_by: Optional[str] = None


class LabInfo(BaseModel):
    """Lab environment information."""
    lab_id: str
    scenario_id: str
    scenario_name: str
    activated_by: str
    status: str
    container_count: int
    network_count: int
    started_at: Optional[str] = None


@app.post("/scenarios/{scenario_id}/activate")
async def activate_scenario(
    scenario_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Activate a scenario for training (instructor/admin only)."""
    s = db.get(scenario_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")

    if scenario_id in active_scenarios:
        raise HTTPException(status_code=400, detail="Scenario is already active")

    try:
        # Create lab environment using orchestrator
        lab = await orchestrator.create_lab(
            scenario_id=scenario_id,
            scenario_name=s.name,
            topology=s.topology,
            constraints=s.constraints,
            activated_by=current_user.username
        )

        active_scenarios[scenario_id] = {
            "scenario_id": scenario_id,
            "scenario_name": s.name,
            "activated_by": current_user.username,
            "status": "active",
            "lab_id": lab.lab_id
        }
        # Add reverse mapping for O(1) lookup
        lab_to_scenario[lab.lab_id] = scenario_id

        log_action(
            action=AuditAction.ACTIVATE_SCENARIO,
            username=current_user.username,
            resource_type="scenario",
            resource_id=scenario_id,
            details=f"Activated scenario: {s.name} (lab_id: {lab.lab_id})"
        )

        return {
            "message": f"Scenario '{s.name}' activated",
            "status": "active",
            "lab_id": lab.lab_id,
            "containers": len(lab.containers),
            "networks": len(lab.networks)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/scenarios/{scenario_id}/deactivate")
async def deactivate_scenario(
    scenario_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Deactivate a running scenario (instructor/admin only)."""
    if scenario_id not in active_scenarios:
        raise HTTPException(status_code=400, detail="Scenario is not active")

    scenario_info = active_scenarios.pop(scenario_id)

    # Stop the lab if it has one
    if "lab_id" in scenario_info:
        lab_id = scenario_info["lab_id"]
        # Clean up reverse mapping
        lab_to_scenario.pop(lab_id, None)
        try:
            await orchestrator.stop_lab(lab_id)
        except Exception as e:
            # Log error but don't fail - scenario is already deactivated
            log_action(
                action=AuditAction.DEACTIVATE_SCENARIO,
                username=current_user.username,
                resource_type="scenario",
                resource_id=scenario_id,
                details=f"Warning: Failed to stop lab: {e}",
                success=False
            )

    log_action(
        action=AuditAction.DEACTIVATE_SCENARIO,
        username=current_user.username,
        resource_type="scenario",
        resource_id=scenario_id,
        details=f"Deactivated scenario: {scenario_info['scenario_name']}"
    )

    return {"message": "Scenario deactivated", "status": "inactive"}


@app.post("/kill-switch")
async def emergency_kill_switch(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Emergency kill switch - deactivate ALL active scenarios immediately."""
    deactivated_count = len(active_scenarios)
    deactivated_scenarios = list(active_scenarios.keys())

    # Stop all labs via orchestrator
    stopped_labs = await orchestrator.kill_all_labs(current_user.username)

    # Clear all active scenarios and reverse mapping
    active_scenarios.clear()
    lab_to_scenario.clear()

    log_action(
        action=AuditAction.KILL_SWITCH,
        username=current_user.username,
        resource_type="system",
        details=(
            f"Emergency kill switch activated. Deactivated {deactivated_count} scenarios, "
            f"stopped {len(stopped_labs)} labs."
        )
    )

    return {
        "message": "Emergency kill switch activated",
        "deactivated_count": deactivated_count,
        "deactivated_scenarios": deactivated_scenarios,
        "stopped_labs": stopped_labs
    }


# ============ Lab Management Endpoints ============

@app.get("/labs", response_model=List[LabInfo])
async def list_labs(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> List[LabInfo]:
    """List all lab environments (active and stopped)."""
    labs = orchestrator.get_all_labs()
    return [
        LabInfo(
            lab_id=lab.lab_id,
            scenario_id=lab.scenario_id,
            scenario_name=lab.scenario_name,
            activated_by=lab.activated_by,
            status=lab.status.value,
            container_count=len(lab.containers),
            network_count=len(lab.networks),
            started_at=lab.started_at.isoformat() if lab.started_at else None
        )
        for lab in labs
    ]


@app.get("/labs/active", response_model=List[LabInfo])
async def list_active_labs(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> List[LabInfo]:
    """List all currently active lab environments."""
    labs = orchestrator.get_active_labs()
    return [
        LabInfo(
            lab_id=lab.lab_id,
            scenario_id=lab.scenario_id,
            scenario_name=lab.scenario_name,
            activated_by=lab.activated_by,
            status=lab.status.value,
            container_count=len(lab.containers),
            network_count=len(lab.networks),
            started_at=lab.started_at.isoformat() if lab.started_at else None
        )
        for lab in labs
    ]


@app.get("/labs/{lab_id}")
async def get_lab(
    lab_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get detailed information about a specific lab."""
    lab = orchestrator.get_lab(lab_id)
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    return {
        "lab_id": lab.lab_id,
        "scenario_id": lab.scenario_id,
        "scenario_name": lab.scenario_name,
        "activated_by": lab.activated_by,
        "status": lab.status.value,
        "started_at": lab.started_at.isoformat() if lab.started_at else None,
        "error_message": lab.error_message,
        "containers": [
            {
                "container_id": c.container_id,
                "node_id": c.node_id,
                "hostname": c.hostname,
                "image": c.image,
                "ip_address": c.ip_address,
                "status": c.status
            }
            for c in lab.containers
        ],
        "networks": [
            {
                "network_id": n.network_id,
                "name": n.name,
                "subnet": n.subnet,
                "isolated": n.isolated
            }
            for n in lab.networks
        ]
    }


@app.post("/labs/{lab_id}/stop")
async def stop_lab(
    lab_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Stop a specific lab environment."""
    try:
        lab = await orchestrator.stop_lab(lab_id)

        # Also remove from active scenarios using O(1) reverse lookup
        scenario_id = lab_to_scenario.pop(lab_id, None)
        if scenario_id:
            active_scenarios.pop(scenario_id, None)

        log_action(
            action=AuditAction.DEACTIVATE_SCENARIO,
            username=current_user.username,
            resource_type="lab",
            resource_id=lab_id,
            details=f"Stopped lab for scenario: {lab.scenario_name}"
        )

        return {
            "message": "Lab stopped successfully",
            "lab_id": lab_id,
            "status": lab.status.value
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/labs/{lab_id}/health")
async def get_lab_health(
    lab_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get health status of all containers in a lab."""
    try:
        health = await orchestrator.get_container_health(lab_id)
        return {
            "lab_id": lab_id,
            "docker_mode": orchestrator.docker_available,
            "containers": health
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/labs/{lab_id}/resources")
async def get_lab_resources(
    lab_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get resource usage for all containers in a lab."""
    try:
        usage = orchestrator.get_resource_usage(lab_id)
        return {
            "lab_id": lab_id,
            "docker_mode": orchestrator.docker_available,
            "containers": usage
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/labs/{lab_id}/recover")
async def recover_lab_containers(
    lab_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Attempt to restart unhealthy containers in a lab (auto-recovery)."""
    try:
        restarted = await orchestrator.restart_unhealthy_containers(lab_id)
        log_action(
            action=AuditAction.LAB_RECOVERY,
            username=current_user.username,
            resource_type="lab",
            resource_id=lab_id,
            details=f"Auto-recovery: restarted {len(restarted)} containers"
        )
        return {
            "lab_id": lab_id,
            "docker_mode": orchestrator.docker_available,
            "restarted_containers": restarted,
            "count": len(restarted)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ WebSocket Endpoints for Real-Time Monitoring ============

@app.websocket("/ws/labs/{lab_id}")
async def websocket_lab_monitor(websocket: WebSocket, lab_id: str):
    """
    WebSocket endpoint for real-time lab monitoring.

    Clients should send a token query parameter or authenticate first.
    Sends periodic updates with container health and resource usage.
    """
    # Get token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    # Validate token
    user = get_user_from_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Check role permissions
    if user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        await websocket.close(code=4003, reason="Insufficient permissions")
        return

    # Handle the WebSocket connection
    await handle_lab_websocket(websocket, lab_id, user.username)


@app.get("/ws/status")
async def websocket_status(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get WebSocket connection status for monitoring."""
    return {
        "connected_labs": connection_manager.get_connected_labs(),
        "total_connections": connection_manager.get_connection_count()
    }


# ============ Session Recording Endpoints ============

class RecordingStartRequest(BaseModel):
    """Request to start a recording session."""
    lab_id: str
    scenario_id: str
    scenario_name: str
    metadata: Optional[dict] = None


class RecordEventRequest(BaseModel):
    """Request to record an event."""
    event_type: str
    container_id: Optional[str] = None
    hostname: Optional[str] = None
    data: Optional[dict] = None


class CommandEventRequest(BaseModel):
    """Request to record a command execution."""
    container_id: str
    hostname: str
    command: str
    output: str
    exit_code: int
    duration_ms: int


@app.post("/recordings/start")
async def start_recording(
    request: RecordingStartRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Start a new recording session for a lab."""
    try:
        session = await session_recorder.start_recording(
            lab_id=request.lab_id,
            scenario_id=request.scenario_id,
            scenario_name=request.scenario_name,
            username=current_user.username,
            metadata=request.metadata
        )

        log_action(
            action=AuditAction.ACTIVATE_SCENARIO,
            username=current_user.username,
            resource_type="recording",
            resource_id=session.session_id,
            details=f"Started recording for lab {request.lab_id}"
        )

        return session.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/recordings/{session_id}/stop")
async def stop_recording(
    session_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Stop a recording session."""
    try:
        session = await session_recorder.stop_recording(session_id)

        log_action(
            action=AuditAction.DEACTIVATE_SCENARIO,
            username=current_user.username,
            resource_type="recording",
            resource_id=session_id,
            details=f"Stopped recording (duration: {session.get_duration():.1f}s)"
        )

        return session.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/recordings/{session_id}/pause")
async def pause_recording(
    session_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Pause a recording session."""
    try:
        session = await session_recorder.pause_recording(session_id)
        return session.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/recordings/{session_id}/resume")
async def resume_recording(
    session_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Resume a paused recording session."""
    try:
        session = await session_recorder.resume_recording(session_id)
        return session.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/recordings/labs/{lab_id}/events")
async def record_event(
    lab_id: str,
    request: RecordEventRequest,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Record an event for a lab's active session."""
    try:
        event_type = EventType(request.event_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type: {request.event_type}"
        )

    event = await session_recorder.record_event(
        lab_id=lab_id,
        event_type=event_type,
        container_id=request.container_id,
        hostname=request.hostname,
        data=request.data
    )

    if event:
        return event.to_dict()
    return {"message": "No active recording for this lab"}


@app.post("/recordings/labs/{lab_id}/commands")
async def record_command(
    lab_id: str,
    request: CommandEventRequest,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Record a command execution for a lab's active session."""
    event = await session_recorder.record_command(
        lab_id=lab_id,
        container_id=request.container_id,
        hostname=request.hostname,
        command=request.command,
        output=request.output,
        exit_code=request.exit_code,
        duration_ms=request.duration_ms
    )

    if event:
        return event.to_dict()
    return {"message": "No active recording for this lab"}


@app.get("/recordings")
async def list_recordings(
    username: Optional[str] = None,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> List[dict]:
    """List all recording sessions."""
    if username:
        sessions = session_recorder.get_sessions_for_user(username)
    else:
        sessions = session_recorder.get_all_sessions()

    return [s.to_dict() for s in sessions]


@app.get("/recordings/{session_id}")
async def get_recording(
    session_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get a recording session details."""
    session = session_recorder.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Recording not found")

    return session.to_dict()


@app.get("/recordings/{session_id}/summary")
async def get_recording_summary(
    session_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get a summary of a recording session."""
    summary = session_recorder.get_session_summary(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Recording not found")

    return summary


@app.get("/recordings/{session_id}/events")
async def get_recording_events(
    session_id: str,
    event_types: Optional[str] = None,
    limit: int = 1000,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> List[dict]:
    """Get events from a recording session."""
    # Parse event types filter
    filter_types = None
    if event_types:
        try:
            filter_types = [EventType(t.strip()) for t in event_types.split(",")]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {e}")

    events = session_recorder.get_session_events(
        session_id=session_id,
        event_types=filter_types,
        limit=limit
    )

    return [e.to_dict() for e in events]


@app.get("/recordings/{session_id}/playback")
async def get_playback_data(
    session_id: str,
    speed: float = 1.0,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get recording data formatted for playback."""
    session = session_recorder.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Recording not found")

    if session.state not in [RecordingState.STOPPED, RecordingState.PAUSED]:
        raise HTTPException(
            status_code=400,
            detail="Cannot playback an active recording"
        )

    events = session_recorder.get_playback_events(session_id, speed)

    return {
        "session": session.to_dict(),
        "events": events,
        "playback_speed": speed,
        "total_duration_ms": events[-1]["elapsed_ms"] if events else 0
    }


@app.get("/recordings/labs/{lab_id}/current")
async def get_current_recording(
    lab_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get the current recording session for a lab."""
    session = session_recorder.get_session_for_lab(lab_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="No active recording for this lab"
        )

    return session.to_dict()


# ============ Progress Tracking Endpoints ============


class StartExerciseRequest(BaseModel):
    """Request to start tracking an exercise."""
    exercise_id: str
    exercise_name: str
    scenario_id: str
    objectives_total: int = 0
    max_score: float = 100.0


class CompleteObjectiveRequest(BaseModel):
    """Request to complete an objective."""
    objective_id: str
    points_earned: float = 0


class CompleteExerciseRequest(BaseModel):
    """Request to complete an exercise."""
    final_score: Optional[float] = None
    notes: str = ""


class AssessSkillRequest(BaseModel):
    """Request to assess a skill."""
    skill_name: str
    skill_category: str
    experience_gained: int = 0


@app.post("/progress/exercises/start")
async def start_exercise_progress(
    request: StartExerciseRequest,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Start tracking progress for an exercise."""
    progress = progress_tracker.start_exercise(
        username=current_user.username,
        exercise_id=request.exercise_id,
        exercise_name=request.exercise_name,
        scenario_id=request.scenario_id,
        objectives_total=request.objectives_total,
        max_score=request.max_score
    )
    return progress.to_dict()


@app.post("/progress/exercises/{progress_id}/objectives")
async def complete_objective(
    progress_id: str,
    request: CompleteObjectiveRequest,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Mark an objective as completed."""
    progress = progress_tracker.complete_objective(
        progress_id=progress_id,
        objective_id=request.objective_id,
        points_earned=request.points_earned
    )
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    return progress.to_dict()


@app.post("/progress/exercises/{progress_id}/complete")
async def complete_exercise_progress(
    progress_id: str,
    request: CompleteExerciseRequest,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Mark an exercise as completed."""
    progress = progress_tracker.complete_exercise(
        progress_id=progress_id,
        final_score=request.final_score,
        notes=request.notes
    )
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    return progress.to_dict()


@app.post("/progress/exercises/{progress_id}/fail")
async def fail_exercise_progress(
    progress_id: str,
    notes: str = "",
    current_user: User = Depends(get_current_user)
) -> dict:
    """Mark an exercise as failed."""
    progress = progress_tracker.fail_exercise(progress_id, notes)
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    return progress.to_dict()


@app.post("/progress/exercises/{progress_id}/hint")
async def record_hint_used(
    progress_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Record that a hint was used."""
    progress = progress_tracker.add_hint_used(progress_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    return progress.to_dict()


@app.get("/progress/exercises/{progress_id}")
async def get_exercise_progress(
    progress_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get exercise progress by ID."""
    progress = progress_tracker.get_exercise_progress(progress_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    return progress.to_dict()


@app.get("/progress/me")
async def get_my_progress(
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get current user's exercise progress."""
    progress_list = progress_tracker.get_user_progress(current_user.username)
    return [p.to_dict() for p in progress_list]


@app.get("/progress/me/report")
async def get_my_progress_report(
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get comprehensive progress report for current user."""
    return progress_tracker.get_progress_report(current_user.username)


@app.get("/progress/users/{username}")
async def get_user_progress(
    username: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> List[dict]:
    """Get a user's exercise progress (admin/instructor only)."""
    progress_list = progress_tracker.get_user_progress(username)
    return [p.to_dict() for p in progress_list]


@app.get("/progress/users/{username}/report")
async def get_user_progress_report(
    username: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get comprehensive progress report for a user (admin/instructor only)."""
    return progress_tracker.get_progress_report(username)


@app.post("/progress/skills/assess")
async def assess_skill(
    request: AssessSkillRequest,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Assess and update skill level."""
    assessment = progress_tracker.assess_skill(
        username=current_user.username,
        skill_name=request.skill_name,
        skill_category=request.skill_category,
        experience_gained=request.experience_gained
    )
    return assessment.to_dict()


@app.get("/progress/skills/{username}")
async def get_user_skills(
    username: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get a user's skill assessments (admin/instructor only)."""
    profile = progress_tracker.get_profile(username)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {k: v.to_dict() for k, v in profile.skills.items()}


@app.get("/progress/leaderboard")
async def get_leaderboard(
    metric: str = "score",
    limit: int = 10,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get the leaderboard."""
    if metric not in ["score", "exercises", "time"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid metric. Use 'score', 'exercises', or 'time'"
        )
    return progress_tracker.get_leaderboard(metric, limit)


@app.get("/progress/badges")
async def get_available_badges(
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get all available badges."""
    return progress_tracker.get_available_badges()


@app.get("/progress/skill-categories")
async def get_skill_categories(
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get all skill categories and skills."""
    return progress_tracker.get_skill_categories()


@app.get("/progress/profiles")
async def get_all_profiles(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> List[dict]:
    """Get all trainee profiles (admin/instructor only)."""
    profiles = progress_tracker.get_all_profiles()
    return [p.to_dict() for p in profiles]


# ============ Marketplace Endpoints ============

class CreateTemplateRequest(BaseModel):
    """Request to create a new template."""
    name: str
    description: str
    category: str
    difficulty: str
    tags: List[str] = []
    estimated_duration_minutes: int = 30
    prerequisites: List[str] = []
    learning_objectives: List[str] = []


class AddVersionRequest(BaseModel):
    """Request to add a new template version."""
    version: str
    changelog: str
    scenario_data: dict


class AddReviewRequest(BaseModel):
    """Request to add a review."""
    rating: int
    title: str
    comment: str


class UpdateTemplateRequest(BaseModel):
    """Request to update template metadata."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None
    estimated_duration_minutes: Optional[int] = None
    prerequisites: Optional[List[str]] = None
    learning_objectives: Optional[List[str]] = None


@app.post("/marketplace/templates")
async def create_template(
    request: CreateTemplateRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Create a new template (as draft)."""
    try:
        category = TemplateCategory(request.category)
        difficulty = DifficultyLevel(request.difficulty)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    template = marketplace.create_template(
        name=request.name,
        description=request.description,
        author=current_user.username,
        category=category,
        difficulty=difficulty,
        tags=request.tags,
        estimated_duration_minutes=request.estimated_duration_minutes,
        prerequisites=request.prerequisites,
        learning_objectives=request.learning_objectives
    )
    return template.to_dict()


@app.get("/marketplace/templates")
async def list_templates(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    tags: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """List published templates with optional filters."""
    cat = TemplateCategory(category) if category else None
    diff = DifficultyLevel(difficulty) if difficulty else None
    tag_list = tags.split(",") if tags else None

    templates = marketplace.list_templates(
        category=cat,
        difficulty=diff,
        tags=tag_list,
        search_query=search
    )
    return [t.to_dict() for t in templates]


@app.get("/marketplace/templates/popular")
async def get_popular_templates(
    limit: int = 10,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get most downloaded templates."""
    templates = marketplace.get_popular_templates(limit)
    return [t.to_dict() for t in templates]


@app.get("/marketplace/templates/top-rated")
async def get_top_rated_templates(
    limit: int = 10,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get highest rated templates."""
    templates = marketplace.get_top_rated_templates(limit)
    return [t.to_dict() for t in templates]


@app.get("/marketplace/templates/recent")
async def get_recent_templates(
    limit: int = 10,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get recently updated templates."""
    templates = marketplace.get_recent_templates(limit)
    return [t.to_dict() for t in templates]


@app.get("/marketplace/templates/{template_id}")
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get a template by ID."""
    template = marketplace.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template.to_dict(include_reviews=True, include_versions=True)


@app.put("/marketplace/templates/{template_id}")
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Update template metadata."""
    template = marketplace.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Only author or admin can update
    if template.author != current_user.username and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this template")

    category = TemplateCategory(request.category) if request.category else None
    difficulty = DifficultyLevel(request.difficulty) if request.difficulty else None

    updated = marketplace.update_template(
        template_id=template_id,
        name=request.name,
        description=request.description,
        category=category,
        difficulty=difficulty,
        tags=request.tags,
        estimated_duration_minutes=request.estimated_duration_minutes,
        prerequisites=request.prerequisites,
        learning_objectives=request.learning_objectives
    )
    return updated.to_dict()


@app.delete("/marketplace/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Delete a template (admin only)."""
    if not marketplace.delete_template(template_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete template (not found or built-in)"
        )
    return {"message": "Template deleted"}


@app.post("/marketplace/templates/{template_id}/versions")
async def add_template_version(
    template_id: str,
    request: AddVersionRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Add a new version to a template."""
    template = marketplace.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Only author or admin can add versions
    if template.author != current_user.username and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        version = marketplace.add_version(
            template_id=template_id,
            version=request.version,
            changelog=request.changelog,
            scenario_data=request.scenario_data,
            created_by=current_user.username
        )
        return version.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/marketplace/templates/{template_id}/versions/{version}")
async def get_template_version(
    template_id: str,
    version: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get a specific template version."""
    version_obj = marketplace.get_version(template_id, version)
    if not version_obj:
        raise HTTPException(status_code=404, detail="Version not found")
    return version_obj.to_dict()


@app.post("/marketplace/templates/{template_id}/submit")
async def submit_template_for_review(
    template_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Submit a template for review."""
    template = marketplace.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.author != current_user.username and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        updated = marketplace.submit_for_review(template_id)
        return updated.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/marketplace/templates/{template_id}/approve")
async def approve_template(
    template_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Approve and publish a template (admin only)."""
    try:
        template = marketplace.approve_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/marketplace/templates/{template_id}/reject")
async def reject_template(
    template_id: str,
    reason: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Reject a template (admin only)."""
    try:
        template = marketplace.reject_template(template_id, reason)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/marketplace/templates/{template_id}/deprecate")
async def deprecate_template(
    template_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Mark a template as deprecated (admin only)."""
    template = marketplace.deprecate_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template.to_dict()


@app.post("/marketplace/templates/{template_id}/reviews")
async def add_review(
    template_id: str,
    request: AddReviewRequest,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Add a review to a template."""
    try:
        review = marketplace.add_review(
            template_id=template_id,
            username=current_user.username,
            rating=request.rating,
            title=request.title,
            comment=request.comment
        )
        if not review:
            raise HTTPException(status_code=404, detail="Template not found")
        return review.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/marketplace/templates/{template_id}/reviews/{review_id}/helpful")
async def vote_review_helpful(
    template_id: str,
    review_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Vote a review as helpful."""
    review = marketplace.vote_helpful(template_id, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review.to_dict()


@app.post("/marketplace/templates/{template_id}/download")
async def download_template(
    template_id: str,
    version: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Download/use a template to create a scenario."""
    try:
        result = marketplace.download_template(template_id, version)
        if not result:
            raise HTTPException(status_code=404, detail="Template or version not found")

        log_action(
            action=AuditAction.VIEW_SCENARIO,
            username=current_user.username,
            resource_type="template",
            resource_id=template_id,
            details=f"Downloaded template version {result['version']}"
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/marketplace/categories")
async def get_categories(
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get all template categories with counts."""
    return marketplace.get_categories()


@app.get("/marketplace/statistics")
async def get_marketplace_statistics(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get marketplace statistics."""
    return marketplace.get_statistics()


@app.get("/marketplace/my-templates")
async def get_my_templates(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> List[dict]:
    """Get templates created by the current user."""
    # Get all templates for this author (including drafts and pending)
    all_templates = [
        t for t in marketplace._templates.values()
        if t.author == current_user.username
    ]
    return [t.to_dict() for t in all_templates]


@app.get("/marketplace/pending")
async def get_pending_templates(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> List[dict]:
    """Get templates pending review (admin only)."""
    templates = marketplace.list_templates(status=TemplateStatus.PENDING_REVIEW)
    return [t.to_dict() for t in templates]


# ============ Multi-User Session Endpoints ============


class CreateSessionRequest(BaseModel):
    """Request to create a multi-user session."""
    name: str
    description: str
    lab_id: str
    scenario_id: str
    session_type: str
    max_participants: int = 10
    settings: Optional[dict] = None


class AddParticipantRequest(BaseModel):
    """Request to add a participant."""
    username: str
    display_name: str
    team_role: str
    permissions: Optional[dict] = None


class SendMessageRequest(BaseModel):
    """Request to send a chat message."""
    content: str
    is_team_only: bool = False


class AddObjectiveRequest(BaseModel):
    """Request to add an objective."""
    name: str
    description: str
    points: int
    team_role: Optional[str] = None


@app.post("/sessions")
async def create_multi_user_session(
    request: CreateSessionRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Create a new multi-user session."""
    try:
        session_type = SessionType(request.session_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session type")

    try:
        session = multi_user_manager.create_session(
            name=request.name,
            description=request.description,
            lab_id=request.lab_id,
            scenario_id=request.scenario_id,
            session_type=session_type,
            host_username=current_user.username,
            max_participants=request.max_participants,
            settings=request.settings
        )
        return session.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/sessions")
async def list_multi_user_sessions(
    session_type: Optional[str] = None,
    active_only: bool = True,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """List multi-user sessions."""
    stype = SessionType(session_type) if session_type else None
    sessions = multi_user_manager.list_sessions(
        session_type=stype,
        active_only=active_only
    )
    return [s.to_dict() for s in sessions]


@app.get("/sessions/me")
async def get_my_sessions(
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get sessions the current user is participating in."""
    sessions = multi_user_manager.get_user_sessions(current_user.username)
    return [s.to_dict() for s in sessions]


@app.get("/sessions/{session_id}")
async def get_multi_user_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get a multi-user session by ID."""
    session = multi_user_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict(include_chat=True)


@app.post("/sessions/{session_id}/start")
async def start_multi_user_session(
    session_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Start a multi-user session."""
    session = multi_user_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.host_username != current_user.username and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only host or admin can start session")

    updated = multi_user_manager.start_session(session_id)
    return updated.to_dict()


@app.post("/sessions/{session_id}/end")
async def end_multi_user_session(
    session_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """End a multi-user session."""
    session = multi_user_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.host_username != current_user.username and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only host or admin can end session")

    updated = multi_user_manager.end_session(session_id)
    return updated.to_dict()


@app.delete("/sessions/{session_id}")
async def delete_multi_user_session(
    session_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Delete a multi-user session (admin only)."""
    if not multi_user_manager.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}


@app.post("/sessions/{session_id}/participants")
async def add_session_participant(
    session_id: str,
    request: AddParticipantRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Add a participant to a session."""
    try:
        team_role = TeamRole(request.team_role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team role")

    try:
        participant = multi_user_manager.add_participant(
            session_id=session_id,
            username=request.username,
            display_name=request.display_name,
            team_role=team_role,
            permissions=request.permissions
        )
        if not participant:
            raise HTTPException(status_code=404, detail="Session not found")
        return participant.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sessions/{session_id}/join")
async def join_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Join a session as the current user."""
    participant = multi_user_manager.join_session(session_id, current_user.username)
    if not participant:
        raise HTTPException(status_code=404, detail="Not a participant in this session")
    return participant.to_dict()


@app.post("/sessions/{session_id}/leave")
async def leave_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Leave a session."""
    participant = multi_user_manager.leave_session(session_id, current_user.username)
    if not participant:
        raise HTTPException(status_code=404, detail="Not a participant in this session")
    return participant.to_dict()


@app.delete("/sessions/{session_id}/participants/{participant_id}")
async def remove_session_participant(
    session_id: str,
    participant_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Remove a participant from a session."""
    if not multi_user_manager.remove_participant(session_id, participant_id):
        raise HTTPException(status_code=404, detail="Participant not found")
    return {"message": "Participant removed"}


@app.post("/sessions/{session_id}/teams")
async def create_session_team(
    session_id: str,
    name: str,
    role: str,
    color: str = "#6c757d",
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Create a custom team in a session."""
    try:
        team_role = TeamRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team role")

    team = multi_user_manager.create_team(session_id, name, team_role, color)
    if not team:
        raise HTTPException(status_code=404, detail="Session not found")
    return team.to_dict()


@app.post("/sessions/{session_id}/teams/{team_id}/assign/{participant_id}")
async def assign_participant_to_team(
    session_id: str,
    team_id: str,
    participant_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Assign a participant to a team."""
    if not multi_user_manager.assign_to_team(session_id, participant_id, team_id):
        raise HTTPException(status_code=404, detail="Session, team, or participant not found")
    return {"message": "Participant assigned to team"}


@app.post("/sessions/{session_id}/teams/{team_id}/score")
async def update_team_score(
    session_id: str,
    team_id: str,
    points: int,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Update a team's score."""
    team = multi_user_manager.update_team_score(session_id, team_id, points)
    if not team:
        raise HTTPException(status_code=404, detail="Session or team not found")
    return team.to_dict()


@app.post("/sessions/{session_id}/objectives")
async def add_session_objective(
    session_id: str,
    request: AddObjectiveRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Add an objective to a session."""
    team_role = TeamRole(request.team_role) if request.team_role else None

    objective = multi_user_manager.add_objective(
        session_id=session_id,
        name=request.name,
        description=request.description,
        points=request.points,
        team_role=team_role
    )
    if not objective:
        raise HTTPException(status_code=404, detail="Session not found")
    return objective.to_dict()


@app.post("/sessions/{session_id}/objectives/{objective_id}/complete")
async def complete_session_objective(
    session_id: str,
    objective_id: str,
    team_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Mark an objective as completed."""
    try:
        objective = multi_user_manager.complete_objective(session_id, objective_id, team_id)
        if not objective:
            raise HTTPException(status_code=404, detail="Objective not found")
        return objective.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/sessions/{session_id}/messages")
async def send_session_message(
    session_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Send a chat message in a session."""
    message = multi_user_manager.send_message(
        session_id=session_id,
        sender_username=current_user.username,
        sender_display_name=current_user.username,
        content=request.content,
        is_team_only=request.is_team_only
    )
    if not message:
        raise HTTPException(status_code=404, detail="Session not found")
    return message.to_dict()


@app.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = 50,
    after: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get chat messages from a session."""
    messages = multi_user_manager.get_messages(
        session_id=session_id,
        username=current_user.username,
        limit=limit,
        after=after
    )
    return [m.to_dict() for m in messages]


@app.get("/sessions/{session_id}/scores")
async def get_session_scores(
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get current scores for all teams in a session."""
    session = multi_user_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "teams": [t.to_dict() for t in session.teams.values()],
        "objectives": [o.to_dict() for o in session.objectives]
    }


# ============ Scheduling Endpoints ============

class RecurrenceSettingsModel(BaseModel):
    """Recurrence settings for a schedule."""
    recurrence_type: str
    interval: int = 1
    days_of_week: List[int] = []
    end_date: Optional[str] = None
    max_occurrences: Optional[int] = None


class CreateScheduleRequest(BaseModel):
    """Request to create a scheduled exercise."""
    title: str
    description: str
    scenario_id: str
    scenario_name: str
    start_time: str  # ISO format
    end_time: str  # ISO format
    participants: List[str] = []
    notifications_enabled: bool = True
    auto_provision: bool = True
    auto_teardown: bool = True
    recurrence: Optional[RecurrenceSettingsModel] = None
    notes: str = ""


class UpdateScheduleRequest(BaseModel):
    """Request to update a scheduled exercise."""
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    participants: Optional[List[str]] = None
    notifications_enabled: Optional[bool] = None
    auto_provision: Optional[bool] = None
    auto_teardown: Optional[bool] = None
    notes: Optional[str] = None


@app.post("/schedules")
async def create_schedule(
    request: CreateScheduleRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Create a new scheduled exercise."""
    try:
        start_time = datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {e}")

    recurrence = None
    if request.recurrence:
        try:
            recurrence_type = RecurrenceType(request.recurrence.recurrence_type)
            end_date = None
            if request.recurrence.end_date:
                end_date = datetime.fromisoformat(
                    request.recurrence.end_date.replace('Z', '+00:00')
                )
            recurrence = RecurrenceSettings(
                recurrence_type=recurrence_type,
                interval=request.recurrence.interval,
                days_of_week=request.recurrence.days_of_week,
                end_date=end_date,
                max_occurrences=request.recurrence.max_occurrences
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid recurrence: {e}")

    try:
        schedule = exercise_scheduler.create_schedule(
            title=request.title,
            description=request.description,
            scenario_id=request.scenario_id,
            scenario_name=request.scenario_name,
            created_by=current_user.username,
            start_time=start_time,
            end_time=end_time,
            participants=request.participants,
            notifications_enabled=request.notifications_enabled,
            auto_provision=request.auto_provision,
            auto_teardown=request.auto_teardown,
            recurrence=recurrence,
            notes=request.notes
        )
        return schedule.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/schedules")
async def list_schedules(
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """List scheduled exercises."""
    schedule_status = ScheduleStatus(status) if status else None

    from_dt = None
    to_dt = None
    if from_date:
        from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
    if to_date:
        to_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))

    # Non-admin users only see their own schedules
    participant = None
    if current_user.role == UserRole.TRAINEE:
        participant = current_user.username

    schedules = exercise_scheduler.list_schedules(
        status=schedule_status,
        participant=participant,
        from_date=from_dt,
        to_date=to_dt
    )
    return [s.to_dict() for s in schedules]


@app.get("/schedules/upcoming")
async def get_upcoming_schedules(
    days: int = 7,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get upcoming scheduled exercises."""
    schedules = exercise_scheduler.get_upcoming_schedules(days)

    # Filter for trainees
    if current_user.role == UserRole.TRAINEE:
        schedules = [
            s for s in schedules
            if current_user.username in s.participants
        ]

    return [s.to_dict() for s in schedules]


@app.get("/schedules/calendar/{year}/{month}")
async def get_calendar_view(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get calendar view of schedules for a month."""
    username = None
    if current_user.role == UserRole.TRAINEE:
        username = current_user.username

    return exercise_scheduler.get_calendar_view(year, month, username)


@app.get("/schedules/me")
async def get_my_schedules(
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get schedules for the current user."""
    schedules = exercise_scheduler.get_user_schedules(current_user.username)
    return [s.to_dict() for s in schedules]


@app.get("/schedules/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get a scheduled exercise by ID."""
    schedule = exercise_scheduler.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule.to_dict()


@app.put("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    request: UpdateScheduleRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Update a scheduled exercise."""
    schedule = exercise_scheduler.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Only creator or admin can update
    if schedule.created_by != current_user.username and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    start_time = None
    end_time = None
    if request.start_time:
        start_time = datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
    if request.end_time:
        end_time = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))

    try:
        updated = exercise_scheduler.update_schedule(
            schedule_id=schedule_id,
            title=request.title,
            description=request.description,
            start_time=start_time,
            end_time=end_time,
            participants=request.participants,
            notifications_enabled=request.notifications_enabled,
            auto_provision=request.auto_provision,
            auto_teardown=request.auto_teardown,
            notes=request.notes
        )
        return updated.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/schedules/{schedule_id}/cancel")
async def cancel_schedule(
    schedule_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Cancel a scheduled exercise."""
    schedule = exercise_scheduler.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if schedule.created_by != current_user.username and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        updated = exercise_scheduler.cancel_schedule(schedule_id)
        return updated.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Delete a scheduled exercise (admin only)."""
    try:
        if not exercise_scheduler.delete_schedule(schedule_id):
            raise HTTPException(status_code=404, detail="Schedule not found")
        return {"message": "Schedule deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/schedules/{schedule_id}/start")
async def start_scheduled_exercise(
    schedule_id: str,
    lab_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Start a scheduled exercise."""
    try:
        schedule = exercise_scheduler.start_exercise(schedule_id, lab_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return schedule.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/schedules/{schedule_id}/complete")
async def complete_scheduled_exercise(
    schedule_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Mark a scheduled exercise as completed."""
    schedule = exercise_scheduler.complete_exercise(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule.to_dict()


@app.post("/schedules/{schedule_id}/participants/{username}")
async def add_schedule_participant(
    schedule_id: str,
    username: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Add a participant to a schedule."""
    schedule = exercise_scheduler.add_participant(schedule_id, username)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule.to_dict()


@app.delete("/schedules/{schedule_id}/participants/{username}")
async def remove_schedule_participant(
    schedule_id: str,
    username: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Remove a participant from a schedule."""
    schedule = exercise_scheduler.remove_participant(schedule_id, username)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule.to_dict()


# ============ Notification Endpoints ============

@app.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get notifications for the current user."""
    notifications = exercise_scheduler.get_user_notifications(
        username=current_user.username,
        unread_only=unread_only,
        limit=limit
    )
    return [n.to_dict() for n in notifications]


@app.get("/notifications/unread-count")
async def get_unread_notification_count(
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get count of unread notifications."""
    count = exercise_scheduler.get_unread_count(current_user.username)
    return {"unread_count": count}


@app.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Mark a notification as read."""
    notification = exercise_scheduler.mark_notification_read(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification.to_dict()


@app.post("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user)
) -> dict:
    """Mark all notifications as read."""
    count = exercise_scheduler.mark_all_notifications_read(current_user.username)
    return {"marked_read": count}
