# InsightAI — Workforce Intelligence Platform

An AI-powered analytics platform that lets users upload employee CSV datasets and explore them through natural language conversation. Built with a **schema-driven visualization pipeline**, **version-controlled dashboards**, and **secure cloud sandboxing** using LangGraph, DeepAgents, and Azure OpenAI.

## Features

- **CSV Upload with Auto-Insights**: Upload employee datasets (max 10 MB); the system auto-generates 3–4 overview charts and a text summary on ingestion.
- **Natural Language Queries**: Ask questions in plain English; the AI generates Python code, executes it in a cloud sandbox, and returns structured chart schemas.
- **Schema-Driven Visualization**: A generic Recharts rendering engine on the frontend interprets JSON chart schemas (bar, line, pie, area, scatter, radar) without hardcoded chart logic.
- **Persistent Dashboards**: Dashboard state (widgets, layouts, chart data) is stored in PostgreSQL. Dashboards survive page refreshes and can be reloaded by ID.
- **Version-Controlled Dashboards**: Every chat-driven change creates a new dashboard version. Users can view version history and roll back to any previous state.
- **Intelligent Chart Replacement**: Commands like "replace pie chart with bar chart" use LLM-powered intent classification + self-serve agent discovery via a Python sandbox helper to accurately swap charts without hardcoded backend coupling. Falls back to asking the user if ambiguous.
- **Drag-and-Drop Layout**: Native pointer-event based widget repositioning with grid snapping (no external grid library).
- **Secure Sandbox Execution**: All generated Python code runs inside ephemeral Daytona cloud sandboxes — fully isolated from the host. Context and helpers are mounted directly into the sandbox.
- **Semantic Layer**: Chart templates are stored in PostgreSQL (`semantic_definitions` table) and injected into agent prompts so the LLM always produces valid schemas.
- **LangSmith Observability**: Full tracing of every LLM call, intent classification, and pipeline execution via LangSmith.
- **Response Sanitization**: Agent output is stripped of code blocks, file paths, and technical artifacts before reaching the user.
- **Session Management**: Per-user in-memory sessions with configurable TTL and automatic cleanup.

## Tech Stack

| Layer          | Technology                              |
| -------------- | --------------------------------------- |
| Frontend       | Next.js · Recharts · Tailwind CSS      |
| Backend        | FastAPI · SQLAlchemy (async)            |
| Database       | PostgreSQL 15 (via `asyncpg`)           |
| Orchestration  | LangGraph (StateGraph)                  |
| Agent          | DeepAgents · LangChain                  |
| LLM            | Azure OpenAI (`gpt-4.1`)               |
| Sandbox        | Daytona Cloud Sandbox (`langchain-daytona`) |
| Observability  | LangSmith                               |
| Containerisation | Docker Compose                        |

## Architecture

This project uses a **layered deep-agent architecture** with persistent dashboard state.

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                FRONTEND (Next.js + Recharts)                    │
│  ┌────────────┐ ┌─────────────┐ ┌──────────────────────────┐  │
│  │ FileUpload │ │ ChatWindow  │ │  Dashboard (Draggable)   │  │
│  └──────┬─────┘ └──────┬──────┘ └────────────┬─────────────┘  │
│         │              │                     │                  │
│         └──────────────┼─────────────────────┘                  │
│                        │ REST (fetch)                            │
└────────────────────────┼────────────────────────────────────────┘
                         │
          ┌──────────────▼──────────────┐
          │    FastAPI Backend (:8000)   │
          │  /api/upload                │
          │  /api/chat                  │
          │  /api/dashboard/*           │
          └──────────┬──────────────────┘
                     │
   ┌─────────────────┼──────────────────────┐
   │                 │                      │
┌──▼───────┐  ┌──────▼─────────┐  ┌────────▼────────┐
│ Session  │  │   LangGraph    │  │   PostgreSQL    │
│ Manager  │  │   Pipeline     │  │   (asyncpg)     │
│ (in-mem) │  │                │  │                 │
└──────────┘  └──────┬─────────┘  │ datasets        │
                     │            │ dashboards      │
              ┌──────▼──────┐     │ dash_components │
              │   Intent    │     │ semantic_defs   │
              │ Classifier  │     │ query_logs      │
              │ (LangGraph) │     └─────────────────┘
              └──────┬──────┘
                     │
           ┌─────────┴──────────┐
           │                    │
        Type A              Type B
      (Direct)            (Analysis)
           │                    │
    ┌──────▼──────┐     ┌──────▼──────────┐
    │ Lightweight │     │  DeepAgents +   │
    │ NLP Executor│     │  Daytona Sandbox│
    │ (No Charts) │     │  (Charts/Math)  │
    └──────┬──────┘     └──────┬──────────┘
           │                    │
    ┌──────▼────────────────────▼──────┐
    │  Dashboard Manager               │
    │  (version, clone, replace/add)   │
    └──────┬───────────────────────────┘
           │
    ┌──────▼───────────┐
    │ Response to       │
    │ Frontend (JSON)   │
    └──────────────────┘
```

### Data Flow

1. **Upload**: User uploads a CSV → FastAPI saves raw bytes to PostgreSQL `datasets` table → DeepAgents auto-generates 3–4 charts in a Daytona sandbox → chart schemas + insights are persisted as `dashboard_components` linked to a `dashboard` record → response includes `session_id` and `dashboard_id`.
2. **Chat**: User sends a query → LangGraph classifies intent (direct / analysis / replace / create / modify) → For analysis, DeepAgents generates and executes Python code in a Daytona sandbox → agent writes `chart_schemas.json` inside the sandbox → backend retrieves it → a new dashboard version is created (clone + apply changes) → response includes the new `dashboard_id`.
3. **Dashboard Reload**: Frontend stores `dashboard_id` in `localStorage` → on page load, fetches widgets by ID directly from PostgreSQL → dashboard survives refreshes.
4. **Version Rollback**: User views version history → selects a previous version → session's `dashboard_id` is updated → frontend reloads that version's widgets.
5. **Layout Persistence**: User drags/resizes widgets → saves layout → component positions are updated in PostgreSQL.

### Backend Component Responsibilities

| Module | Responsibility |
|--------|----------------|
| `main.py` | FastAPI app, CORS, lifespan (DB init, LangSmith init), exception handlers, router mounting |
| `config.py` | Pydantic Settings from `.env.local`; constants for allowed imports, file types, sandbox limits |
| `routes/upload.py` | `POST /api/upload` — CSV ingestion, auto-insight generation, dashboard creation |
| `routes/chat.py` | `POST /api/chat` — LangSmith-traced chat endpoint, delegates to pipeline |
| `routes/dashboard.py` | Dashboard CRUD: fetch by session/ID, version listing, rollback, layout updates |
| `workflows/pipeline.py` | Core orchestrator: intent routing, agent invocation, dashboard versioning, response assembly |
| `workflows/intent_classifier.py` | LangGraph StateGraph for LLM-based intent classification with keyword fallback |
| `workflows/agent_planner.py` | DeepAgents + Daytona: creates sandbox, uploads CSV and helpers, executes code, retrieves chart schemas |
| `workflows/dashboard_manager.py` | Dashboard versioning: clone, apply chart replacements/additions, update insights |
| `utils/dashboard_helpers.py` | Python utility mounted directly into the agent's sandbox to allow self-serve exploration of existing dashboard schemas without prompt token overload |
| `workflows/response_formatter.py` | Converts sandbox stdout/stderr into structured `ChatResponse` |
| `db/database.py` | SQLAlchemy async engine, session factory, table creation, chart template seeding |
| `db/models.py` | ORM models: `Dataset`, `Dashboard`, `DashboardComponent`, `QueryLog`, `SemanticDefinition` |
| `semantic/semantic_layer.py` | Queries chart templates from DB, formats them as prompt rules for the agent |
| `models/session.py` | Pydantic schemas: `SessionModel`, `DatasetMetadata`, `ChatRequest`, `ChatResponse`, `UploadResponse` |
| `models/dataset.py` | Pydantic schemas: `ColumnInfo`, `DatasetInfo` |
| `storage/file_manager.py` | CSV validation, metadata extraction, persistence to PostgreSQL `datasets` table |
| `storage/session_manager.py` | Thread-safe in-memory session store with TTL expiry |
| `utils/logger.py` | Structured JSON logging |
| `utils/error_handler.py` | Custom exception hierarchy mapped to HTTP status codes |
| `utils/langsmith_tracer.py` | LangSmith tracing decorators and initialization |

### Frontend Component Responsibilities

| Module | Responsibility |
|--------|----------------|
| `pages/index.tsx` | Main layout: coordinates upload, chat, dashboard state; persists `dashboard_id` in localStorage |
| `components/Dashboard.tsx` | Version-controlled widget grid: drag-and-drop via pointer events, version history panel, layout save |
| `components/ChartDisplay.tsx` | Generic Recharts renderer: registry-based rendering for bar, line, pie, area, scatter, radar |
| `components/ChatWindow.tsx` | Chat UI: message bubbles, inline chart previews, loading animation, keyboard shortcuts |
| `components/FileUpload.tsx` | CSV upload trigger with status feedback |
| `utils/api-client.ts` | Typed fetch wrappers for all API endpoints; client-side intent parser for chat commands |

## Project Structure

```text
Insights/
├── backend/                           # FastAPI service layer
│   ├── __init__.py
│   ├── main.py                        # App entry point & lifecycle
│   ├── config.py                      # Environment & credential management
│   ├── requirements.txt               # Python dependencies
│   ├── db/                            # Database layer (PostgreSQL)
│   │   ├── database.py                # Async engine, session factory, init + seed
│   │   ├── models.py                  # SQLAlchemy ORM models
│   │   └── seed.sql                   # SQL seed script (alternative to auto-seed)
│   ├── semantic/                      # Semantic layer
│   │   └── semantic_layer.py          # Chart template retrieval for agent prompts
│   ├── models/                        # Pydantic data schemas
│   │   ├── __init__.py
│   │   ├── dataset.py                 # ColumnInfo, DatasetInfo
│   │   └── session.py                 # SessionModel, ChatRequest/Response, UploadResponse
│   ├── routes/                        # API endpoint definitions
│   │   ├── __init__.py
│   │   ├── chat.py                    # POST /api/chat
│   │   ├── upload.py                  # POST /api/upload
│   │   └── dashboard.py              # Dashboard CRUD & versioning endpoints
│   ├── workflows/                     # LangGraph + DeepAgents pipelines
│   │   ├── __init__.py
│   │   ├── pipeline.py                # Core orchestration & dashboard versioning
│   │   ├── intent_classifier.py       # LangGraph intent classification
│   │   ├── agent_planner.py           # DeepAgents + Daytona sandbox execution
│   │   ├── dashboard_manager.py       # Dashboard clone, replace, add operations
│   │   └── response_formatter.py      # Sandbox output → ChatResponse
│   ├── sandbox/                       # Placeholder (execution handled by agent_planner)
│   │   └── __init__.py
│   ├── storage/                       # Session & file persistence
│   │   ├── __init__.py
│   │   ├── file_manager.py            # CSV validation + PostgreSQL persistence
│   │   └── session_manager.py         # In-memory session store with TTL
│   ├── utils/                         # Shared utilities
│   │   ├── __init__.py
│   │   ├── error_handler.py           # Exception hierarchy → HTTP codes
│   │   ├── langsmith_tracer.py        # LangSmith tracing integration
│   │   └── logger.py                  # Structured JSON logger
│   └── tests/                         # Test suite
│       └── __init__.py
├── frontend/                          # Next.js web interface
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── pages/                         # File-based routes
│   │   ├── _app.tsx
│   │   ├── _document.tsx
│   │   └── index.tsx                  # Main workspace layout
│   ├── components/                    # UI components
│   │   ├── ChartDisplay.tsx           # Generic Recharts renderer
│   │   ├── ChatWindow.tsx             # Chat interface
│   │   ├── Dashboard.tsx              # Draggable, versioned dashboard
│   │   └── FileUpload.tsx             # CSV upload component
│   ├── utils/                         # API client & helpers
│   │   └── api-client.ts             # Typed API wrappers + client-side intent parser
│   ├── styles/
│   │   └── globals.css               # Global styles + glassmorphism theme
│   └── public/                        # Static assets
├── docker/                            # Containerization
│   ├── backend.dockerfile
│   └── frontend.dockerfile
├── scripts/                           # Automation scripts
│   ├── run-local.bat
│   └── setup.bat
├── docker-compose.yml                 # 3-service stack (backend, frontend, postgres)
├── .env.local                         # Environment variables (not committed)
├── .gitignore
├── ARCHITECTURE.md                    # Deep-dive system design
└── README.md                          # This file
```

## Prerequisites

- Python 3.10+
- Node.js 18+ & npm
- PostgreSQL 15+ (or use Docker Compose)
- Azure OpenAI API key ([Azure Portal](https://portal.azure.com/))
- Daytona API key (for sandbox execution)

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd Insights
```

### 2. Set Up Environment Variables

```bash
# Copy example to .env.local and fill in your credentials
cp .env.example .env.local
```

Required variables:
```bash
# Azure OpenAI
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_MODEL_NAME=gpt-4.1
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment

# Daytona Sandbox
DAYTONA_API_KEY=your-daytona-key

# PostgreSQL
POSTGRES_URI=postgresql+asyncpg://postgres:postgres@localhost:5432/insights
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=insights

# LangSmith (optional)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=Insights
```

### 3. Set Up Backend

```bash
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r backend/requirements.txt
```

### 4. Set Up Frontend

```bash
cd frontend
npm install
cd ..
```

## Running Locally

### Option A: Docker Compose (Recommended)

```bash
docker-compose up --build
```

This starts all three services:
- **Backend**: `http://localhost:8000`
- **Frontend**: `http://localhost:3000`
- **PostgreSQL**: `localhost:5433`

### Option B: Manual (3 terminals)

**Terminal 1: PostgreSQL**
```bash
# Ensure PostgreSQL is running locally on port 5432
# Update POSTGRES_URI in .env.local to point to localhost
```

**Terminal 2: Backend**
```bash
venv\Scripts\activate
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 3: Frontend**
```bash
cd frontend
npm run dev
```

- Backend: `http://localhost:8000` · [API Docs](http://localhost:8000/docs)
- Frontend: `http://localhost:3000`

## API Endpoints

### Upload

**POST** `/api/upload`

Upload a CSV file. Creates a session, persists the dataset to PostgreSQL, auto-generates overview charts via Daytona sandbox, and creates a dashboard.

```bash
curl -X POST http://localhost:8000/api/upload -F "file=@employees.csv"
```

**Response:**
```json
{
  "session_id": "sess_abc123",
  "dashboard_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
  "message": "Upload successful",
  "metadata": {
    "filename": "employees.csv",
    "dataset_id": "...",
    "rows": 150,
    "columns": ["Name", "Department", "Salary", "Experience", "Gender"],
    "dtypes": {"Name": "object", "Salary": "float64"},
    "missing_values": {"Name": 0, "Salary": 2},
    "preview_rows": [...]
  },
  "default_chart_schemas": [...],
  "auto_insights": "Key insights from the dataset..."
}
```

### Chat

**POST** `/api/chat`

Send a natural language query with optional pre-parsed intent.

```json
{
  "session_id": "sess_abc123",
  "message": "Replace the pie chart with a bar chart",
  "parsed_command": {
    "intent": "replace",
    "params": {"source_type": "pie", "target_type": "bar"}
  }
}
```

**Response:**
```json
{
  "role": "assistant",
  "content": "The gender distribution is now shown as a bar chart...",
  "chart_schema": {"type": "bar", "title": "...", "data": [...]},
  "dashboard_id": "new-version-uuid",
  "execution_time_ms": 4500
}
```

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/{session_id}` | Fetch dashboard by active session |
| GET | `/api/dashboard/by-id/{dashboard_id}` | Fetch dashboard directly by UUID |
| GET | `/api/dashboard/{session_id}/versions` | List all versions for the dashboard lineage |
| POST | `/api/dashboard/{session_id}/rollback/{dashboard_id}` | Roll back to a specific version |
| POST | `/api/dashboard/{session_id}/layout` | Persist widget positions after drag |

## Intent Classification

The system classifies user messages into five intent types:

| Intent | Examples | Behaviour |
|--------|----------|-----------|
| `direct` | "How many rows?", "What are the columns?" | Fast local execution via `nlp_query_executor.py` (No sandbox, strictly NO charts). |
| `data_query`| "What is the average salary of managers?" | Executed in Daytona Sandbox for complex math, but charts are strictly suppressed. |
| `analysis` | "Show salary by department", "Visualize trends" | Full DeepAgents + Daytona pipeline (Charts generated). |
| `replace` | "Replace pie chart with bar chart" | Agent generates new chart + swaps in dashboard. |
| `create` | "Add a scatter plot of experience vs salary" | Agent generates new chart + appends to dashboard. |
| `modify` | "Change the chart title" | Modifies existing chart properties. |

Intent is classified by a **LangGraph StateGraph** with two nodes:
1. `classify` — LLM-powered extraction via Azure OpenAI
2. `validate` — Normalize chart types, ensure valid intent enum

Falls back to keyword matching if the LLM fails.

## Supported Chart Types

| Type | Recharts Component | Use Case |
|------|-------------------|----------|
| `bar` | `BarChart` + `Bar` | Category comparisons |
| `line` | `LineChart` + `Line` | Trends over time |
| `area` | `AreaChart` + `Area` | Cumulative trends |
| `pie` | `PieChart` + `Pie` | Proportional distributions |
| `scatter` | `ScatterChart` + `Scatter` | Correlations |
| `radar` | `RadarChart` + `Radar` | Multi-dimensional comparisons |

Chart templates are seeded from `db/database.py` into the `semantic_definitions` table and dynamically injected into agent prompts.

## Database Schema

Five PostgreSQL tables managed via SQLAlchemy ORM:

| Table | Purpose |
|-------|---------|
| `datasets` | Raw CSV bytes, schema JSON, version |
| `dashboards` | Dashboard name, layout, version, timestamps |
| `dashboard_components` | Widgets: chart schema, position, type, linked to dashboard |
| `semantic_definitions` | Chart templates, metrics, dimensions (semantic layer) |
| `query_logs` | Execution audit trail: plan, timing, status |

## Configuration

### Key Environment Variables

```bash
# Server
FASTAPI_HOST=127.0.0.1
FASTAPI_PORT=8000
NEXT_PUBLIC_API_URL=http://localhost:8000

# Limits
SANDBOX_TIMEOUT=20              # Seconds per sandbox execution
MAX_UPLOAD_SIZE=10485760         # 10 MB

# Session
SESSION_TIMEOUT_HOURS=24
CLEANUP_INTERVAL_MINUTES=30

# Database
POSTGRES_URI=postgresql+asyncpg://postgres:postgres@localhost:5432/insights
```

## Troubleshooting

### Database connection errors
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Verify POSTGRES_URI in .env.local matches your setup
# For Docker: postgresql+asyncpg://postgres:postgres@postgres:5432/insights
# For local:  postgresql+asyncpg://postgres:postgres@localhost:5432/insights
```

### Daytona sandbox errors
```bash
# Verify DAYTONA_API_KEY is set in .env.local
# Check Daytona service status
# The sandbox cannot access the Docker network — data is uploaded directly as bytes
```

### Azure OpenAI errors
```bash
# Verify API key, endpoint, and deployment name in .env.local
cat .env.local | grep AZURE_OPENAI
```

### Port conflicts
```bash
# Backend: Change FASTAPI_PORT in .env.local
# Frontend: Edit frontend/package.json or use PORT=3001 npm run dev
# PostgreSQL: Mapped to 5433 externally in docker-compose.yml
```

## Documentation

- [Architecture Guide](ARCHITECTURE.md) — Deep-dive system design, data models, state machines
- [API Documentation](http://localhost:8000/docs) — Interactive Swagger explorer
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/) — Workflow framework
- [Recharts Docs](https://recharts.org/) — Chart rendering library
- [Daytona Docs](https://www.daytona.io/docs) — Cloud sandbox platform

## License

MIT License — See LICENSE file

## Contributing

Contributions welcome! Follow the development workflow:
1. Feature branch: `git checkout -b feature/your-feature`
2. Test locally with `docker-compose up`
3. Commit: `git commit -m "feat: description"`
4. Push & open a Pull Request
