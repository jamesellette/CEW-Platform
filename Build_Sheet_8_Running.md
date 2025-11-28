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
