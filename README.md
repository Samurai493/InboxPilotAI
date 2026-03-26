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

### Prerequisites

- **Python 3.11+** (matches the backend Docker image)
- **Node.js 18+** (frontend)
- **Docker** (recommended): Postgres and Redis for local development

### 1. Python virtual environment

From the repository root:

```bash
python3 -m venv .venv
```

Activate it:

- **Linux / macOS**: `source .venv/bin/activate`
- **Windows (PowerShell)**: `.venv\Scripts\Activate.ps1`

### 2. Start Postgres and Redis (local)

From the repository root:

```bash
docker compose up -d
```

This starts:

- Postgres on `localhost:5432` (user/password/db: `postgres` / `postgres` / `inboxpilot` per `docker-compose.yml`)
- Redis on `localhost:6379`

Stop with `docker compose down` when finished.

### 3. Backend server

```bash
cd backend
pip install -r requirements.txt
```

#### Environment file: `backend/.env`

Configuration is loaded from `backend/.env` (see `backend/app/config.py`). Create the file in one of these ways:

- **Interactive (Windows, PowerShell)** — from repo root:

  ```powershell
  .\setup-env.ps1
  ```

  Use `-Force` to overwrite an existing file.

- **Interactive (Linux / macOS)** — from repo root:

  ```bash
  make setup-env
  ```

These scripts write a minimal `.env` with `OPENAI_API_KEY`, default `DATABASE_URL` / `REDIS_URL` pointing at **localhost**, LangSmith keys, and basic app settings.

**You should extend `backend/.env` for a full local experience** (Google Sign-In, Gmail, correct CORS, and OAuth redirect). Typical additions:

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `openai` (default), `anthropic`, or `google_genai` (Gemini). |
| `LLM_MODEL` | Optional override (e.g. `gpt-4o-mini`, `claude-3-5-sonnet-20241022`, `gemini-1.5-flash`). If unset, defaults per provider. |
| `OPENAI_API_KEY` | Required when `LLM_PROVIDER=openai` (set by setup scripts or manually). |
| `ANTHROPIC_API_KEY` | Required when `LLM_PROVIDER=anthropic`. |
| `GEMINI_API_KEY` | Required when `LLM_PROVIDER=google_genai` (Google AI Studio key for Gemini). |
| `DATABASE_URL` | PostgreSQL URL. Default matches `docker compose` local Postgres. |
| `REDIS_URL` | Redis URL. Default matches `docker compose` local Redis. |
| `SECRET_KEY` | Sign Gmail OAuth state and similar; **change in production**. |
| `GOOGLE_CLIENT_ID` | Google Cloud OAuth client ID (Gmail + optional token verification). |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret. |
| `GOOGLE_REDIRECT_URI` | Must match Google Cloud “Authorized redirect URIs”, e.g. `http://localhost:8000/api/v1/gmail/oauth/callback`. |
| `FRONTEND_URL` | Where the backend redirects the browser after Gmail OAuth (e.g. `http://localhost:3002` if that is your Next dev URL). |
| `CORS_ORIGINS` | JSON array of allowed browser origins, e.g. `["http://localhost:3000","http://localhost:3001","http://localhost:3002"]`. |
| `LANGSMITH_API_KEY` | Optional; tracing in LangSmith. |

Optional: `LANGSMITH_TRACING`, `OPENAI_MODEL` (used when `LLM_MODEL` is unset and provider is OpenAI), `CONFIDENCE_THRESHOLD`, etc.

#### Run the API

```bash
cd backend
uvicorn app.main:app --reload
```

The API defaults to **http://localhost:8000**. Check **http://localhost:8000/health** for `{"status":"healthy"}` and **http://localhost:8000/docs** for OpenAPI.

If the database is unreachable, the process still starts; DB-backed routes fail until `DATABASE_URL` is correct and Postgres is running.

### 4. Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local` (see [frontend/README.md](frontend/README.md)):

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
```

```bash
npm run dev
```

Use the dev URL shown in the terminal (often port 3000; Next may pick 3001/3002 if busy). Ensure that URL is listed in backend `CORS_ORIGINS` and in Google Cloud **Authorized JavaScript origins** if you use Google Sign-In.

### 5. All-in-one with Docker (optional)

`docker-compose.yml` includes a `backend` service that builds `./backend`, depends on Postgres and Redis, and reads `./backend/.env`. After creating `backend/.env` and running `docker compose up --build` from the repo root, the API is available on port **8000** with `DATABASE_URL` / `REDIS_URL` overridden for the compose network.

## Usage

1. Open the frontend URL from `npm run dev`.
2. Sign in with Google (if configured), connect Gmail when prompted, or use flows that do not require Gmail (e.g. paste text on `/inbox` depending on your build).
3. View classified results, drafts, and extracted tasks where the UI exposes them; use the review queue as needed.

## Deploy (Cloud Run + Cloud SQL)

This project uses PostgreSQL via `DATABASE_URL` (see `backend/app/config.py`). For Cloud Run, **do not** use `localhost` for the database.

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
- `FRONTEND_URL` to your deployed frontend origin (for post–Gmail OAuth redirect)
- `CORS_ORIGINS` to include your frontend origin

### Verify the deployment

- `GET /health` should return `{"status":"healthy"}`
- `POST /api/v1/users/bootstrap` should return a user UUID (requires DB connectivity)
- `GET /api/v1/gmail/oauth/authorize?user_id=<uuid>` should return a Google `authorization_url`

## Project Structure

```
InboxPilotAI/
├── backend/           # FastAPI backend
├── docs/              # Architecture notes (e.g. multi-agent workflow)
├── frontend/          # Next.js frontend
├── README.md          # This file
├── docker-compose.yml # Local Postgres + Redis (+ optional backend)
├── setup-env.ps1      # Windows helper to create backend/.env
└── Makefile           # `make setup-env` for Unix-like systems
```

See [docs/MULTI_AGENT_WORKFLOW.md](docs/MULTI_AGENT_WORKFLOW.md) for how classifier routing and specialist nodes fit together.

## Milestones

- ✅ Milestone 1: Foundational MVP
- ✅ Milestone 2: Persistence + Memory
- ✅ Milestone 3: Human Review + Safety
- ✅ Milestone 4: Specialist Routing
- ✅ Milestone 5: Observability + Evaluation
- 🔄 Milestone 6: Real Integrations + Beta Launch (in progress)
- ⏳ Milestone 7: Growth-Ready Productization
