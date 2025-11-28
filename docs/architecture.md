# Architecture Overview

Key components:
- Frontend (React): Scenario editor, planner, dashboard, instructor controls.
- Backend (FastAPI): scenario CRUD, sessions, orchestration API, authentication.
- Orchestrator: Lab environment manager that creates isolated training environments.
- Emulation Layer: docker containers (isolated), GNU Radio (software-sim), or SDR hardware in isolated lab nodes.
- Database: SQLite (development), Postgres (production via SQLAlchemy async).
- Message bus: Redis/Rabbit (future).

## Components

### Authentication & Authorization
- JWT-based authentication with role-based access control (RBAC)
- Roles: Admin, Instructor, Trainee
- Audit logging for security compliance

### Scenario Management
- CRUD operations for training scenarios
- JSON/YAML import/export support
- Topology templates for quick setup

### Lab Orchestration
- Isolated lab environments with container and network management
- Safety constraints enforcement (no external network, no real RF)
- Kill switch for emergency shutdown of all labs

Safety: air-gapped, role-based access, kill-switch for labs.
