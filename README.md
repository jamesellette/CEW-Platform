# CEW-Training-Platform

A training-focused Cyber & Electronic Warfare offensive planning platform.

## ⚠️ Safety Notice

**This platform is for TRAINING PURPOSES ONLY in controlled, air-gapped environments.**

- Do NOT connect to operational networks or real-world targets
- Use synthetic target assets and isolated lab infrastructure
- Review the [Safety Checklist](docs/safety_checklist.md) before use
- The platform enforces air-gap and RF safety constraints by default

## Features

- **Scenario Editor**: Create and manage training scenarios with network topologies
- **Lab Orchestration**: Isolated container-based training environments
- **Authentication & RBAC**: JWT-based auth with Admin/Instructor/Trainee roles
- **Instructor Controls**: Real-time lab monitoring and emergency kill switch
- **Audit Logging**: Complete activity tracking for compliance
- **User Management**: Admin panel for user administration

## Documentation

- [Architecture Overview](docs/architecture.md) - System design and components
- [Safety Checklist](docs/safety_checklist.md) - Required safety procedures
- [Operator Guide](docs/operator_guide.md) - Quick-start and operations guide

## Project Structure

- `backend/`: FastAPI service for scenarios & orchestration API
- `frontend/`: React UI for scenario editor, dashboard, and admin panels
- `docker-compose.yml`: Local orchestration for development
- `docs/`: Documentation and safety guidelines

## Running locally

### Backend (without Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
# API available at http://127.0.0.1:8000
```

### Frontend (dev)

```bash
cd frontend
npm install
npm start
# opens at http://localhost:3000
```

### All services via Docker Compose

```bash
docker compose up --build
# stops by Ctrl-C; to run detached: docker compose up -d
```

### Run tests locally

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

## Default Accounts

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Administrator |
| instructor | instructor123 | Instructor |
| trainee | trainee123 | Trainee |

**⚠️ Change default passwords in production!**

## License

MIT