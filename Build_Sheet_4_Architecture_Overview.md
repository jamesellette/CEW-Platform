```markdown
# Architecture Overview

Key components:
- Frontend (React): Scenario editor, planner, dashboard.
- Backend (FastAPI): scenario CRUD, sessions, orchestration API.
- Orchestrator: worker queue to spin up emulated assets (Docker, CORE/Mininet).
- Emulation Layer: docker containers (isolated), GNU Radio (software-sim), or SDR hardware in isolated lab nodes.
- Database: Postgres (future), currently in-memory for initial scaffold.
- Message bus: Redis/Rabbit (future).

Safety: air-gapped, role-based access, kill-switch for labs.
```

docker-compose.yml
```yaml
version: "3.8"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db/postgres
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"

  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: password
    volumes:
      - db_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    command: ["redis-server", "--save", "900", "1"]

volumes:
  db_data:
```

backend/main.py (FastAPI minimal)
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uuid

app = FastAPI(title="CEW Training Backend (prototype)")

class Scenario(BaseModel):
    id: str = None
    name: str
    description: str = ""
    topology: dict = {}
    constraints: dict = {}

db = {}  # in-memory store for initial prototype

@app.post("/scenarios", response_model=Scenario)
def create_scenario(s: Scenario):
    s.id = str(uuid.uuid4())
    if s.constraints.get("allow_external_network", False):
        raise HTTPException(status_code=400, detail="External network access disabled in prototype")
    db[s.id] = s
    return s

@app.get("/scenarios", response_model=List[Scenario])
def list_scenarios():
    return list(db.values())

@app.get("/scenarios/{scenario_id}", response_model=Scenario)
def get_scenario(scenario_id: str):
    s = db.get(scenario_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return s
```
