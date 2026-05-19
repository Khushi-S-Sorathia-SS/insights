# Backend Refactor: Architecture, Quality & Structure

## Overview

A comprehensive refactor of the `Insights` backend to enforce clean architecture, strict configuration management, proper logging, absolute imports, structured LangChain patterns, and a `src/app/` package layout. The frontend is untouched. Docker is fully removed. The repo split will be done manually — this plan only covers the code changes.

---

## User Review Required

> [!IMPORTANT]
> The `POSTGRES_URI` in `.env.local` currently uses the Docker hostname `postgres:5432`. After Docker removal, it must be changed to `localhost:5432`. The new `backend/.env` will reflect this. Confirm your local Postgres port is `5432`.

> [!WARNING]
> The `display_name` column in the `datasets` table will become `NOT NULL`. Any existing rows with a null `display_name` will need to be manually patched before running migrations, or they will violate the constraint. Check your local DB before this change is applied.

> [!IMPORTANT]
> After the restructure, the backend run command changes from:
> `python -m uvicorn backend.main:app`
> to:
> `python -m uvicorn src.app.main:app`
> Run from inside the `backend/` directory with the venv active.

---

## Proposed Changes

---

### Phase 1 — Delete Dead Code & Docker

#### [DELETE] `backend/sandbox/executor.py`
Unused dead code. The Daytona path via `agent_planner.py` is the only active execution path.

#### [DELETE] `docker-compose.yml`
Docker orchestration is being removed entirely.

#### [DELETE] `docker/backend.dockerfile`

#### [DELETE] `docker/frontend.dockerfile`

#### [DELETE] `docker/` directory (will be empty after above)

#### [MODIFY] `README.md` and `ARCHITECTURE.md`
Remove all Docker references, update run instructions to reflect local venv + local Postgres.

---

### Phase 2 — New Folder Structure (Backend `src/app/`)

Create the new directory tree inside `backend/`:

```
backend/
├── requirements.txt           ← stays here
├── src/
│   └── app/
│       ├── __init__.py        ← NEW
│       ├── main.py            ← MOVED from backend/main.py
│       ├── config/
│       │   ├── __init__.py    ← NEW
│       │   ├── settings.py    ← MOVED/RENAMED from backend/config.py
│       │   └── app_config.py  ← NEW (plain class constants)
│       ├── prompts/
│       │   ├── __init__.py    ← NEW
│       │   ├── agent_system_prompt.py    ← NEW (extracted from agent_planner.py)
│       │   ├── intent_classification.py  ← NEW (extracted from intent_classifier.py)
│       │   └── chart_templates.py        ← NEW (extracted from database.py)
│       ├── agents/
│       │   ├── __init__.py    ← NEW
│       │   └── agent_planner.py   ← MOVED from backend/workflows/agent_planner.py
│       ├── workflows/
│       │   ├── __init__.py    ← NEW
│       │   ├── pipeline.py        ← MOVED
│       │   ├── dashboard_manager.py ← MOVED
│       │   ├── intent_classifier.py ← MOVED
│       │   ├── nlp_query_executor.py ← MOVED
│       │   └── response_formatter.py ← MOVED
│       ├── routes/
│       │   ├── __init__.py    ← NEW
│       │   ├── chat.py        ← MOVED
│       │   ├── upload.py      ← MOVED
│       │   ├── dashboard.py   ← MOVED
│       │   └── datasets.py    ← MOVED
│       ├── db/
│       │   ├── __init__.py    ← NEW
│       │   ├── database.py    ← MOVED
│       │   └── models.py      ← MOVED
│       ├── models/
│       │   ├── __init__.py    ← NEW
│       │   ├── session.py     ← MOVED
│       │   └── dataset.py     ← MOVED
│       ├── storage/
│       │   ├── __init__.py    ← NEW
│       │   ├── file_manager.py   ← MOVED
│       │   └── session_manager.py ← MOVED
│       ├── semantic/
│       │   ├── __init__.py    ← NEW
│       │   └── semantic_layer.py ← MOVED
│       └── utils/
│           ├── __init__.py    ← NEW
│           ├── error_handler.py    ← MOVED
│           ├── logger.py          ← MOVED
│           ├── langsmith_tracer.py ← MOVED
│           └── dashboard_helpers.py ← MOVED
```

The old flat directories under `backend/` (`workflows/`, `routes/`, `db/`, etc.) are removed once content is migrated.

---

### Phase 3 — `config/settings.py` (was `backend/config.py`)

#### [MODIFY] `backend/src/app/config/settings.py`

**Changes:**
- Add `LLM_TEMPERATURE_AGENT`, `LLM_TEMPERATURE_CLASSIFIER`, `LLM_TEMPERATURE_NLP` as env-driven fields
- Add `PREVIEW_ROWS_COUNT: int = 5` as env-driven field
- `ALLOWED_ORIGINS` already reads from env — keep as-is
- Change `extra = "ignore"` → `extra = "forbid"`
- Remove module-level constants (`ALLOWED_CSV_COLUMNS`, `ALLOWED_IMPORTS`, `FORBIDDEN_IMPORTS`, `MAX_UPLOAD_SIZE_MB`, `DEFAULT_SANDBOX_TIMEOUT`, etc.) — these move to `AppConfig`
- Remove hardcoded `os.getenv()` calls inside field defaults — Pydantic settings handles this natively via `env_file`
- Fix `Settings()` direct instantiation in `intent_classifier.py` and `nlp_query_executor.py` → use `get_settings()`

```python
# New fields to add
LLM_TEMPERATURE_AGENT: float = 0.1
LLM_TEMPERATURE_CLASSIFIER: float = 0.0
LLM_TEMPERATURE_NLP: float = 0.0
PREVIEW_ROWS_COUNT: int = 5

# Grid layout constants (env-driven)
GRID_COLUMNS: int = 12
DEFAULT_WIDGET_WIDTH: int = 6
DEFAULT_WIDGET_HEIGHT: int = 4
INSIGHT_WIDGET_HEIGHT: int = 3

class Config:
    env_file = "backend/.env"
    case_sensitive = True
    extra = "forbid"
```

---

### Phase 4 — `config/app_config.py` (NEW)

#### [NEW] `backend/src/app/config/app_config.py`

A plain Python class. Not Pydantic. Not env-driven. Pure static constants.

```python
class AppConfig:
    # File validation
    ALLOWED_FILE_TYPES = {".csv"}
    ALLOWED_CSV_COLUMNS = {"name", "id", "employee_id", ...}

    # Sandbox security
    ALLOWED_IMPORTS = {"pandas", "numpy", "matplotlib", "io", "base64", "json"}
    FORBIDDEN_IMPORTS = {"os", "sys", "subprocess", "requests", ...}

    # Sandbox defaults
    DEFAULT_SANDBOX_TIMEOUT = 20
    DEFAULT_SANDBOX_MEMORY_LIMIT = "512M"

    # Dataset preview
    PREVIEW_ROWS_COUNT = 5

    # Dashboard grid defaults
    GRID_COLUMNS = 12
    DEFAULT_WIDGET_WIDTH = 6
    DEFAULT_WIDGET_HEIGHT = 4
    INSIGHT_WIDGET_HEIGHT = 3
```

---

### Phase 5 — `prompts/` Modules (NEW)

#### [NEW] `backend/src/app/prompts/agent_system_prompt.py`

Extracts the large f-string system prompt from `agent_planner.py` into a helper function:

```python
def get_agent_system_prompt(dataset, sandbox_path: str, chart_rules: str,
                             current_widgets_summary: list) -> str:
    return f"""You are an expert data analyst..."""
```

#### [NEW] `backend/src/app/prompts/intent_classification.py`

Extracts `INTENT_PROMPT` from `intent_classifier.py`:

```python
INTENT_PROMPT = """You are an expert at parsing user commands..."""
```

#### [NEW] `backend/src/app/prompts/chart_templates.py`

Extracts `CHART_TEMPLATE_SEEDS` from `database.py`:

```python
CHART_TEMPLATE_SEEDS = [
    {"name": "bar", "definition_json": {...}},
    ...
]
```

---

### Phase 6 — `agents/agent_planner.py` (MOVED + REFACTORED)

#### [MODIFY] `backend/src/app/agents/agent_planner.py`

**Changes:**
- Update all imports to absolute: `from src.app.config.settings import get_settings`
- Use `settings.LLM_TEMPERATURE_AGENT` instead of hardcoded `0.1`
- Use `get_system_prompt(...)` from `src.app.prompts.agent_system_prompt`
- Replace dict-based messages with LangChain types:
  ```python
  # Before
  {"role": "user", "content": user_message}
  # After
  HumanMessage(content=user_message)
  ```
- Fix silent exception in sandbox cleanup:
  ```python
  # Before
  except Exception:
      pass
  # After
  except Exception as e:
      logger.error(f"Sandbox cleanup failed: {e}")
  ```
- Replace `print()` calls with `logger.debug()` / `logger.info()`
- Remove regex-based response parsing where possible (agent returns structured output)

---

### Phase 7 — `workflows/intent_classifier.py` (MOVED + REFACTORED)

#### [MODIFY] `backend/src/app/workflows/intent_classifier.py`

**Changes:**
- Absolute imports
- Use `get_settings()` instead of `Settings()` direct call
- Use `settings.LLM_TEMPERATURE_CLASSIFIER`
- Import `INTENT_PROMPT` from `src.app.prompts.intent_classification`
- Replace `JsonOutputParser` with `PydanticOutputParser`
- Convert `ParsedCommand` to a Pydantic model:
  ```python
  class ParsedCommand(BaseModel):
      intent: IntentType
      params: Dict[str, Any]
  ```
- Remove `to_dict()` — callers use `.model_dump()`
- `fallback_classification()` returns a `ParsedCommand` instance, not a raw dict
- Chart type mappings move to `AppConfig`
- Keyword lists move to `AppConfig`

---

### Phase 8 — `workflows/nlp_query_executor.py` (MOVED + REFACTORED)

#### [MODIFY] `backend/src/app/workflows/nlp_query_executor.py`

**Changes:**
- Absolute imports
- Use `get_settings()` instead of `Settings()` direct call
- Use `settings.LLM_TEMPERATURE_NLP`
- Move `PROMPT_TEMPLATE` to `src.app.prompts.intent_classification` or keep inline (it's NLP-specific, so keep inline is fine)

---

### Phase 9 — `db/database.py` (MOVED + REFACTORED)

#### [MODIFY] `backend/src/app/db/database.py`

**Changes:**
- Absolute imports
- Remove `CHART_TEMPLATE_SEEDS` → import from `src.app.prompts.chart_templates`
- Replace all `print()` calls with `logger.info()`

---

### Phase 10 — `storage/file_manager.py` (MOVED + REFACTORED)

#### [MODIFY] `backend/src/app/storage/file_manager.py`

**Changes:**
- Absolute imports
- Replace `df.head(5)` literal with `AppConfig.PREVIEW_ROWS_COUNT`
- Remove fallback: change `display_name: str = None` → `display_name: str` (mandatory)
- Remove `display_name or filename` pattern

---

### Phase 11 — `routes/upload.py` (MOVED + REFACTORED)

#### [MODIFY] `backend/src/app/routes/upload.py`

**Changes:**
- Absolute imports
- Replace all `print()` calls with `logger.info()` / `logger.error()`
- Replace hardcoded grid values with `AppConfig` constants:
  ```python
  # Before
  x = (i % 2) * 6
  y = (i // 2) * 4
  position={"x": 0, "y": final_y, "w": 12, "h": 3}

  # After
  x = (i % 2) * AppConfig.DEFAULT_WIDGET_WIDTH
  y = (i // 2) * AppConfig.DEFAULT_WIDGET_HEIGHT
  position={"x": 0, "y": final_y, "w": AppConfig.GRID_COLUMNS, "h": AppConfig.INSIGHT_WIDGET_HEIGHT}
  ```
- Move upload initial analysis prompt (the `generate_analysis_code` call string) to `src.app.prompts.agent_system_prompt` as a constant `INITIAL_ANALYSIS_PROMPT`
- Clean up the component insert loop (single `db.commit()` remains at the end — already correct, just clean up dead tracking variables `current_y`, `row_height` that are computed but never used correctly)

---

### Phase 12 — `db/models.py` (MOVED + REFACTORED)

#### [MODIFY] `backend/src/app/db/models.py`

**Changes:**
- Absolute imports
- Change `display_name = Column(String, unique=True, nullable=True)` → `nullable=False`

---

### Phase 13 — `routes/datasets.py` (MOVED + REFACTORED)

#### [MODIFY] `backend/src/app/routes/datasets.py`

**Changes:**
- Absolute imports
- Remove `display_name or filename` fallback:
  ```python
  # Before
  "display_name": d.display_name or d.filename,
  # After
  "display_name": d.display_name,
  ```

---

### Phase 14 — All Other Moved Files (Import Updates Only)

#### [MODIFY] `backend/src/app/workflows/pipeline.py`
- Absolute imports
- Update `ParsedCommand` usage: `to_dict()` → `.model_dump()`

#### [MODIFY] `backend/src/app/workflows/dashboard_manager.py`
- Absolute imports only

#### [MODIFY] `backend/src/app/routes/chat.py`
- Absolute imports only

#### [MODIFY] `backend/src/app/routes/dashboard.py`
- Absolute imports only

#### [MODIFY] `backend/src/app/semantic/semantic_layer.py`
- Absolute imports only

#### [MODIFY] `backend/src/app/utils/error_handler.py`
- No logic changes, absolute imports

#### [MODIFY] `backend/src/app/utils/logger.py`
- Absolute imports only

#### [MODIFY] `backend/src/app/utils/langsmith_tracer.py`
- Absolute imports only

#### [MODIFY] `backend/src/app/utils/dashboard_helpers.py`
- Absolute imports only

#### [MODIFY] `backend/src/app/storage/session_manager.py`
- Absolute imports only

#### [MODIFY] `backend/src/app/models/session.py`
- No changes (already uses absolute-style Pydantic, no relative imports)

---

### Phase 15 — ENV Files

#### [NEW] `backend/.env`
Backend-only env file. Clean, no Docker keys, updated Postgres URI.

```env
# App
FASTAPI_HOST=127.0.0.1
FASTAPI_PORT=8000
FASTAPI_ENV=development
DEBUG=true

# Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_MODEL_NAME=gpt-4.1
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1-khushi

# LLM Temperatures
LLM_TEMPERATURE_AGENT=0.1
LLM_TEMPERATURE_CLASSIFIER=0
LLM_TEMPERATURE_NLP=0

# LangSmith
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=Insights

# Daytona
DAYTONA_API_KEY=...

# Database (local Postgres)
POSTGRES_URI=postgresql+asyncpg://postgres:postgres@localhost:5432/insights

# Sandbox
SANDBOX_TIMEOUT=20
MAX_UPLOAD_SIZE=10485760

# Session
SESSION_TIMEOUT_HOURS=24
CLEANUP_INTERVAL_MINUTES=30

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Frontend URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Grid Layout
GRID_COLUMNS=12
DEFAULT_WIDGET_WIDTH=6
DEFAULT_WIDGET_HEIGHT=4
INSIGHT_WIDGET_HEIGHT=3

# Dataset
PREVIEW_ROWS_COUNT=5
```

#### [NEW] `frontend/.env`
Frontend-only env file.

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### [DELETE] `.env.local` (root-level)
Replaced by the two separate env files above.

---

### Phase 16 — `backend/src/app/main.py` Updates

#### [MODIFY] `backend/src/app/main.py`

**Changes:**
- Absolute imports (`from src.app.config.settings import get_settings`, etc.)
- Update `env_file` path in Settings config to `backend/.env`
- No structural changes needed

---

## Files Touched Summary

| File | Action | Key Change |
|---|---|---|
| `backend/sandbox/executor.py` | DELETE | Dead code |
| `docker-compose.yml` | DELETE | Docker removal |
| `docker/backend.dockerfile` | DELETE | Docker removal |
| `docker/frontend.dockerfile` | DELETE | Docker removal |
| `backend/config.py` | MOVE+MODIFY | → `src/app/config/settings.py`, add LLM temps, `extra="forbid"` |
| `backend/main.py` | MOVE+MODIFY | → `src/app/main.py`, absolute imports |
| `backend/workflows/agent_planner.py` | MOVE+MODIFY | → `src/app/agents/`, HumanMessage, logger, prompt extracted |
| `backend/workflows/intent_classifier.py` | MOVE+MODIFY | → `src/app/workflows/`, PydanticParser, ParsedCommand as Pydantic |
| `backend/workflows/nlp_query_executor.py` | MOVE+MODIFY | → `src/app/workflows/`, get_settings() |
| `backend/workflows/pipeline.py` | MOVE+MODIFY | → `src/app/workflows/`, .model_dump() |
| `backend/workflows/dashboard_manager.py` | MOVE | → `src/app/workflows/` |
| `backend/db/database.py` | MOVE+MODIFY | → `src/app/db/`, CHART_TEMPLATE_SEEDS extracted, print→logger |
| `backend/db/models.py` | MOVE+MODIFY | → `src/app/db/`, display_name NOT NULL |
| `backend/routes/upload.py` | MOVE+MODIFY | → `src/app/routes/`, AppConfig constants, print→logger, prompt extracted |
| `backend/routes/chat.py` | MOVE | → `src/app/routes/` |
| `backend/routes/dashboard.py` | MOVE | → `src/app/routes/` |
| `backend/routes/datasets.py` | MOVE+MODIFY | → `src/app/routes/`, remove display_name fallback |
| `backend/storage/file_manager.py` | MOVE+MODIFY | → `src/app/storage/`, AppConfig.PREVIEW_ROWS_COUNT, mandatory display_name |
| `backend/storage/session_manager.py` | MOVE | → `src/app/storage/` |
| `backend/semantic/semantic_layer.py` | MOVE | → `src/app/semantic/` |
| `backend/utils/*.py` (all 4) | MOVE | → `src/app/utils/` |
| `backend/models/session.py` | MOVE | → `src/app/models/` |
| `backend/models/dataset.py` | MOVE | → `src/app/models/` |
| `src/app/config/app_config.py` | NEW | Plain constants class |
| `src/app/prompts/agent_system_prompt.py` | NEW | Dynamic prompt function + `INITIAL_ANALYSIS_PROMPT` |
| `src/app/prompts/intent_classification.py` | NEW | `INTENT_PROMPT` constant |
| `src/app/prompts/chart_templates.py` | NEW | `CHART_TEMPLATE_SEEDS` data |
| `backend/.env` | NEW | Backend-only env (localhost Postgres) |
| `frontend/.env` | NEW | Frontend-only env |
| `.env.local` | DELETE | Replaced by split env files |
| `README.md` / `ARCHITECTURE.md` | MODIFY | Remove Docker refs |

**Total: ~30 files modified/created, 5 deleted**

---

## Verification Plan

### Automated
1. Start local Postgres on `localhost:5432` with DB `insights`
2. Run from `backend/` with venv active:
   ```bash
   python -m uvicorn src.app.main:app --reload
   ```
3. Confirm startup logs show DB initialization, no import errors
4. Hit `GET /health` → `{"status": "healthy"}`
5. Hit `GET /docs` → Swagger UI loads

### Manual
- Upload a CSV → verify dashboard generates
- Send a chat message → verify Daytona sandbox executes
- Verify `logger` output instead of `print` in terminal
- Verify no `extra = "ignore"` silently swallowing typos — test by adding a bogus env key

