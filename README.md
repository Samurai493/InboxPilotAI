# InboxPilot AI

A LangGraph-powered inbox copilot that transforms messy inbound emails and messages into structured, reviewable workflows.

## Features

- **Message Classification**: Automatically classify messages by intent (recruiter, scheduling, academic, support, billing, personal, spam)
- **Specialist Routing**: Route messages to domain-specific agents for better reply quality
- **Draft Generation**: Generate context-aware reply drafts tailored to message type
- **Task Extraction**: Automatically extract action items and deadlines
- **Human-in-the-Loop**: Review queue for risky or low-confidence messages
- **Persistent Memory**: User preferences for tone, signature, and reply style
- **Thread History**: View execution timeline and state changes
- **Observability**: LangSmith integration for tracing and evaluation

## Architecture

- **Frontend**: Next.js 14+ with TypeScript and Tailwind CSS
- **Backend**: FastAPI with Python
- **AI Layer**: LangGraph for workflows, LangChain for integrations
- **Database**: PostgreSQL for persistence
- **Observability**: LangSmith for tracing and evaluation

## Setup
Set up python virtual environment
```bash 
python3 -m venv .venv
source .venv/bin/activate

```
### Backend
1. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Set up environment variables in repo root (`backend/.env`):
```bash
# Windows (PowerShell)
./setup-env.ps1

# Linux/WSL
make setup-env
# Create backend/.env manually (at minimum set OPENAI_API_KEY)
```

3. Initialize database (dev behavior):
```bash
# Tables are created automatically on backend startup (dev-friendly).
# If you are using migrations, you can also run:
# alembic upgrade head
```

4. Run the server:
```bash
cd backend
uvicorn app.main:app --reload
```

### Frontendimage.png

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Set up environment variables:
```bash
# Create .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
```

3. Run the development server:
```bash
npm run dev
```

## Usage

1. Navigate to `http://localhost:3000`
2. Paste an email or message
3. View the classified result, draft reply, and extracted tasks
4. Review pending items in the review queue if needed

## Deploy (Cloud Run + Cloud SQL)

This project uses PostgreSQL via `DATABASE_URL` (see `backend/app/config.py`). For Cloud Run, **do not** use `localhost`.

### Cloud SQL instance

- **Instance connection name example**: `inboxpilotai-491403:us-central1:inbox-pilot-ai`
- Create a Postgres database (example: `inboxpilot`) and a user/password.

### Cloud Run configuration

In your Cloud Run service:

- **Connections**: attach the Cloud SQL instance (same instance connection name as above).
- **IAM**: grant the Cloud Run runtime service account `roles/cloudsql.client`.
- **Variables & Secrets**: set `DATABASE_URL` using the Unix-socket format:

```text
DATABASE_URL=postgresql://DB_USER:DB_PASSWORD@/DB_NAME?host=/cloudsql/inboxpilotai-491403:us-central1:inbox-pilot-ai
```

Also set:

- `SECRET_KEY` (used to sign Gmail OAuth state)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI` to your deployed callback, e.g. `https://YOUR_SERVICE_URL/api/v1/gmail/oauth/callback`

### Verify the deployment

- `GET /health` should return `{"status":"healthy"}`
- `POST /api/v1/users/bootstrap` should return a user UUID (requires DB connectivity)
- `GET /api/v1/gmail/oauth/authorize?user_id=<uuid>` should return a Google `authorization_url`

## Project Structure

```
InboxPilotAI/
├── backend/          # FastAPI backend
├── frontend/         # Next.js frontend
├── README.md         # This file
└── docker-compose.yml # Local development setup
```

## Milestones

- ✅ Milestone 1: Foundational MVP
- ✅ Milestone 2: Persistence + Memory
- ✅ Milestone 3: Human Review + Safety
- ✅ Milestone 4: Specialist Routing
- ✅ Milestone 5: Observability + Evaluation
- 🔄 Milestone 6: Real Integrations + Beta Launch (in progress)
- ⏳ Milestone 7: Growth-Ready Productization
