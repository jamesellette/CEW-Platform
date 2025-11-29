from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
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
from topology_editor import (
    topology_editor, NodeType, ConnectionType, ValidationSeverity
)
from rate_limiting import (
    rate_limiter, RateLimitTier, RateLimitRule, ThrottleAction,
    EndpointRateLimitConfig
)
from backup_recovery import (
    backup_manager, BackupType, BackupStatus, RestoreStatus
)
from external_integrations import (
    external_integrations, IntegrationType, IntegrationStatus, LogLevel
)
from rf_ew_simulation import (
    rf_ew_simulator, SignalType, ModulationType, JammingType,
    ThreatType, SimulationStatus as RFSimStatus
)
from contextlib import asynccontextmanager
import asyncio


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


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to all requests."""
    # Skip rate limiting for certain paths
    if request.url.path in ["/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)
    
    # Get user info from token if present
    user_id = None
    user_role = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user = get_user_from_token(token)
        if user:
            user_id = user.username
            user_role = user.role
    
    # Get client IP
    ip_address = request.client.host if request.client else "unknown"
    
    # Check rate limit
    result = await rate_limiter.check_rate_limit(
        endpoint=request.url.path,
        ip_address=ip_address,
        user_id=user_id,
        user_role=user_role
    )
    
    if not result["allowed"]:
        # Return 429 Too Many Requests
        return JSONResponse(
            status_code=429,
            content={
                "detail": result.get("reason", "Rate limit exceeded"),
                "retry_after_seconds": result.get("retry_after_seconds", 60)
            },
            headers={
                "Retry-After": str(result.get("retry_after_seconds", 60)),
                "X-RateLimit-Remaining": "0"
            }
        )
    
    # Add delay if requested
    if result.get("action") == "delay":
        await asyncio.sleep(result.get("delay_seconds", 1.0))
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    remaining = result.get("remaining", {})
    response.headers["X-RateLimit-Remaining-Minute"] = str(remaining.get("per_minute", 0))
    response.headers["X-RateLimit-Remaining-Hour"] = str(remaining.get("per_hour", 0))
    
    return response

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


# ============ Topology Editor Endpoints ============


class CreateTopologyRequest(BaseModel):
    """Request to create a new topology."""
    name: str
    description: str
    metadata: Optional[dict] = None


class AddNodeRequest(BaseModel):
    """Request to add a node."""
    name: str
    node_type: str
    x: float
    y: float
    image: str = "alpine:latest"
    ip_addresses: List[str] = []
    properties: Optional[dict] = None
    ports: List[str] = []
    labels: Optional[dict] = None


class UpdateNodeRequest(BaseModel):
    """Request to update a node."""
    name: Optional[str] = None
    node_type: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    image: Optional[str] = None
    ip_addresses: Optional[List[str]] = None
    properties: Optional[dict] = None
    ports: Optional[List[str]] = None
    labels: Optional[dict] = None


class AddConnectionRequest(BaseModel):
    """Request to add a connection."""
    source_node_id: str
    target_node_id: str
    connection_type: str = "ethernet"
    source_port: Optional[str] = None
    target_port: Optional[str] = None
    bandwidth: Optional[str] = None
    latency: Optional[int] = None
    properties: Optional[dict] = None
    labels: Optional[dict] = None


class AddSubnetRequest(BaseModel):
    """Request to add a subnet."""
    name: str
    cidr: str
    vlan_id: Optional[int] = None
    gateway: Optional[str] = None
    dns_servers: List[str] = []
    properties: Optional[dict] = None


class ImportTopologyRequest(BaseModel):
    """Request to import a topology."""
    name: str
    content: str
    format: str = "json"


@app.post("/topology-editor")
async def create_topology(
    request: CreateTopologyRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Create a new topology."""
    topology = topology_editor.create_topology(
        name=request.name,
        description=request.description,
        created_by=current_user.username,
        metadata=request.metadata
    )
    return topology.to_dict()


@app.get("/topology-editor")
async def list_editor_topologies(
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """List topologies."""
    # Trainees only see their own topologies
    created_by = None
    if current_user.role == UserRole.TRAINEE:
        created_by = current_user.username

    topologies = topology_editor.list_topologies(created_by=created_by)
    return [t.to_dict() for t in topologies]


@app.get("/topology-editor/node-types")
async def get_node_types(
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get available node types."""
    return [
        {"value": nt.value, "name": nt.value.replace("_", " ").title()}
        for nt in NodeType
    ]


@app.get("/topology-editor/connection-types")
async def get_connection_types(
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get available connection types."""
    return [
        {"value": ct.value, "name": ct.value.replace("_", " ").title()}
        for ct in ConnectionType
    ]


@app.get("/topology-editor/{topology_id}")
async def get_editor_topology(
    topology_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get a topology by ID."""
    topology = topology_editor.get_topology(topology_id)
    if not topology:
        raise HTTPException(status_code=404, detail="Topology not found")
    return topology.to_dict()


@app.put("/topology-editor/{topology_id}")
async def update_editor_topology(
    topology_id: str,
    request: CreateTopologyRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Update a topology."""
    topology = topology_editor.update_topology(
        topology_id=topology_id,
        name=request.name,
        description=request.description,
        metadata=request.metadata
    )
    if not topology:
        raise HTTPException(status_code=404, detail="Topology not found")
    return topology.to_dict()


@app.delete("/topology-editor/{topology_id}")
async def delete_topology(
    topology_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Delete a topology."""
    if not topology_editor.delete_topology(topology_id):
        raise HTTPException(status_code=404, detail="Topology not found")
    return {"message": "Topology deleted"}


@app.post("/topology-editor/{topology_id}/clone")
async def clone_topology(
    topology_id: str,
    new_name: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Clone a topology."""
    clone = topology_editor.clone_topology(
        topology_id=topology_id,
        new_name=new_name,
        created_by=current_user.username
    )
    if not clone:
        raise HTTPException(status_code=404, detail="Topology not found")
    return clone.to_dict()


@app.post("/topology-editor/{topology_id}/nodes")
async def add_node(
    topology_id: str,
    request: AddNodeRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Add a node to a topology."""
    try:
        node_type = NodeType(request.node_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node type")

    node = topology_editor.add_node(
        topology_id=topology_id,
        name=request.name,
        node_type=node_type,
        x=request.x,
        y=request.y,
        image=request.image,
        ip_addresses=request.ip_addresses,
        properties=request.properties,
        ports=request.ports,
        labels=request.labels
    )
    if not node:
        raise HTTPException(status_code=404, detail="Topology not found")
    return node.to_dict()


@app.put("/topology-editor/{topology_id}/nodes/{node_id}")
async def update_node(
    topology_id: str,
    node_id: str,
    request: UpdateNodeRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Update a node."""
    node_type = None
    if request.node_type:
        try:
            node_type = NodeType(request.node_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid node type")

    node = topology_editor.update_node(
        topology_id=topology_id,
        node_id=node_id,
        name=request.name,
        node_type=node_type,
        x=request.x,
        y=request.y,
        image=request.image,
        ip_addresses=request.ip_addresses,
        properties=request.properties,
        ports=request.ports,
        labels=request.labels
    )
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node.to_dict()


@app.delete("/topology-editor/{topology_id}/nodes/{node_id}")
async def delete_node(
    topology_id: str,
    node_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Delete a node."""
    if not topology_editor.delete_node(topology_id, node_id):
        raise HTTPException(status_code=404, detail="Node not found")
    return {"message": "Node deleted"}


@app.post("/topology-editor/{topology_id}/nodes/{node_id}/move")
async def move_node(
    topology_id: str,
    node_id: str,
    x: float,
    y: float,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Move a node to a new position."""
    node = topology_editor.move_node(topology_id, node_id, x, y)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node.to_dict()


@app.post("/topology-editor/{topology_id}/connections")
async def add_connection(
    topology_id: str,
    request: AddConnectionRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Add a connection between nodes."""
    try:
        conn_type = ConnectionType(request.connection_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid connection type")

    try:
        connection = topology_editor.add_connection(
            topology_id=topology_id,
            source_node_id=request.source_node_id,
            target_node_id=request.target_node_id,
            connection_type=conn_type,
            source_port=request.source_port,
            target_port=request.target_port,
            bandwidth=request.bandwidth,
            latency=request.latency,
            properties=request.properties,
            labels=request.labels
        )
        if not connection:
            raise HTTPException(status_code=404, detail="Topology not found")
        return connection.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/topology-editor/{topology_id}/connections/{connection_id}")
async def delete_connection(
    topology_id: str,
    connection_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Delete a connection."""
    if not topology_editor.delete_connection(topology_id, connection_id):
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"message": "Connection deleted"}


@app.post("/topology-editor/{topology_id}/subnets")
async def add_subnet(
    topology_id: str,
    request: AddSubnetRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Add a subnet to a topology."""
    subnet = topology_editor.add_subnet(
        topology_id=topology_id,
        name=request.name,
        cidr=request.cidr,
        vlan_id=request.vlan_id,
        gateway=request.gateway,
        dns_servers=request.dns_servers,
        properties=request.properties
    )
    if not subnet:
        raise HTTPException(status_code=404, detail="Topology not found")
    return subnet.to_dict()


@app.delete("/topology-editor/{topology_id}/subnets/{subnet_id}")
async def delete_subnet(
    topology_id: str,
    subnet_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Delete a subnet."""
    if not topology_editor.delete_subnet(topology_id, subnet_id):
        raise HTTPException(status_code=404, detail="Subnet not found")
    return {"message": "Subnet deleted"}


@app.get("/topology-editor/{topology_id}/validate")
async def validate_topology(
    topology_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Validate a topology and return any issues."""
    issues = topology_editor.validate_topology(topology_id)
    errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
    warnings = [i for i in issues if i.severity == ValidationSeverity.WARNING]

    return {
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": [i.to_dict() for i in issues]
    }


@app.get("/topology-editor/{topology_id}/export")
async def export_topology(
    topology_id: str,
    format: str = "json",
    current_user: User = Depends(get_current_user)
) -> Response:
    """Export a topology in various formats."""
    if format == "json":
        content = topology_editor.export_json(topology_id)
        media_type = "application/json"
    elif format == "yaml":
        content = topology_editor.export_yaml(topology_id)
        media_type = "application/x-yaml"
    elif format == "graphviz":
        content = topology_editor.export_graphviz(topology_id)
        media_type = "text/plain"
    elif format == "scenario":
        result = topology_editor.export_scenario(topology_id)
        if not result:
            raise HTTPException(status_code=404, detail="Topology not found")
        return result
    else:
        raise HTTPException(status_code=400, detail="Invalid format")

    if not content:
        raise HTTPException(status_code=404, detail="Topology not found")

    topology = topology_editor.get_topology(topology_id)
    filename = f"{topology.name}.{format}" if topology else f"topology.{format}"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.post("/topology-editor/import")
async def import_topology(
    request: ImportTopologyRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Import a topology from JSON or YAML."""
    try:
        if request.format == "json":
            topology = topology_editor.import_json(
                json_content=request.content,
                name=request.name,
                created_by=current_user.username
            )
        elif request.format == "yaml":
            topology = topology_editor.import_yaml(
                yaml_content=request.content,
                name=request.name,
                created_by=current_user.username
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid format")

        return topology.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ Rate Limiting Endpoints ============


class SetTierLimitsRequest(BaseModel):
    """Request to set tier rate limits."""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: int = 10
    burst_window_seconds: int = 10
    action_on_exceed: str = "reject"
    delay_seconds: float = 1.0


class SetEndpointConfigRequest(BaseModel):
    """Request to set endpoint rate limit config."""
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    burst_limit: Optional[int] = None
    exempt_tiers: List[str] = []
    enabled: bool = True


class BlockUserRequest(BaseModel):
    """Request to block a user."""
    duration_minutes: int = 60


@app.get("/rate-limits/status")
async def get_rate_limit_status(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Get rate limiting status and configuration."""
    return {
        "enabled": rate_limiter.is_enabled(),
        "tier_rules": rate_limiter.get_tier_rules(),
        "endpoint_configs": rate_limiter.get_endpoint_configs()
    }


@app.post("/rate-limits/enable")
async def enable_rate_limiting(
    enabled: bool = True,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Enable or disable rate limiting globally."""
    rate_limiter.set_enabled(enabled)
    log_action(
        action=AuditAction.VIEW_SCENARIO,  # Using existing action type
        username=current_user.username,
        resource_type="rate_limits",
        details=f"Rate limiting {'enabled' if enabled else 'disabled'}"
    )
    return {"enabled": rate_limiter.is_enabled()}


@app.get("/rate-limits/statistics")
async def get_rate_limit_statistics(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Get rate limiting usage statistics."""
    return rate_limiter.get_statistics()


@app.get("/rate-limits/violations")
async def get_rate_limit_violations(
    user_id: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> List[dict]:
    """Get rate limit violation history."""
    return rate_limiter.get_violations(user_id=user_id, limit=limit)


@app.get("/rate-limits/top-users")
async def get_top_api_users(
    limit: int = 10,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> List[dict]:
    """Get top users by API request count."""
    return rate_limiter.get_top_users(limit)


@app.get("/rate-limits/top-endpoints")
async def get_top_api_endpoints(
    limit: int = 10,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> List[dict]:
    """Get top endpoints by request count."""
    return rate_limiter.get_top_endpoints(limit)


@app.get("/rate-limits/users/{user_id}")
async def get_user_rate_limit_state(
    user_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Get rate limit state for a specific user."""
    state = rate_limiter.get_user_state(user_id)
    if not state:
        raise HTTPException(status_code=404, detail="User state not found")
    return state


@app.post("/rate-limits/users/{user_id}/reset")
async def reset_user_rate_limit(
    user_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Reset rate limit state for a user."""
    rate_limiter.reset_user_state(user_id)
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="rate_limits",
        resource_id=user_id,
        details=f"Reset rate limit state for user: {user_id}"
    )
    return {"message": f"Rate limit state reset for user: {user_id}"}


@app.post("/rate-limits/users/{user_id}/block")
async def block_user_rate_limit(
    user_id: str,
    request: BlockUserRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Block a user from making API requests."""
    rate_limiter.block_user(user_id, request.duration_minutes)
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="rate_limits",
        resource_id=user_id,
        details=f"Blocked user {user_id} for {request.duration_minutes} minutes"
    )
    return {"message": f"User {user_id} blocked for {request.duration_minutes} minutes"}


@app.post("/rate-limits/users/{user_id}/unblock")
async def unblock_user_rate_limit(
    user_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Unblock a blocked user."""
    if rate_limiter.unblock_user(user_id):
        log_action(
            action=AuditAction.VIEW_SCENARIO,
            username=current_user.username,
            resource_type="rate_limits",
            resource_id=user_id,
            details=f"Unblocked user: {user_id}"
        )
        return {"message": f"User {user_id} unblocked"}
    raise HTTPException(status_code=404, detail="User not found or not blocked")


@app.put("/rate-limits/tiers/{tier}")
async def set_tier_rate_limits(
    tier: str,
    request: SetTierLimitsRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Set rate limits for a specific tier."""
    try:
        tier_enum = RateLimitTier(tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}")
    
    try:
        action = ThrottleAction(request.action_on_exceed)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action: {request.action_on_exceed}"
        )
    
    rule = RateLimitRule(
        rule_id=f"{tier}_custom",
        name=f"{tier.title()} Custom Limit",
        requests_per_minute=request.requests_per_minute,
        requests_per_hour=request.requests_per_hour,
        requests_per_day=request.requests_per_day,
        burst_limit=request.burst_limit,
        burst_window_seconds=request.burst_window_seconds,
        action_on_exceed=action,
        delay_seconds=request.delay_seconds
    )
    
    rate_limiter.set_tier_limits(tier_enum, rule)
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="rate_limits",
        details=f"Updated rate limits for tier: {tier}"
    )
    
    return rule.to_dict()


@app.put("/rate-limits/endpoints/{endpoint:path}")
async def set_endpoint_rate_limit(
    endpoint: str,
    request: SetEndpointConfigRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Set rate limit configuration for a specific endpoint."""
    exempt_tiers = []
    for tier_str in request.exempt_tiers:
        try:
            exempt_tiers.append(RateLimitTier(tier_str))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid tier: {tier_str}")
    
    config = EndpointRateLimitConfig(
        endpoint_pattern=f"/{endpoint}",
        requests_per_minute=request.requests_per_minute,
        requests_per_hour=request.requests_per_hour,
        burst_limit=request.burst_limit,
        exempt_tiers=exempt_tiers,
        enabled=request.enabled
    )
    
    rate_limiter.set_endpoint_config(f"/{endpoint}", config)
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="rate_limits",
        details=f"Updated rate limit config for endpoint: /{endpoint}"
    )
    
    return config.to_dict()


@app.post("/rate-limits/statistics/reset")
async def reset_rate_limit_statistics(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Reset rate limiting statistics."""
    rate_limiter.reset_statistics()
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="rate_limits",
        details="Reset rate limiting statistics"
    )
    return {"message": "Statistics reset"}


@app.get("/rate-limits/me")
async def get_my_rate_limit_status(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get current user's rate limit status."""
    state = rate_limiter.get_user_state(current_user.username)
    tier_rules = rate_limiter.get_tier_rules()
    
    # Map user role to tier
    tier_map = {
        "admin": "admin",
        "instructor": "instructor",
        "trainee": "trainee"
    }
    user_tier = tier_map.get(current_user.role, "trainee")
    
    return {
        "username": current_user.username,
        "tier": user_tier,
        "limits": tier_rules.get(user_tier, {}),
        "current_state": state
    }


# ============ Backup & Disaster Recovery Endpoints ============


class CreateBackupRequest(BaseModel):
    """Request to create a backup."""
    backup_type: str
    description: str = ""
    tags: List[str] = []
    retention_days: int = 30


class CreateLabSnapshotRequest(BaseModel):
    """Request to create a lab snapshot."""
    lab_id: str
    scenario_id: str
    status: str
    containers: List[dict] = []
    networks: List[dict] = []
    environment: dict = {}
    notes: str = ""


class CreateBackupScheduleRequest(BaseModel):
    """Request to create a backup schedule."""
    backup_type: str
    frequency: str  # daily, weekly, monthly
    time_of_day: str  # HH:MM
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    retention_days: int = 30
    max_backups: int = 10


class UpdateScheduleRequest(BaseModel):
    """Request to update a backup schedule."""
    enabled: Optional[bool] = None
    time_of_day: Optional[str] = None
    retention_days: Optional[int] = None
    max_backups: Optional[int] = None


class ImportBackupRequest(BaseModel):
    """Request to import a backup."""
    content: str
    format: str = "json"


@app.post("/backups")
async def create_backup(
    request: CreateBackupRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Create a new backup."""
    try:
        backup_type = BackupType(request.backup_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid backup type: {request.backup_type}")
    
    # Collect data based on backup type
    data = {}
    if backup_type == BackupType.SCENARIOS:
        data = {"scenarios": {k: v.model_dump() for k, v in db.items()}}
    elif backup_type == BackupType.CONFIG:
        data = {"config": {"safety": {"air_gap_enforced": True}}}
    elif backup_type == BackupType.FULL:
        data = {
            "scenarios": {k: v.model_dump() for k, v in db.items()},
            "config": {"safety": {"air_gap_enforced": True}},
            "active_scenarios": dict(active_scenarios)
        }
    
    metadata = backup_manager.create_backup(
        backup_type=backup_type,
        created_by=current_user.username,
        description=request.description,
        data=data,
        tags=request.tags,
        retention_days=request.retention_days
    )
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="backup",
        resource_id=metadata.backup_id,
        details=f"Created {backup_type.value} backup"
    )
    
    return metadata.to_dict()


@app.get("/backups")
async def list_backups(
    backup_type: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> List[dict]:
    """List backups."""
    btype = BackupType(backup_type) if backup_type else None
    bstatus = BackupStatus(status) if status else None
    tag_list = tags.split(",") if tags else None
    
    backups = backup_manager.list_backups(
        backup_type=btype,
        status=bstatus,
        tags=tag_list,
        limit=limit
    )
    
    return [b.to_dict() for b in backups]


@app.get("/backups/statistics")
async def get_backup_statistics(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Get backup statistics."""
    return backup_manager.get_statistics()


@app.get("/backups/{backup_id}")
async def get_backup(
    backup_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Get a backup by ID."""
    backup = backup_manager.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    return backup.to_dict()


@app.delete("/backups/{backup_id}")
async def delete_backup(
    backup_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Delete a backup."""
    if not backup_manager.delete_backup(backup_id):
        raise HTTPException(status_code=404, detail="Backup not found")
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="backup",
        resource_id=backup_id,
        details="Deleted backup"
    )
    
    return {"message": "Backup deleted"}


@app.post("/backups/{backup_id}/verify")
async def verify_backup(
    backup_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Verify backup integrity."""
    result = backup_manager.verify_backup(backup_id)
    return result


@app.post("/backups/{backup_id}/restore")
async def restore_backup(
    backup_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Restore from a backup."""
    restore_point = backup_manager.restore_backup(
        backup_id=backup_id,
        created_by=current_user.username
    )
    
    if restore_point.status == RestoreStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=restore_point.error_message or "Restore failed"
        )
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="backup",
        resource_id=backup_id,
        details=f"Restored from backup (restore_id: {restore_point.restore_id})"
    )
    
    return restore_point.to_dict()


@app.get("/backups/{backup_id}/export")
async def export_backup(
    backup_id: str,
    format: str = "json",
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> Response:
    """Export a backup."""
    content = backup_manager.export_backup(backup_id, format)
    if not content:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    media_type = "application/json" if format == "json" else "application/x-yaml"
    
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="backup_{backup_id}.{format}"'}
    )


@app.post("/backups/import")
async def import_backup(
    request: ImportBackupRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Import a backup."""
    try:
        metadata = backup_manager.import_backup(
            content=request.content,
            format=request.format,
            created_by=current_user.username
        )
        
        log_action(
            action=AuditAction.VIEW_SCENARIO,
            username=current_user.username,
            resource_type="backup",
            resource_id=metadata.backup_id,
            details="Imported backup"
        )
        
        return metadata.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/backups/cleanup")
async def cleanup_expired_backups(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Remove expired backups."""
    count = backup_manager.cleanup_expired_backups()
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="backup",
        details=f"Cleaned up {count} expired backups"
    )
    
    return {"removed_count": count}


# ============ Lab Snapshots ============


@app.post("/snapshots")
async def create_lab_snapshot(
    request: CreateLabSnapshotRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Create a lab state snapshot."""
    snapshot = backup_manager.create_lab_snapshot(
        lab_id=request.lab_id,
        scenario_id=request.scenario_id,
        created_by=current_user.username,
        status=request.status,
        containers=request.containers,
        networks=request.networks,
        environment=request.environment,
        notes=request.notes
    )
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="snapshot",
        resource_id=snapshot.snapshot_id,
        details=f"Created lab snapshot for lab {request.lab_id}"
    )
    
    return snapshot.to_dict()


@app.get("/snapshots")
async def list_lab_snapshots(
    lab_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> List[dict]:
    """List lab snapshots."""
    snapshots = backup_manager.list_lab_snapshots(
        lab_id=lab_id,
        scenario_id=scenario_id,
        limit=limit
    )
    return [s.to_dict() for s in snapshots]


@app.get("/snapshots/{snapshot_id}")
async def get_lab_snapshot(
    snapshot_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get a lab snapshot by ID."""
    snapshot = backup_manager.get_lab_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot.to_dict()


@app.delete("/snapshots/{snapshot_id}")
async def delete_lab_snapshot(
    snapshot_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Delete a lab snapshot."""
    if not backup_manager.delete_lab_snapshot(snapshot_id):
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="snapshot",
        resource_id=snapshot_id,
        details="Deleted lab snapshot"
    )
    
    return {"message": "Snapshot deleted"}


@app.post("/snapshots/{snapshot_id}/restore")
async def restore_lab_snapshot(
    snapshot_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Restore from a lab snapshot."""
    result = backup_manager.restore_lab_snapshot(
        snapshot_id=snapshot_id,
        created_by=current_user.username
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="snapshot",
        resource_id=snapshot_id,
        details="Restored from lab snapshot"
    )
    
    return result


# ============ Restore Points ============


@app.get("/restore-points")
async def list_restore_points(
    backup_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> List[dict]:
    """List restore points."""
    rstatus = RestoreStatus(status) if status else None
    
    points = backup_manager.list_restore_points(
        backup_id=backup_id,
        status=rstatus,
        limit=limit
    )
    
    return [p.to_dict() for p in points]


@app.get("/restore-points/{restore_id}")
async def get_restore_point(
    restore_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Get a restore point by ID."""
    point = backup_manager.get_restore_point(restore_id)
    if not point:
        raise HTTPException(status_code=404, detail="Restore point not found")
    return point.to_dict()


# ============ Backup Schedules ============


@app.post("/backup-schedules")
async def create_backup_schedule(
    request: CreateBackupScheduleRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Create an automated backup schedule."""
    try:
        backup_type = BackupType(request.backup_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid backup type: {request.backup_type}")
    
    if request.frequency not in ["daily", "weekly", "monthly"]:
        raise HTTPException(status_code=400, detail="Invalid frequency")
    
    schedule = backup_manager.create_schedule(
        backup_type=backup_type,
        created_by=current_user.username,
        frequency=request.frequency,
        time_of_day=request.time_of_day,
        day_of_week=request.day_of_week,
        day_of_month=request.day_of_month,
        retention_days=request.retention_days,
        max_backups=request.max_backups
    )
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="backup_schedule",
        resource_id=schedule.schedule_id,
        details=f"Created {request.frequency} backup schedule"
    )
    
    return schedule.to_dict()


@app.get("/backup-schedules")
async def list_backup_schedules(
    enabled_only: bool = False,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> List[dict]:
    """List backup schedules."""
    schedules = backup_manager.list_schedules(enabled_only=enabled_only)
    return [s.to_dict() for s in schedules]


@app.get("/backup-schedules/{schedule_id}")
async def get_backup_schedule(
    schedule_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Get a backup schedule by ID."""
    schedule = backup_manager.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule.to_dict()


@app.put("/backup-schedules/{schedule_id}")
async def update_backup_schedule(
    schedule_id: str,
    request: UpdateScheduleRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Update a backup schedule."""
    schedule = backup_manager.update_schedule(
        schedule_id=schedule_id,
        enabled=request.enabled,
        time_of_day=request.time_of_day,
        retention_days=request.retention_days,
        max_backups=request.max_backups
    )
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="backup_schedule",
        resource_id=schedule_id,
        details="Updated backup schedule"
    )
    
    return schedule.to_dict()


@app.delete("/backup-schedules/{schedule_id}")
async def delete_backup_schedule(
    schedule_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Delete a backup schedule."""
    if not backup_manager.delete_schedule(schedule_id):
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="backup_schedule",
        resource_id=schedule_id,
        details="Deleted backup schedule"
    )
    
    return {"message": "Schedule deleted"}


# ============ External Integrations Endpoints ============


class CreateIntegrationRequest(BaseModel):
    """Request to create an integration."""
    integration_type: str
    name: str
    config: dict = {}
    enabled: bool = True


class UpdateIntegrationRequest(BaseModel):
    """Request to update an integration."""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[dict] = None


class CreateAttackMappingRequest(BaseModel):
    """Request to create an ATT&CK mapping."""
    scenario_id: str
    scenario_name: str
    techniques: List[str]
    notes: str = ""


class UpdateAttackMappingRequest(BaseModel):
    """Request to update an ATT&CK mapping."""
    techniques: Optional[List[str]] = None
    notes: Optional[str] = None


class CreateForwardingRuleRequest(BaseModel):
    """Request to create a forwarding rule."""
    name: str
    integration_id: str
    log_levels: List[str] = ["info", "warning", "error"]
    source_filter: Optional[str] = None
    batch_size: int = 100
    flush_interval: int = 30


class UpdateForwardingRuleRequest(BaseModel):
    """Request to update a forwarding rule."""
    enabled: Optional[bool] = None
    log_levels: Optional[List[str]] = None
    source_filter: Optional[str] = None
    batch_size: Optional[int] = None


class CreateEmulationConfigRequest(BaseModel):
    """Request to create an emulation config."""
    name: str
    topology_id: str
    emulator_type: str
    controller: str = "default"
    link_params: dict = {}
    host_params: dict = {}
    switch_params: dict = {}


# Integration Management

@app.post("/integrations")
async def create_integration(
    request: CreateIntegrationRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Create a new external integration."""
    try:
        integration_type = IntegrationType(request.integration_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid integration type: {request.integration_type}")
    
    config = external_integrations.create_integration(
        integration_type=integration_type,
        name=request.name,
        created_by=current_user.username,
        config=request.config,
        enabled=request.enabled
    )
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="integration",
        resource_id=config.integration_id,
        details=f"Created {integration_type.value} integration: {request.name}"
    )
    
    return config.to_dict()


@app.get("/integrations")
async def list_integrations(
    integration_type: Optional[str] = None,
    enabled_only: bool = False,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> List[dict]:
    """List external integrations."""
    itype = IntegrationType(integration_type) if integration_type else None
    
    integrations = external_integrations.list_integrations(
        integration_type=itype,
        enabled_only=enabled_only
    )
    
    return [i.to_dict() for i in integrations]


@app.get("/integrations/statistics")
async def get_integration_statistics(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Get external integration statistics."""
    return external_integrations.get_statistics()


@app.get("/integrations/{integration_id}")
async def get_integration(
    integration_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Get an integration by ID."""
    integration = external_integrations.get_integration(integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration.to_dict()


@app.put("/integrations/{integration_id}")
async def update_integration(
    integration_id: str,
    request: UpdateIntegrationRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Update an integration."""
    integration = external_integrations.update_integration(
        integration_id=integration_id,
        name=request.name,
        enabled=request.enabled,
        config=request.config
    )
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return integration.to_dict()


@app.delete("/integrations/{integration_id}")
async def delete_integration(
    integration_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Delete an integration."""
    if not external_integrations.delete_integration(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="integration",
        resource_id=integration_id,
        details="Deleted integration"
    )
    
    return {"message": "Integration deleted"}


@app.post("/integrations/{integration_id}/test")
async def test_integration(
    integration_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Test integration connectivity."""
    result = external_integrations.test_integration(integration_id)
    return result


# MITRE ATT&CK

@app.get("/mitre-attack/tactics")
async def get_attack_tactics(
    current_user: User = Depends(get_current_user)
) -> List[str]:
    """Get MITRE ATT&CK tactics."""
    return external_integrations.get_tactics()


@app.get("/mitre-attack/techniques")
async def list_attack_techniques(
    tactic: Optional[str] = None,
    platform: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """List MITRE ATT&CK techniques."""
    techniques = external_integrations.list_techniques(
        tactic=tactic,
        platform=platform,
        search=search
    )
    return [t.to_dict() for t in techniques]


@app.get("/mitre-attack/techniques/{technique_id}")
async def get_attack_technique(
    technique_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get a MITRE ATT&CK technique by ID."""
    technique = external_integrations.get_technique(technique_id)
    if not technique:
        raise HTTPException(status_code=404, detail="Technique not found")
    return technique.to_dict()


@app.post("/mitre-attack/mappings")
async def create_attack_mapping(
    request: CreateAttackMappingRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Create a MITRE ATT&CK mapping for a scenario."""
    mapping = external_integrations.create_attack_mapping(
        scenario_id=request.scenario_id,
        scenario_name=request.scenario_name,
        techniques=request.techniques,
        created_by=current_user.username,
        notes=request.notes
    )
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="attack_mapping",
        resource_id=mapping.mapping_id,
        details=f"Created ATT&CK mapping for scenario {request.scenario_id}"
    )
    
    return mapping.to_dict()


@app.get("/mitre-attack/mappings")
async def list_attack_mappings(
    created_by: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """List MITRE ATT&CK mappings."""
    mappings = external_integrations.list_attack_mappings(created_by=created_by)
    return [m.to_dict() for m in mappings]


@app.get("/mitre-attack/mappings/{mapping_id}")
async def get_attack_mapping_endpoint(
    mapping_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get an ATT&CK mapping by ID."""
    mapping = external_integrations.get_attack_mapping(mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return mapping.to_dict()


@app.get("/mitre-attack/mappings/{mapping_id}/details")
async def get_attack_mapping_details(
    mapping_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get detailed ATT&CK mapping with technique info."""
    details = external_integrations.get_mapping_details(mapping_id)
    if not details:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return details


@app.get("/mitre-attack/scenarios/{scenario_id}/mapping")
async def get_scenario_attack_mapping(
    scenario_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get ATT&CK mapping for a scenario."""
    mapping = external_integrations.get_mapping_for_scenario(scenario_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="No mapping found for this scenario")
    return mapping.to_dict()


@app.put("/mitre-attack/mappings/{mapping_id}")
async def update_attack_mapping_endpoint(
    mapping_id: str,
    request: UpdateAttackMappingRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Update an ATT&CK mapping."""
    mapping = external_integrations.update_attack_mapping(
        mapping_id=mapping_id,
        techniques=request.techniques,
        notes=request.notes
    )
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    return mapping.to_dict()


@app.delete("/mitre-attack/mappings/{mapping_id}")
async def delete_attack_mapping_endpoint(
    mapping_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Delete an ATT&CK mapping."""
    if not external_integrations.delete_attack_mapping(mapping_id):
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    return {"message": "Mapping deleted"}


# Log Forwarding

@app.post("/log-forwarding/rules")
async def create_forwarding_rule(
    request: CreateForwardingRuleRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Create a log forwarding rule."""
    try:
        log_levels = [LogLevel(l) for l in request.log_levels]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid log level: {e}")
    
    rule = external_integrations.create_forwarding_rule(
        name=request.name,
        integration_id=request.integration_id,
        log_levels=log_levels,
        source_filter=request.source_filter,
        batch_size=request.batch_size,
        flush_interval=request.flush_interval
    )
    
    return rule.to_dict()


@app.get("/log-forwarding/rules")
async def list_forwarding_rules(
    integration_id: Optional[str] = None,
    enabled_only: bool = False,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> List[dict]:
    """List log forwarding rules."""
    rules = external_integrations.list_forwarding_rules(
        integration_id=integration_id,
        enabled_only=enabled_only
    )
    return [r.to_dict() for r in rules]


@app.get("/log-forwarding/rules/{rule_id}")
async def get_forwarding_rule(
    rule_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Get a forwarding rule by ID."""
    rule = external_integrations.get_forwarding_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule.to_dict()


@app.put("/log-forwarding/rules/{rule_id}")
async def update_forwarding_rule_endpoint(
    rule_id: str,
    request: UpdateForwardingRuleRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Update a forwarding rule."""
    log_levels = None
    if request.log_levels:
        try:
            log_levels = [LogLevel(l) for l in request.log_levels]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid log level: {e}")
    
    rule = external_integrations.update_forwarding_rule(
        rule_id=rule_id,
        enabled=request.enabled,
        log_levels=log_levels,
        source_filter=request.source_filter,
        batch_size=request.batch_size
    )
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return rule.to_dict()


@app.delete("/log-forwarding/rules/{rule_id}")
async def delete_forwarding_rule_endpoint(
    rule_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Delete a forwarding rule."""
    if not external_integrations.delete_forwarding_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"message": "Rule deleted"}


# Network Emulation

@app.post("/emulation/configs")
async def create_emulation_config(
    request: CreateEmulationConfigRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Create a network emulation configuration."""
    if request.emulator_type not in ["mininet", "core"]:
        raise HTTPException(status_code=400, detail="Invalid emulator type. Use 'mininet' or 'core'")
    
    config = external_integrations.create_emulation_config(
        name=request.name,
        topology_id=request.topology_id,
        emulator_type=request.emulator_type,
        controller=request.controller,
        link_params=request.link_params or {"bw": 10, "delay": "5ms"},
        host_params=request.host_params,
        switch_params=request.switch_params
    )
    
    return config.to_dict()


@app.get("/emulation/configs")
async def list_emulation_configs(
    topology_id: Optional[str] = None,
    emulator_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """List network emulation configurations."""
    configs = external_integrations.list_emulation_configs(
        topology_id=topology_id,
        emulator_type=emulator_type
    )
    return [c.to_dict() for c in configs]


@app.get("/emulation/configs/{config_id}")
async def get_emulation_config(
    config_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get an emulation config by ID."""
    config = external_integrations.get_emulation_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config.to_dict()


@app.delete("/emulation/configs/{config_id}")
async def delete_emulation_config(
    config_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Delete an emulation config."""
    if not external_integrations.delete_emulation_config(config_id):
        raise HTTPException(status_code=404, detail="Config not found")
    
    return {"message": "Config deleted"}


@app.get("/emulation/configs/{config_id}/script")
async def get_mininet_script(
    config_id: str,
    current_user: User = Depends(get_current_user)
) -> Response:
    """Generate a Mininet Python script from config."""
    script = external_integrations.generate_mininet_script(config_id)
    if not script:
        raise HTTPException(
            status_code=400,
            detail="Could not generate script. Config not found or not a Mininet config."
        )
    
    return Response(
        content=script,
        media_type="text/x-python",
        headers={"Content-Disposition": f'attachment; filename="mininet_{config_id}.py"'}
    )


# ============ RF/EW Simulation Endpoints ============
# SAFETY NOTE: All RF operations are SIMULATED - no real RF transmission occurs


class CreateRFSimulationRequest(BaseModel):
    """Request to create an RF simulation."""
    name: str
    description: str = ""
    settings: dict = {}


class AddSignalRequest(BaseModel):
    """Request to add a signal."""
    name: str
    signal_type: str
    frequency_hz: float
    bandwidth_hz: float
    power_dbm: float
    modulation: str
    location: Optional[List[float]] = None
    metadata: dict = {}


class UpdateSignalRequest(BaseModel):
    """Request to update a signal."""
    active: Optional[bool] = None
    frequency_hz: Optional[float] = None
    power_dbm: Optional[float] = None


class AddJammingRequest(BaseModel):
    """Request to add jamming."""
    name: str
    jamming_type: str
    target_freq_hz: float
    bandwidth_hz: float
    power_dbm: float
    duration_seconds: Optional[float] = None


class CaptureSpectrumRequest(BaseModel):
    """Request to capture spectrum."""
    center_freq_hz: float
    bandwidth_hz: float
    fft_size: int = 1024


class CreateSIGINTReportRequest(BaseModel):
    """Request to create SIGINT report."""
    signals_analyzed: List[str]
    threat_assessment: str
    recommendations: List[str]
    confidence_level: float


# Simulation Management

@app.post("/rf-simulation")
async def create_rf_simulation(
    request: CreateRFSimulationRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Create a new RF/EW simulation (simulation only - no real RF)."""
    sim = rf_ew_simulator.create_simulation(
        name=request.name,
        description=request.description,
        created_by=current_user.username,
        settings=request.settings
    )
    
    log_action(
        action=AuditAction.VIEW_SCENARIO,
        username=current_user.username,
        resource_type="rf_simulation",
        resource_id=sim.simulation_id,
        details=f"Created RF simulation: {request.name}"
    )
    
    return sim.to_dict()


@app.get("/rf-simulation")
async def list_rf_simulations(
    created_by: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """List RF simulations."""
    rstatus = RFSimStatus(status) if status else None
    
    sims = rf_ew_simulator.list_simulations(
        created_by=created_by,
        status=rstatus
    )
    
    return [s.to_dict() for s in sims]


@app.get("/rf-simulation/statistics")
async def get_rf_simulation_statistics(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Get RF simulation statistics."""
    return rf_ew_simulator.get_statistics()


@app.get("/rf-simulation/frequency-bands")
async def get_frequency_bands(
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get standard frequency band definitions."""
    return [b.to_dict() for b in rf_ew_simulator.get_frequency_bands()]


@app.get("/rf-simulation/threats")
async def get_predefined_threats(
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get predefined EW threats for training."""
    return [t.to_dict() for t in rf_ew_simulator.get_predefined_threats()]


@app.get("/rf-simulation/{simulation_id}")
async def get_rf_simulation(
    simulation_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get an RF simulation by ID."""
    sim = rf_ew_simulator.get_simulation(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim.to_dict()


@app.post("/rf-simulation/{simulation_id}/start")
async def start_rf_simulation(
    simulation_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Start an RF simulation."""
    sim = rf_ew_simulator.start_simulation(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim.to_dict()


@app.post("/rf-simulation/{simulation_id}/pause")
async def pause_rf_simulation(
    simulation_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Pause an RF simulation."""
    sim = rf_ew_simulator.pause_simulation(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim.to_dict()


@app.post("/rf-simulation/{simulation_id}/stop")
async def stop_rf_simulation(
    simulation_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Stop an RF simulation."""
    sim = rf_ew_simulator.stop_simulation(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim.to_dict()


@app.delete("/rf-simulation/{simulation_id}")
async def delete_rf_simulation(
    simulation_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> dict:
    """Delete an RF simulation."""
    if not rf_ew_simulator.delete_simulation(simulation_id):
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {"message": "Simulation deleted"}


# Signal Management

@app.post("/rf-simulation/{simulation_id}/signals")
async def add_signal(
    simulation_id: str,
    request: AddSignalRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Add a simulated signal to an RF simulation."""
    try:
        signal_type = SignalType(request.signal_type)
        modulation = ModulationType(request.modulation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid type: {e}")
    
    location = tuple(request.location) if request.location else None
    
    signal = rf_ew_simulator.add_signal(
        simulation_id=simulation_id,
        name=request.name,
        signal_type=signal_type,
        frequency_hz=request.frequency_hz,
        bandwidth_hz=request.bandwidth_hz,
        power_dbm=request.power_dbm,
        modulation=modulation,
        location=location,
        metadata=request.metadata
    )
    
    if not signal:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return signal.to_dict()


@app.get("/rf-simulation/{simulation_id}/signals")
async def list_signals(
    simulation_id: str,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """List signals in an RF simulation."""
    signals = rf_ew_simulator.list_signals(simulation_id)
    return [s.to_dict() for s in signals]


@app.get("/rf-simulation/{simulation_id}/signals/{signal_id}")
async def get_signal(
    simulation_id: str,
    signal_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get a signal by ID."""
    signal = rf_ew_simulator.get_signal(simulation_id, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal.to_dict()


@app.put("/rf-simulation/{simulation_id}/signals/{signal_id}")
async def update_signal(
    simulation_id: str,
    signal_id: str,
    request: UpdateSignalRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Update a signal."""
    signal = rf_ew_simulator.update_signal(
        simulation_id=simulation_id,
        signal_id=signal_id,
        active=request.active,
        frequency_hz=request.frequency_hz,
        power_dbm=request.power_dbm
    )
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    return signal.to_dict()


@app.delete("/rf-simulation/{simulation_id}/signals/{signal_id}")
async def remove_signal(
    simulation_id: str,
    signal_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Remove a signal from simulation."""
    if not rf_ew_simulator.remove_signal(simulation_id, signal_id):
        raise HTTPException(status_code=404, detail="Signal not found")
    return {"message": "Signal removed"}


# Jamming Simulation

@app.post("/rf-simulation/{simulation_id}/jamming")
async def add_jamming(
    simulation_id: str,
    request: AddJammingRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Add a jamming effect to simulation (simulation only)."""
    try:
        jamming_type = JammingType(request.jamming_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid jamming type: {request.jamming_type}")
    
    effect = rf_ew_simulator.add_jamming(
        simulation_id=simulation_id,
        name=request.name,
        jamming_type=jamming_type,
        target_freq_hz=request.target_freq_hz,
        bandwidth_hz=request.bandwidth_hz,
        power_dbm=request.power_dbm,
        duration_seconds=request.duration_seconds
    )
    
    if not effect:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return effect.to_dict()


@app.get("/rf-simulation/{simulation_id}/jamming")
async def list_jamming(
    simulation_id: str,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """List jamming effects in simulation."""
    effects = rf_ew_simulator.list_jamming(simulation_id)
    return [e.to_dict() for e in effects]


@app.delete("/rf-simulation/{simulation_id}/jamming/{effect_id}")
async def remove_jamming(
    simulation_id: str,
    effect_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Remove a jamming effect."""
    if not rf_ew_simulator.remove_jamming(simulation_id, effect_id):
        raise HTTPException(status_code=404, detail="Jamming effect not found")
    return {"message": "Jamming effect removed"}


# Threat Management

@app.post("/rf-simulation/{simulation_id}/threats/{threat_id}")
async def add_threat(
    simulation_id: str,
    threat_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Add a predefined threat to simulation."""
    threat = rf_ew_simulator.add_threat(simulation_id, threat_id)
    if not threat:
        raise HTTPException(status_code=404, detail="Simulation or threat not found")
    return threat.to_dict()


@app.get("/rf-simulation/{simulation_id}/threats")
async def list_simulation_threats(
    simulation_id: str,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """List threats in simulation."""
    threats = rf_ew_simulator.list_threats(simulation_id)
    return [t.to_dict() for t in threats]


@app.delete("/rf-simulation/{simulation_id}/threats/{threat_id}")
async def remove_threat(
    simulation_id: str,
    threat_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Remove a threat from simulation."""
    if not rf_ew_simulator.remove_threat(simulation_id, threat_id):
        raise HTTPException(status_code=404, detail="Threat not found")
    return {"message": "Threat removed"}


# Spectrum Analysis

@app.post("/rf-simulation/{simulation_id}/spectrum")
async def capture_spectrum(
    simulation_id: str,
    request: CaptureSpectrumRequest,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Capture a spectrum snapshot (simulated)."""
    snapshot = rf_ew_simulator.capture_spectrum(
        simulation_id=simulation_id,
        center_freq_hz=request.center_freq_hz,
        bandwidth_hz=request.bandwidth_hz,
        fft_size=request.fft_size
    )
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return snapshot.to_dict()


@app.get("/rf-simulation/{simulation_id}/spectrum")
async def get_spectrum_snapshots(
    simulation_id: str,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get recent spectrum snapshots."""
    snapshots = rf_ew_simulator.get_snapshots(simulation_id, limit)
    return [s.to_dict() for s in snapshots]


# SIGINT Reports

@app.post("/rf-simulation/{simulation_id}/reports")
async def create_sigint_report(
    simulation_id: str,
    request: CreateSIGINTReportRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.INSTRUCTOR]))
) -> dict:
    """Create a SIGINT report."""
    report = rf_ew_simulator.create_sigint_report(
        simulation_id=simulation_id,
        created_by=current_user.username,
        signals_analyzed=request.signals_analyzed,
        threat_assessment=request.threat_assessment,
        recommendations=request.recommendations,
        confidence_level=request.confidence_level
    )
    
    if not report:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return report.to_dict()


@app.get("/rf-simulation/{simulation_id}/reports")
async def get_sigint_reports(
    simulation_id: str,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Get SIGINT reports from simulation."""
    reports = rf_ew_simulator.get_reports(simulation_id, limit)
    return [r.to_dict() for r in reports]
