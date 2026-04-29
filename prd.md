# Product Requirements Document (PRD)

# Employee Dataset Insight Chatbot (MVP v1.0)

## 1. Overview

Build an AI-powered chatbot that allows users to upload an employee CSV dataset and ask natural language questions about the data.

The system uses **LangGraph + LangChain Deep Agent + Python Sandbox** to dynamically analyze the dataset, generate charts, and return business insights.

The chatbot should behave like an on-demand data analyst.

---

# 2. Product Goal

Enable users to:

* Upload an employee dataset
* Ask questions in plain English
* Receive summaries, charts, comparisons, and insights
* Interactively explore data through chat

---

# 3. Core Value Proposition

Instead of manually using Excel or BI tools, users can ask:

* Which department has the highest salary?
* Show gender vs salary
* Compare IT vs Sales attrition
* What missing data exists?
* Plot experience vs salary

The AI writes analysis code, runs it securely, and returns answers instantly.

---

# 4. Primary User Flow

```text id="8c2qik"
Upload CSV
↓
Dataset stored for session
↓
User sends chat query
↓
LangGraph evaluates request
↓
Agent generates Python code
↓
Code runs in sandbox
↓
Results returned in chat
```

---

# 5. In Scope (MVP)

## File Handling

* Upload CSV file
* Validate format
* Associate file with session

## Chat Analysis

* Natural language questions
* Follow-up questions
* Context memory per session

## Dynamic Analysis

* AI-generated Python code
* Secure sandbox execution
* Pandas-based data analysis

## Visual Output

* Dynamic charts generated from code
* Returned in chat UI

## Operational

* Basic logs
* Error handling
* Session management

---

# 6. Out of Scope (Post-MVP)

* Multiple file uploads
* Excel / PDF files
* Scheduled reports
* Predictive analytics
* Multi-user collaboration
* Authentication / RBAC
* Export to PowerPoint / PDF

---

# 7. Supported User Requests

## Summary Requests

* Analyze this dataset
* Give me top insights
* Show salary summary

## Comparison Requests

* Compare IT vs Sales salaries
* Male vs female average salary

## Visualization Requests

* Show gender vs salary
* Plot department headcount
* Experience vs salary chart

## Data Quality Requests

* Missing values
* Duplicate rows
* Invalid records

---

# 8. Functional Requirements

# 8.1 File Upload

### Supported Format

* `.csv`

### Validation Rules

* Max size: 10 MB
* Must contain tabular data
* Reject unreadable files

---

# 8.2 Session Management

Each upload starts or joins a session.

Session stores:

* Uploaded dataset reference
* Chat history
* Prior outputs

---

# 8.3 Query Processing

Every user message is classified into:

### Type A: Direct Response

Simple question answered from prior context.

### Type B: Data Action Required

Requires fresh analysis, aggregation, filtering, or chart generation.

Triggers:

```text id="v1ur4q"
LangGraph → Agent → Sandbox
```

---

# 8.4 Code Generation

The agent writes Python code for:

* Aggregations
* Filtering
* Grouping
* Statistics
* Visualization

Libraries allowed:

* pandas
* numpy
* matplotlib

---

# 8.5 Sandbox Execution

All generated code runs in isolated environment.

### Limits

* Timeout: 20 sec
* Temporary storage only
* No shell/system commands
* Restricted imports

---

# 8.6 Output Types

System may return:

## Text

* Answer
* Summary
* Insights

## Table

* Top records
* Grouped metrics

## Chart

* PNG image generated in sandbox

---

# 9. Example User Journey

## Step 1

User uploads:

```text id="j2g44n"
employee_data.csv
```

## Step 2

User asks:

```text id="0w8f50"
Analyze this dataset
```

## Response

* Total employees
* Avg salary
* Missing values
* Top insights

## Step 3

User asks:

```text id="e4ijcn"
Show gender vs salary
```

## Response

Agent generates code, runs chart, returns graph.

---

# 10. System Architecture

```text id="7tzdv5"
Frontend (Next.js)
↓
FastAPI Backend
↓
LangGraph Workflow

1. Input Router
2. Session Loader
3. Intent Classifier
4. Agent Planner
5. Sandbox Executor
6. Response Formatter
```

---

# 11. LangGraph Workflow Logic

```text id="89cb63"
START
↓
Load Session
↓
Read User Query
↓
Need Data Action?

No → LLM Response

Yes →
Agent Plans
↓
Generate Python Code
↓
Run in Sandbox
↓
Parse Output
↓
Return Result
END
```

---

# 12. Tech Stack

| Layer    | Technology      |
| -------- | --------------- |
| Frontend | Next.js         |
| Backend  | FastAPI         |
| Workflow | LangGraph       |
| Agent    | LangChain       |
| LLM      | Gemini 2.5 flash|
| Analysis | Python + Pandas |
| Sandbox  | venv            |
| Memory   | Redis           |
| Logs     | MongoDB         |

---

# 13. Non-Functional Requirements

## Performance

* Standard response: < 3 sec
* Sandbox chart request: < 8 sec

## Reliability

* Graceful error messages
* Retry transient failures

## Security

* Isolated execution
* Temporary files deleted
* File size limits

---

# 14. Success Metrics

| Metric                   | Target |
| ------------------------ | ------ |
| Upload Success Rate      | >95%   |
| Query Success Rate       | >90%   |
| Avg Response Time        | <5 sec |
| Chart Generation Success | >90%   |
| Error Rate               | <5%    |

---

# 15. MVP Deliverable

Build only:

```text id="epttwe"
Upload CSV
→ Ask Question
→ AI Writes Code
→ Sandbox Runs Code
→ Return Insight / Chart
```

---

# 16. Final User Experience Goal

The user should feel:

> “I uploaded my HR dataset and now I have an AI data analyst in chat.”
