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

### Backend

1. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Initialize database:
```bash
alembic upgrade head
```

4. Run the server:
```bash
uvicorn app.main:app --reload
```

### Frontend

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Set up environment variables:
```bash
# Create .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
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

## License

MIT
