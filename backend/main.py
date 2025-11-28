from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid

app = FastAPI(title="CEW Training Backend (prototype)")


class Scenario(BaseModel):
    id: Optional[str] = None
    name: str
    description: str = ""
    topology: dict = {}
    constraints: dict = {}


db: dict[str, Scenario] = {}  # in-memory store for initial prototype


@app.post("/scenarios", response_model=Scenario)
def create_scenario(s: Scenario) -> Scenario:
    s.id = str(uuid.uuid4())
    if s.constraints.get("allow_external_network", False):
        raise HTTPException(
            status_code=400,
            detail="External network access disabled in prototype"
        )
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
