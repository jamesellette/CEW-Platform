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
- Integrate safe tools: CORE/Mininet for IP topologies, GNU Radio.
- Add instructor controls & kill switch.

---
