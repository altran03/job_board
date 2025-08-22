# Smart Job Application Tracker

Automates and organizes the job hunt with Gmail parsing, Google Calendar reminders, and insights. Built with Python/FastAPI, React (Vite), and PostgreSQL.

## Stack
- Backend: FastAPI, Uvicorn, Pydantic Settings
- Frontend: React + TypeScript (Vite)
- DB: PostgreSQL (coming soon via SQLModel/SQLAlchemy + Alembic)
- Integrations: Gmail API, Google Calendar API, Notion API (planned)

## Quickstart

### Docker (recommended for easy startup)

```bash
# Build images and start services
docker compose up --build

# Stop
docker compose down
```

- API: http://localhost:8000/health
- Web: http://localhost:5173
- Postgres: localhost:5432 (jobtracker/jobtracker)

### Prerequisites
- Python 3.10+
- Node 18+
- GitHub repo set up (already configured)

### Setup
```bash
# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### Run the app
```bash
cd frontend
npm run dev
```
- API: http://localhost:8000/health
- Web: http://localhost:5173

## Roadmap
- Auth & user accounts
- Job application model + CRUD
- Gmail integration: parse recruiter emails, auto-log applications
- Google Calendar integration: create events/reminders for interviews/OAs
- Notion sync (optional): mirror applications to a Notion database
- Analytics dashboard: response rate, company segments, timelines

## Development
- Linting/formatting (to add): Ruff/Black for Python, ESLint/Prettier for web
- DB migrations (to add): Alembic scripts
- Env config: use .env (examples to follow)

## Learning Goals
- Real-world API integrations (OAuth 2.0, webhooks/polling)
- Background jobs and rate limits
- Full-stack typing and validation
- CI/CD basics
