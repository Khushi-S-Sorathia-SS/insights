# System Architecture: Employee Dataset Insight Chatbot

## Overview

This document describes the system architecture, data flow, and component interactions for the Employee Dataset Insight Chatbot MVP.

**Core Concept**: Transform CSV data into an interactive AI analyst that answers questions in natural language.

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐   │
│  │  File Upload     │  │  Chat Window     │  │ Visualization  │   │
│  │   Component      │  │   (Messages)     │  │ Engine (Schema)│   │
│  └────────┬─────────┘  └────────┬─────────┘  └────────────────┘   │
│           │                     │                                   │
│           └─────────────────────┼───────────────────────────────┘  │
│                                 │                                   │
│                          HTTP & WebSocket                          │
│                                 │                                   │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   FASTAPI BACKEND (8000)  │
                    │  ┌──────────────────────┐ │
                    │  │ POST /upload         │ │
                    │  │ POST /chat           │ │
                    │  └──────────────────────┘ │
                    └──────────┬────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
      ┌───▼────┐        ┌──────▼──────┐     ┌──────▼──────┐
      │ SESSION │        │  LANGGRAPH  │     │  DAYTONA    │
      │ MANAGER │        │  WORKFLOW   │     │  SANDBOX    │
      │(In-Mem) │        │  (Routing)  │     │ (agent_planner)│
      └────┬────┘        └──────┬──────┘     └──────┬──────┘
           │                    │                    │
           │              ┌─────▼──────────┐        │
           │              │  Intent        │        │
           │              │  Classifier    │        │
           │              └─────┬──────────┘        │
           │                    │                   │
           │                    ├───(Type A)────────┼─────────┐
           │                    │  Direct Response  │         │
           │                    │  (From Context)   │         │
           │                    │                   │         │
           │                    └───(Type B)────────┼─────────┤
           │                       Data Action      │         │
           │                                        │         │
           │                     ┌──────────────────┘         │
           │                     │                            │
           │              ┌──────▼──────────┐                │
           │              │ Agent Planner   │                │
           │              │ (LangChain +    │                │
           │              │  Azure OpenAI)  │                │
           │              └──────┬──────────┘                │
           │                     │                            │
           │              ┌──────▼──────────┐                │
           │              │  Code Generator │                │
           │              │  (Python)       │                │
           │              └──────┬──────────┘                │
           │                     │                            │
           │                     │ (Aggregations/Pandas)      │
           │                     │                            │
           │                     └──────────────────┬─────────┘
           │                                        │
           │                                   ┌────▼──────────┐
           │                                   │ Code Executor │
           │                                   │ + Validator   │
           │                                   └────┬──────────┘
           │                                        │
           │                                   ┌────▼──────────┐
           │                                   │  Pandas       │
           │                                   │  NumPy        │
           │                                   │  (No plots)   │
           │                                   └────┬──────────┘
           │                                        │
           │                     ┌──────────────────┘
           │                     │
           │              ┌──────▼──────────┐
           │              │ Response        │
           │              │ Formatter       │
           │              └──────┬──────────┘
           │                     │
           │        ┌──────────────┼─────────────┐
           │        │              │             │
           └────────┼──────► TEXT  │ CHART SCHEMA│ ERROR MSG
                    │              │             │
                    └──────────────┼─────────────┘
                                   │
                    ┌──────────────▼─────────────┐
                    │  Response to Frontend      │
                    │  (Text + Chart JSON Schema)│
                    └────────────────────────────┘
```

---

## Data Flow: Upload & Chat

### 1. File Upload Flow

```
User selects CSV file
        │
        ▼
┌─────────────────────────────┐
│ Frontend: FileUpload.tsx    │ - Validate file size ≤10MB
│                             │ - Validate file type = .csv
│                             │ - Show progress indicator
└────────────┬────────────────┘
             │
             ▼ POST /upload {file}
        ┌──────────────────────┐
        │ Backend: upload.py   │
        │                      │
        │ 1. Write to /tmp/    │
        │ 2. Read as DataFrame │
        │ 3. Extract metadata  │
        │ 4. Create session    │
        └────────┬─────────────┘
                 │
                 ▼
        ┌──────────────────────┐
        │ SessionManager       │
        │ {                    │
        │   "session_id": xxx, │
        │   "csv_path": yyy,   │
        │   "columns": [...],  │
        │   "dtypes": {...},   │
        │   "chat_history": [] │
        │ }                    │
        └────────┬─────────────┘
                 │
                 ▼
        Return session_id + metadata
        ┌──────────────────────┐
        │ Frontend: Store in   │
        │ React state/cookies  │
        └──────────────────────┘
```

### 2. Chat Query Flow

```
User sends: "Show department salary chart"
        │
        ▼ POST /chat {session_id, message}
    ┌───────────────────────────┐
    │ Backend: chat.py          │
    │ 1. Load session           │
    │ 2. Add to chat_history    │
    └────────┬──────────────────┘
             │
             ▼
    ┌───────────────────────────┐
    │ LangGraph Pipeline        │
    │ (State Machine)           │
    └────────┬──────────────────┘
             │
      ┌──────▼──────┐
      │ Classify    │
      │ Intent      │
      └──────┬──────┘
             │
          ┌──┴──┐
          │     │
       TYPE A  TYPE B
    (Direct)  (Analysis)
          │     │
          │     ▼
          │  ┌─────────────────────┐
          │  │ Agent Planner       │
          │  │ Prompt:             │
          │  │ "Given dataset with │
          │  │  columns [x,y,z],   │
          │  │  write Python code  │
          │  │  to: [user request]"│
          │  └──────┬──────────────┘
          │         │
          │         ▼
          │  ┌─────────────────────┐
          │  │ Code Generation     │
          │  │ (LLM Response)      │
          │  │                     │
          │  │ import pandas as pd │
          │  │ df = pd.read_csv... │
          │  │ result = df.groupby()│
          │  │ print(result.to_json)│
          │  └──────┬──────────────┘
          │         │
          │         ▼
          │  ┌─────────────────────┐
          │  │ Daytona Sandbox     │
          │  │ (agent_planner)     │
          │  │ execute generated   │
          │  │ Python analysis     │
          │  │ code in an isolated │
          │  │ sandbox environment │
          │  └──────┬──────────────┘
          │         │
          ▼         ▼
    ┌──────────────────────────┐
    │ Response Formatter       │
    │ - Parse computed data    │
    │ - Determine chart intent │
    │ - Build JSON Chart Schema│
    └──────┬───────────────────┘
           │
           ▼
    Return to Frontend:
    {
      "role": "assistant",
      "content": "Department salaries:\nIT: $95K",
      "chart_schema": {"type": "bar", "data": [...]}
    }
           │
           ▼
    Frontend renders message
    + generic chart engine renders Schema
```

---

## Component Responsibilities

### Frontend (Next.js)

| Component | Responsibility |
|-----------|-----------------|
| `FileUpload.tsx` | File selection, size validation, drag-drop UX |
| `ChatWindow.tsx` | Message list, input box, loading states |
| `Message.tsx` | Individual message rendering |
| `ChartDisplay.tsx` | Generic visualization engine with predefined registry (bar, line, pie, etc.) |
| `ErrorBoundary.tsx` | Global error display |
| `useChat.ts` | Chat state, message history, API calls |
| `api-client.ts` | HTTP client for /upload, /chat endpoints |
| `socket-client.ts` | WebSocket for real-time updates (optional) |

### Backend (FastAPI)

| Component | Responsibility |
|-----------|-----------------|
| `main.py` | App initialization, CORS, middleware |
| `config.py` | Environment loading, constants, validation |
| `upload.py` | POST /upload handler |
| `chat.py` | POST /chat handler, LangGraph invocation |
| `session_manager.py` | Session CRUD (in-memory dict) |
| `file_manager.py` | CSV storage, cleanup, metadata extraction |

### Workflows (LangGraph)

| Component | Responsibility |
|-----------|-----------------|
| `langgraph_pipeline.py` | StateGraph definition, node orchestration |
| `intent_classifier.py` | Classify query as Type A (direct) or Type B (analysis) |
| `agent_planner.py` | LangChain agent with code generation |
| `response_formatter.py` | Convert computed outputs into standardized chart schema |

### Sandbox (Secure Execution)

| Component | Responsibility |
|-----------|-----------------|
| `backend/workflows/agent_planner.py` | Create a Daytona sandbox, upload the dataset, execute generated Python analysis code, and retrieve computed JSON outputs |

---

## State Management in LangGraph

### State Schema

```python
class PipelineState(TypedDict):
    # Input
    session_id: str
    user_input: str
    
    # Session Data
    dataset_path: str
    columns: list[str]
    chat_history: list[dict]
    
    # Processing
    intent_type: Literal["A", "B"]  # Direct or Analysis
    generated_code: str
    sandbox_output: dict  # {stdout, stderr, computed_data}
    
    # Output
    response_text: str
    chart_schema: Optional[dict]
    error_message: Optional[str]
```

### State Transitions

```
START
  ↓
load_session (fetch session data)
  ↓
classify_intent (determine Type A or B)
  ├─→ (Type A) direct_response (LLM answers from context)
  │     ↓
  │  format_response
  │     ↓
  │  RETURN
  │
  └─→ (Type B) generate_code (Agent → Azure OpenAI)
        ↓
      agent_planner (Create Daytona sandbox, execute analysis code)
        ↓
      format_response (Extract output, determine chart schema)
        ↓
      RETURN
```

---

## Data Models (Pydantic)

### Session

```python
class SessionModel(BaseModel):
    session_id: str
    created_at: datetime
    csv_path: str
    dataset_metadata: DatasetMetadata
    chat_history: list[ChatMessage]
    
    class Config:
        extra = "forbid"
```

### ChatMessage

```python
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    analysis_result: Optional[dict]  # For Type B responses
```

### DatasetMetadata

```python
class DatasetMetadata(BaseModel):
    filename: str
    rows: int
    columns: list[str]
    dtypes: dict[str, str]
    missing_values: dict[str, int]
```

---

## Security & Isolation

### Daytona Sandbox Isolation

The DeepAgents workflow executes generated Python analysis code inside a Daytona sandbox managed by `backend/workflows/agent_planner.py`.

- The dataset is uploaded into the sandbox filesystem prior to execution.
- The sandbox provides runtime isolation from the FastAPI host process.
- Timeouts and execution limits are enforced by the Daytona sandbox runtime.
- Computed data is generated inside the sandbox and retrieved via stdout/files.
- Unsafe host-level access is prevented by sandbox isolation.

### Runtime Protections

- The agent prompt is scoped to data analysis and aggregations.
- Generated code writes data outputs to `/tmp` or stdout inside the sandbox.
- The system captures sandbox execution results and returns text/chart schema to the frontend.

---

## Performance Targets

| Metric | Target | Approach |
|--------|--------|----------|
| Standard response (Type A) | <3 sec | Cache context in Redis (post-MVP) |
| Sandbox response (Type B) | <8 sec | Optimize LLM prompt, efficient pandas queries |
| File upload | < 1 sec | Stream to disk, async metadata extraction |
| Chart rendering | < 5 sec | Dynamic frontend rendering based on JSON schema |
| Concurrent queries | 5-10 | Process queue with asyncio |

---

## Error Handling Strategy

### Error Types & Recovery

```python
# 1. Upload Errors
class UploadError(Exception):
    """File validation failed"""
    - InvalidFileFormat
    - FileTooLarge
    - CorruptedData

# 2. Sandbox Errors
class SandboxError(Exception):
    """Code execution failed"""
    - TimeoutError (20s exceeded)
    - RuntimeError (pandas/matplotlib issue)
    - SecurityError (forbidden import)

# 3. LLM Errors
class LLMError(Exception):
    """Azure OpenAI API failed"""
    - RateLimitError
    - APIError
    - InvalidAPIKey

# 4. Session Errors
class SessionError(Exception):
    """Session management failed"""
    - SessionNotFound
    - SessionExpired
```

### User-Facing Error Messages

```
Sandbox Timeout:
  "The analysis took too long. Please try a simpler query."

Forbidden Import:
  "The generated code contains unsafe operations."

LLM Rate Limit:
  "Too many requests. Please wait a moment and try again."

Invalid CSV:
  "CSV file is invalid or corrupted. Please check format."
```

---

## Scalability Path (Post-MVP)

### Immediate Improvements

```
├─ Redis (Session Caching)
│  ├ Persistent session storage (TTL: 24h)
│  ├ Chat history caching
│  └ Request throttling
│
├─ MongoDB (Audit Logging)
│  ├ All queries logged
│  ├ Execution times tracked
│  └ Error analytics
│
├─ Request Queuing (Celery)
│  ├ Async sandbox execution
│  ├ Rate limiting
│  └ Graceful degradation
│
└─ Multi-Instance Deployment
   ├ Load balancer (nginx)
   ├ Shared session storage
   └ Horizontal scaling
```

---

## Deployment Architecture (MVP = Local)

```
Development Setup:

┌─ Terminal 1: Backend  ──┐
│ python -m uvicorn      │
│ backend.main:app       │
│ --reload               │
│ :8000                  │
└────────────────────────┘

┌─ Terminal 2: Frontend ──┐
│ npm run dev            │
│ next.js dev server     │
│ :3000                  │
└────────────────────────┘

┌─ Shared Resources    ──┐
│ /tmp/uploads/         │
│ (CSV files, charts)    │
│ In-memory sessions     │
└────────────────────────┘
```

---

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pandas Documentation](https://pandas.pydata.org/)
- [Azure OpenAI API](https://learn.microsoft.com/en-us/azure/ai-services/openai/)

---

**Last Updated**: April 2026
**Status**: MVP Architecture
**Version**: 1.0
