# Architecture Overview

Key components:
- Frontend (React): Scenario editor, planner, dashboard.
- Backend (FastAPI): scenario CRUD, sessions, orchestration API.
- Orchestrator: worker queue to spin up emulated assets (Docker, CORE/Mininet).
- Emulation Layer: docker containers (isolated), GNU Radio (software-sim), or SDR hardware in isolated lab nodes.
- Database: Postgres (future), currently in-memory for initial scaffold.
- Message bus: Redis/Rabbit (future).

Safety: air-gapped, role-based access, kill-switch for labs.
