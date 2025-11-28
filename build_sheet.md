# CEW Platform — Build Sheet (start-to-finish)

This build sheet consolidates the project scaffold, safety controls, development instructions, CI, and initial issue/milestone plan so you can pick up work from a single authoritative source. Follow the steps in order. Do not run anything on production networks — this is a training/emulation platform and must be deployed only in air-gapped labs.

---

## Summary / Purpose
Create a Cyber & Electronic Warfare (CEW) offensive planning and training platform. This document describes:
- repository layout and initial files
- exact commands to create and populate the repo
- how to run locally (dev + docker)
- CI configuration and tests
- milestones / issues to track progress
- recommended next steps and safety checklist

Repository name (as requested): `CEW-Platform`  
Repository owner: your account (example: `jamesellette`)  
Visibility: Public

---

## Safety & Legal
- This project is for training in isolated, controlled, air-gapped, and open environments.
- Never connect the lab to production networks or the Internet.
- Use synthetic targets and payloads, unless explicit authorization has been granted for testing against a target.
- All actions must be auditable with logs and instructor oversight.
- Include a kill switch in orchestration to immediately stop any running emulated assets.

---

## Branching & Workflow
- Default branch: `main`
- Feature branches: `feature/<short-desc>` (e.g., `feature/scenario-editor`)
- Pull requests must pass CI (lint + tests) before merge.

---

## Top-level repo layout (initial)
- README.md
- LICENSE
- .gitignore
- docker-compose.yml
- docs/
  - architecture.md
- backend/
  - main.py
  - requirements.txt
  - requirements-dev.txt
  - tests/
    - test_main.py
- frontend/
  - package.json
  - src/
    - index.js
    - App.js
    - App.test.js
- .github/
  - workflows/
    - ci.yml

---

## Initial file contents (copy these, or make improvements)

README.md (brief)
```markdown
# CEW-Training-Platform

A training-focused Cyber & Electronic Warfare offensive planning platform.

Notes:
- This project is intended for training in controlled, air-gapped, and open environments.
- Do NOT connect to operational networks or real-world targets, without acknowledging the risks.
- Use synthetic target assets and isolated lab infrastructure.

Starter scaffold:
- backend/: FastAPI service for scenarios & orchestration API.
- frontend/: React UI placeholder for scenario editor and planner.
- docker-compose.yml: local orchestration for dev.

License: MIT
```

docs/architecture.md (brief)
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

backend/requirements.txt
```
fastapi
uvicorn
pydantic
```

backend/requirements-dev.txt
```
pytest
requests
flake8
```

backend/tests/test_main.py
```python
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_list_scenarios_empty():
    r = client.get("/scenarios")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert r.json() == []
```

frontend/package.json
```json
{
  "name": "cew-training-frontend",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "axios": "^1.4.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test --watchAll=false"
  }
}
```

frontend/src/index.js
```javascript
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

const container = document.getElementById('root') || document.createElement('div');
container.id = 'root';
document.body.appendChild(container);

const root = createRoot(container);
root.render(<App />);
```

frontend/src/App.js
```javascript
import React from 'react';

export default function App() {
  return (
    <div>
      <h1>CEW Training Platform</h1>
      <p>Frontend placeholder.</p>
    </div>
  );
}
```

frontend/src/App.test.js
```javascript
import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders platform title', () => {
  render(<App />);
  expect(screen.getByText(/CEW Training Platform/i)).toBeInTheDocument();
});
```

.github/workflows/ci.yml (CI — lint + unit tests + docker build)
```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install backend deps
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-dev.txt
      - name: Lint Python
        run: |
          flake8 backend || true
      - name: Run backend tests
        working-directory: backend
        run: pytest -q

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install frontend deps
        working-directory: frontend
        run: npm ci
      - name: Build frontend
        working-directory: frontend
        run: npm run build --if-present
      - name: Run frontend tests
        working-directory: frontend
        run: npm test --if-present

  docker-compose:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      - name: Build docker-compose services
        run: docker compose -f docker-compose.yml build --progress=plain
```

---

## Commands: create repo (local & push)
Option 1 — Using GitHub CLI (recommended)
```bash
# create local folder and initialize
mkdir CEW-Platform
cd CEW-Platform
git init

# create files (use your editor to paste content from above), then:
git add .
git commit -m "Initial CEW Platform scaffold"

# create remote repo on GitHub (private)
gh repo create jamesellette/CEW-Platform --private --description "CEW Training Platform" --source=. --remote=origin --push
```

Option 2 — Create repo via GitHub web UI, then clone:
```bash
git clone git@github.com:jamesellette/CEW-Platform.git
cd CEW-Platform
# add files, commit, push
git add .
git commit -m "Initial scaffold"
git push origin main
```

---

## How to run locally (dev)
Backend (without Docker)
```bash
# optional: create virtualenv
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
# API available at http://127.0.0.1:8000
```

Frontend (dev)
```bash
cd frontend
npm install
npm start
# opens at http://localhost:3000
```

All services via Docker Compose
```bash
docker compose up --build
# stops by Ctrl-C; to run detached: docker compose up -d
```

Run tests locally
```bash
# backend tests
cd backend
pip install -r requirements-dev.txt
pytest -q

# frontend tests
cd frontend
npm ci
npm test
```

---

## Initial milestones & issues (high level)
Create these issues/milestones in your repo (titles are recommended exactly):

- M0: Milestone M0: Scaffold Verification and Initial Setup
  - Verify all initial files present and that backend & frontend start.
- M1: Scenario Editor (spec & frontend stub)
  - Define schema, simple UI form, backend endpoints.
- M2: Local Orchestration: Isolated Lab Environments (docker-compose)
  - Add host images / sample topologies, enforce air-gap.
- M3: Authentication, RBAC, and Audit Logging (Backend)
  - Add user model + JWT or similar + audit trail.
- M3: Continuous Integration: Linting, Tests, and Build (already scaffolded by CI file)
- M3: Documentation & Safety Checklist

(You can create these via GitHub UI or `gh issue create`.)

---

## Acceptance criteria (initial)
- Backend FastAPI endpoints are reachable and pass unit tests.
- Frontend builds and unit test passes.
- Docker Compose builds services successfully and does not allow external network egress from the lab containers.
- README and docs contain clear safety guidance.

---

## Suggested next development tasks
- Implement DB (Postgres) models and migrations (Alembic).
- Add auth + RBAC (JWT + role middleware).
- Build Scenario Editor UI: form + JSON/YAML export/import.
- Implement orchestrator worker (Celery/RQ) to spin up isolated containers for scenarios.
- Integrate safe emulation tools: CORE/Mininet for IP topologies, GNU Radio for RF simulation (software-only imports).
- Add instructor controls & kill switch.

---

## Development tips & gotchas
- Keep all emulation containers on user-defined bridge networks with no external gateway — test with `docker network inspect` to confirm.
- For RF simulation, start with software-only GNU Radio flows in VM or container, never use physical SDR without locked lab nodes and signed authorization.
- Make unit tests deterministic and mock any “destructive” simulation effects.

---

## If you want me to push files
If you later re-grant push rights or re-authorize, I can push this scaffold and/or create the GitHub issues/milestones automatically.

---

If you want, I can also:
- produce a single ZIP you can download containing the full scaffold,
- or output every file in the repo here in code blocks so you can copy/paste.

Which would you prefer next?
