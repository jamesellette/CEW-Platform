from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json
import yaml
from pathlib import Path
from datetime import timedelta

from auth import (
    User, Token, LoginRequest, UserCreate, UserRole,
    authenticate_user, create_access_token, get_current_user,
    require_role, create_user, list_users, delete_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from audit import (
    AuditLog, AuditAction, log_action, get_audit_logs
)
from orchestrator import orchestrator, LabStatus

app = FastAPI(title="CEW Training Backend (prototype)")

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
        details=f"Emergency kill switch activated. Deactivated {deactivated_count} scenarios, stopped {len(stopped_labs)} labs."
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
