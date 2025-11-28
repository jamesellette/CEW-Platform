from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json
from pathlib import Path

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
