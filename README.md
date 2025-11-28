# CEW-Training-Platform

A training-focused Cyber & Electronic Warfare offensive planning platform.

## Notes

- This project is intended for training in controlled, air-gapped, and open environments.
- Do NOT connect to operational networks or real-world targets, without acknowledging the risks.
- Use synthetic target assets and isolated lab infrastructure.

## Starter scaffold

- `backend/`: FastAPI service for scenarios & orchestration API.
- `frontend/`: React UI placeholder for scenario editor and planner.
- `docker-compose.yml`: local orchestration for dev.

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

## License

MIT