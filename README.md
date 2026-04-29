# Employee Dataset Insight Chatbot (MVP v1.0)

An AI-powered chatbot that allows users to upload employee CSV datasets and ask natural language questions about the data using LangGraph, LangChain, and Gemini 2.5 Flash.

## Features

- **CSV Upload**: Upload employee datasets with validation (max 10MB)
- **Natural Language Queries**: Ask questions in plain English
- **Dynamic Analysis**: AI-generated Python code for data analysis
- **Chart Generation**: Automatic visualization generation
- **Secure Sandbox**: Isolated code execution with timeout protection
- **Session Management**: Per-user session context and chat history

## Tech Stack

| Layer    | Technology      |
| -------- | --------------- |
| Frontend | Next.js         |
| Backend  | FastAPI         |
| Workflow | LangGraph       |
| Agent    | LangChain       |
| LLM      | Gemini 2.5 Flash|
| Analysis | Python + Pandas |
| Sandbox  | venv            |
| Memory   | Redis (optional)|
| Logs     | MongoDB (optional)|

## Prerequisites

- Python 3.10+
- Node.js 18+ & npm
- Gemini API key ([Get one here](https://ai.google.dev))
- Optional: Redis, MongoDB (for post-MVP features)

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd Insights
```

### 2. Set Up Environment Variables

```bash
# Copy example to .env.local
cp .env.example .env.local

# Edit .env.local and add your Gemini API key
GEMINI_API_KEY=your-key-here
```

### 3. Set Up Backend

```bash
# Create Python virtual environment
python -m venv venv

# Activate venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 4. Set Up Frontend

```bash
cd frontend

# Install npm dependencies
npm install

# Return to root
cd ..
```

## Running Locally

### Terminal 1: Start Backend

```bash
# Activate venv first
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Run FastAPI server
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Backend runs at: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Terminal 2: Start Frontend

```bash
cd frontend

# Run Next.js development server
npm run dev
```

Frontend runs at: `http://localhost:3000`

## API Endpoints

### File Upload

**POST** `/upload`

Upload a CSV file to create a new analysis session.

**Request:**
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@employees.csv"
```

**Response:**
```json
{
  "session_id": "sess_abc123def456",
  "message": "Upload successful",
  "metadata": {
    "filename": "employees.csv",
    "rows": 150,
    "columns": ["Name", "Department", "Salary", "Experience", "Gender"],
    "dtypes": {"Name": "object", "Salary": "float64"}
  }
}
```

### Chat / Query Analysis

**POST** `/chat`

Send a natural language query for data analysis.

**Request:**
```json
{
  "session_id": "sess_abc123def456",
  "message": "Show me average salary by department"
}
```

**Response:**
```json
{
  "role": "assistant",
  "content": "Based on the dataset, here's the average salary by department:\n\nIT: $95,000\nSales: $75,000\nHR: $65,000",
  "chart_url": "data:image/png;base64,iVBORw0KGgoAAAANS...",
  "execution_time_ms": 2500
}
```

## Project Structure

```
.
├── backend/                          # FastAPI application
│   ├── main.py                       # App entry point
│   ├── config.py                     # Configuration loader
│   ├── models/                       # Pydantic models
│   ├── routes/                       # API endpoints
│   ├── workflows/                    # LangGraph pipelines
│   ├── sandbox/                      # Code execution
│   ├── storage/                      # Session & file management
│   ├── utils/                        # Utilities
│   └── tests/                        # Unit tests
├── frontend/                         # Next.js application
│   ├── pages/                        # Routes and pages
│   ├── components/                   # React components
│   ├── hooks/                        # Custom React hooks
│   ├── utils/                        # Utilities
│   ├── styles/                       # CSS files
│   └── public/                       # Static assets
├── docker/                           # Docker configuration
├── scripts/                          # Setup scripts
├── .env.example                      # Environment template
├── .gitignore                        # Git ignore rules
├── README.md                         # This file
└── ARCHITECTURE.md                   # System architecture
```

## Usage Examples

### Example 1: Dataset Analysis

```
User: Analyze this dataset
Assistant: 
✓ Total employees: 150
✓ Average salary: $82,500
✓ Missing values: 2 records (Name)
✓ Top insights:
  - IT department has highest avg salary ($95K)
  - Gender split: 60% male, 40% female
```

### Example 2: Visualization

```
User: Show gender vs salary chart
Assistant: [PNG chart showing salary distribution by gender]
```

### Example 3: Data Quality

```
User: Are there any duplicates?
Assistant: Yes, found 3 duplicate rows (same Name and Department).
Recommendations:
  1. Review employee IDs
  2. Consider deduplication strategy
```

## Supported Analysis Types

### Summary Requests
- "Analyze this dataset"
- "Give me top insights"
- "Show salary summary"

### Comparison Requests
- "Compare IT vs Sales salaries"
- "Male vs female average salary"

### Visualization Requests
- "Show gender vs salary"
- "Plot department headcount"
- "Experience vs salary chart"

### Data Quality Requests
- "Missing values"
- "Duplicate rows"
- "Invalid records"

## Configuration

### Environment Variables

Edit `.env.local` to customize:

```bash
# Sandbox limits
SANDBOX_TIMEOUT=20              # Seconds
MAX_UPLOAD_SIZE=10485760        # 10 MB in bytes

# Server
FASTAPI_PORT=8000
NEXT_PUBLIC_API_URL=http://localhost:8000

# Session
SESSION_TIMEOUT_HOURS=24
```

## Running Tests

```bash
# Backend tests
pytest backend/tests/ -v

# With coverage
pytest backend/tests/ --cov=backend --cov-report=html
```

## Development Workflow

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and test locally
3. Run tests: `pytest backend/tests/`
4. Commit: `git commit -m "feat: description"`
5. Push: `git push origin feature/your-feature`
6. Create Pull Request

## Limitations (MVP)

- ❌ Single file upload per session
- ❌ No multi-user authentication
- ❌ No export to PDF/PowerPoint
- ❌ No scheduled reports
- ❌ No predictive analytics

(These will be added in post-MVP releases)

## Performance Targets

| Metric                   | Target |
| ------------------------ | ------ |
| Standard response        | <3 sec |
| Chart generation         | <8 sec |
| Upload success rate      | >95%   |
| Query success rate       | >90%   |
| Error rate               | <5%    |

## Troubleshooting

### Backend won't start
```bash
# Ensure venv is activated
venv\Scripts\activate  # Windows

# Clear Python cache
rm -rf __pycache__ backend/__pycache__

# Reinstall dependencies
pip install -r backend/requirements.txt
```

### Gemini API key error
```bash
# Verify .env.local has GEMINI_API_KEY set
cat .env.local | grep GEMINI_API_KEY

# Get a key: https://ai.google.dev
```

### Port already in use
```bash
# Change port in .env.local or CLI
python -m uvicorn backend.main:app --port 8001
```

## Documentation

- [Architecture Guide](ARCHITECTURE.md) — System design and data flow
- [API Documentation](http://localhost:8000/docs) — Interactive API explorer
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/) — Workflow documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/) — Backend framework

## License

MIT License - See LICENSE file

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review [ARCHITECTURE.md](ARCHITECTURE.md)
3. Open an issue on GitHub

## Contributing

Contributions are welcome! Please follow the development workflow above and ensure tests pass.

---

**Made with ❤️ for data analysis**
