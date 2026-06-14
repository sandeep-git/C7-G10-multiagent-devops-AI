---
title: DevOps Incident Analysis Suite
emoji: 🚨
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
license: mit
short_description: Multi-Agent LangGraph pipeline for DevOps incident triage
---

# 🚨 DevOps Incident Analysis Suite

An enterprise-grade, AI-powered incident triage platform for SREs and DevOps teams.
Upload raw operational logs and a **5-agent LangGraph pipeline** automatically triages the incident,
plans remediation using historical playbooks (RAG), synthesizes an executable runbook, and — after
human approval — creates a real Jira ticket and sends a Slack Block Kit notification with the ticket link.

**Live Demo:** https://sandeepg06-devops-incident-suite.hf.space

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Pipeline — Agent by Agent](#pipeline--agent-by-agent)
  - [Agent 1 · Log Classifier](#agent-1--log-classifier)
  - [Agent 2 · Remediation Agent (RAG)](#agent-2--remediation-agent-rag)
  - [Agent 3 · Cookbook Synthesizer](#agent-3--cookbook-synthesizer)
  - [HITL Approval Gate](#hitl-approval-gate)
  - [Agent 4 · Jira Ticketing Agent](#agent-4--jira-ticketing-agent)
  - [Agent 5 · Slack Notification Agent](#agent-5--slack-notification-agent)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Sample Log Files](#sample-log-files)
- [API Reference](#api-reference)
- [Deployment](#deployment)

---

## Architecture Overview

```
Upload Logs (.log / .txt / .json)
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Pipeline                        │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Agent 1    │───▶│   Agent 2    │───▶│   Agent 3    │  │
│  │ Log          │    │ Remediation  │    │ Cookbook     │  │
│  │ Classifier   │    │ Agent (RAG)  │    │ Synthesizer  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                  │                    │           │
│    Severity=1?        ChromaDB RAG         Runbook MD       │
│    (Benign) ──▶ END        │                    │           │
│                       Playbooks                 ▼           │
│                                        ┌──────────────────┐ │
│                                        │  👤 HITL Gate    │ │
│                                        │  Human Approval  │ │
│                                        │  (threading.Event│ │
│                                        │   pause/resume)  │ │
│                                        └──────────────────┘ │
│                                          Approve ▼  Reject  │
│                                   ┌──────────┐              │
│                                   │ Agent 4  │              │
│                                   │  Jira    │              │
│                                   └──────────┘              │
│                                        │                    │
│                                   ┌──────────┐              │
│                                   │ Agent 5  │              │
│                                   │  Slack   │              │
│                                   │(+Jira    │              │
│                                   │ details) │              │
│                                   └──────────┘              │
│                                        │                    │
│                                       END                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Pipeline — Agent by Agent

### Agent 1 · Log Classifier

**File:** `backend/agents/log_classifier.py`
**Role:** The "eyes" of the pipeline — first contact with raw log data.

#### What it does
- Ingests the raw log text (`.log`, `.txt`, `.json`)
- Uses **few-shot prompting** to detect anomalies — looks for `ERROR`, `FATAL`, `WARN`,
  `OOMKilled`, `timeout`, `connection refused`, stack traces, latency spikes, and more
- Correlates events across multiple services by timestamp
- Scores each anomaly on a **severity scale of 1–5**:

  | Score | Label    | Meaning                              |
  |-------|----------|--------------------------------------|
  | 1     | INFO     | Informational, no action needed      |
  | 2     | LOW      | Minor issue, monitor                 |
  | 3     | MEDIUM   | Investigate soon                     |
  | 4     | HIGH     | Urgent — service degraded            |
  | 5     | CRITICAL | P0 — service down, immediate action  |

#### Output schema — `LogAnalysisResult`
```python
anomalies: List[Anomaly]          # each with service, severity, description, stack_trace
overall_severity: int             # 1–5
affected_services: List[str]      # e.g. ["order-service", "postgres", "api-gateway"]
root_cause_hypothesis: str        # e.g. "OOM in order-service exhausted DB connections"
is_benign: bool                   # True → pipeline stops here (no further agents run)
```

#### Conditional routing
- If `is_benign = True` (severity 1 with no anomalies) → pipeline routes directly to **END**
- If `is_benign = False` → continues to Agent 2

---

### Agent 2 · Remediation Agent (RAG)

**File:** `backend/agents/remediation_agent.py`
**Role:** The "brain" — plans fixes using both LLM reasoning AND historical knowledge.

#### What it does
- Receives the `LogAnalysisResult` from Agent 1
- **Embeds** the root cause hypothesis into a vector using `sentence-transformers/all-MiniLM-L6-v2`
- **Queries ChromaDB** vector database for the top-3 most similar past incidents and SOPs
- Retrieves relevant historical playbooks (e.g. pgBouncer fix, Kafka consumer tuning, Redis stampede)
- Reasons over the retrieved playbooks + current anomalies together
- For **each identified issue**, produces a specific fix with rationale and a confidence score

#### RAG Knowledge Base (pre-seeded)
The vector store is seeded with 7 documents in `backend/vectorstore/seed_data.py`:

| ID            | Title                                      |
|---------------|--------------------------------------------|
| incident-001  | DB Connection Pool Exhaustion (pgBouncer)  |
| incident-002  | Node.js Memory Leak (event listeners)      |
| incident-003  | Kafka Consumer Lag Spike                   |
| incident-004  | Redis Cache Stampede                       |
| incident-005  | Kubernetes Node DiskPressure               |
| sop-001       | SOP: High CPU on Microservice              |
| sop-002       | SOP: Service Unavailable / 503 Errors      |

#### Output schema — `RemediationStrategy`
```python
issues: List[IssueRemediation]    # each with: issue, fix, rationale, confidence_score (0.0–1.0)
retrieved_playbooks: List[str]    # raw playbook text used for reasoning
overall_confidence: float         # weighted average confidence across all fixes
```

---

### Agent 3 · Cookbook Synthesizer

**File:** `backend/agents/cookbook_synthesizer.py`
**Role:** The "technical writer" — turns the abstract plan into something an on-call engineer can execute.

#### What it does
- Receives the `RemediationStrategy` from Agent 2
- Uses **constraint-based prompting** with strict rules:
  - Every shell command must be syntactically valid and copy-pasteable
  - Destructive operations (`rm`, `kill`, `restart`, `flush`, `drop`) must be flagged with `is_destructive=True` and a warning message
  - Must include rollback steps for every significant action
  - Output must be valid Markdown
- Estimates realistic time to resolve in minutes
- Organises steps in logical execution order

#### Output schema — `ActionableRunbook`
```python
title: str                         # e.g. "Redis Auth Failure & Kafka Lag Recovery"
estimated_time_minutes: int        # e.g. 45
steps: List[RunbookStep]           # ordered steps with optional shell commands
rollback_steps: List[RunbookStep]  # how to undo each major action
markdown: str                      # full runbook formatted as Markdown
```

---

### HITL Approval Gate

**Implemented in:** `backend/graph/pipeline.py` using `threading.Event` pause/resume

#### What it does
- After Agent 3 completes the pipeline **blocks** in `node_hitl_gate` using a `threading.Event`
- The pipeline thread waits (up to 1 hour) until the API approve endpoint signals the event
- The Streamlit UI shows a prominent **Approve & Deploy / Reject** form card
- Full runbook is visible for review before the decision is made

#### Why this matters
Agents 4 and 5 create real tickets and send real notifications. The HITL gate ensures:
- A human validates the AI's analysis is correct
- Destructive runbook steps are reviewed before being shared
- False positives don't spam your team's Slack channel or Jira board

#### Decisions
| Decision   | Result                                                    |
|------------|-----------------------------------------------------------|
| ✅ Approve  | Signals threading.Event → Agent 4 (Jira) → Agent 5 (Slack) |
| ❌ Reject   | Pipeline terminates — no external systems triggered       |

---

### Agent 4 · Jira Ticketing Agent

**File:** `backend/agents/jira_agent.py`
**Role:** The "bureaucrat" — creates a structured incident ticket in Jira via REST API.

#### What it does
- Receives `LogAnalysisResult` + `ActionableRunbook`
- Uses the LLM to format a proper Jira issue payload (summary, description, priority, labels, story points)
- Maps incident severity to Jira priority:

  | Severity | Jira Priority |
  |----------|---------------|
  | 5        | Highest       |
  | 4        | High          |
  | 3        | Medium        |
  | 2        | Low           |
  | 1        | Lowest        |

- Makes a **real REST API call** to `POST /rest/api/3/issue` on your Atlassian site
- Falls back to a mock URL if Jira credentials are not configured

#### Required env vars
```bash
JIRA_BASE_URL=https://your-site.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=OPS
```

#### Output schema — `JiraPayload`
```python
summary: str          # e.g. "P0: order-service OOMKilled — DB connections exhausted"
description: str      # full incident description in Atlassian Document Format
priority: str         # Highest / High / Medium / Low / Lowest
epic: str             # epic name
story_points: int     # 1–13
labels: List[str]     # e.g. ["incident", "kubernetes", "auto-generated"]
ticket_url: str       # e.g. https://your-site.atlassian.net/browse/JIRA-3
```

---

### Agent 5 · Slack Notification Agent

**File:** `backend/agents/notification_agent.py`
**Role:** The "dispatcher" — sends a rich Block Kit incident alert including the Jira ticket link.

#### What it does
- Receives `LogAnalysisResult` + `ActionableRunbook` + `JiraPayload` (from Agent 4)
- Uses the LLM to generate **Slack Block Kit JSON** with:
  - Header: severity emoji + incident title
  - Summary: 2–3 sentence root cause
  - Fields: Severity, Affected Services, ETA, Steps
  - Jira section: clickable ticket link, priority, summary, labels
  - **"Open Jira Ticket"** button for one-click navigation
- Posts to configured Slack channel via Incoming Webhook
- Falls back to locally-built blocks if LLM fails

#### Required env vars
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx
SLACK_CHANNEL=#devops-ai-incidents
```

#### Output schema — `SlackNotification`
```python
channel: str          # e.g. "#devops-ai-incidents"
blocks: List[dict]    # Slack Block Kit payload including Jira details
thread_url: str       # webhook URL confirming successful post
```

---

## Tech Stack

| Layer         | Technology                                          |
|---------------|-----------------------------------------------------|
| Orchestration | LangGraph (StateGraph + threading.Event HITL)       |
| LLM           | OpenRouter API (default: `anthropic/claude-sonnet-4-5`) |
| LLM Framework | LangChain (`langchain-openai`, `langchain-core`)    |
| Vector DB     | ChromaDB (local persistent)                         |
| Embeddings    | `sentence-transformers/all-MiniLM-L6-v2` (local)   |
| Backend API   | FastAPI + Uvicorn (SSE streaming)                   |
| Frontend UI   | Streamlit (purple-indigo gradient dashboard)        |
| Validation    | Pydantic v2 (all agent I/O schemas)                 |
| Jira          | Atlassian REST API v3                               |
| Slack         | Incoming Webhooks + Block Kit                       |
| Deployment    | Docker + Supervisord (Hugging Face Spaces)          |

---

## Project Structure

```
devops-incident-suite/
│
├── backend/
│   ├── agents/
│   │   ├── llm.py                    # Shared OpenRouter LLM init
│   │   ├── log_classifier.py         # Agent 1 — few-shot anomaly detection
│   │   ├── remediation_agent.py      # Agent 2 — RAG-powered remediation
│   │   ├── cookbook_synthesizer.py   # Agent 3 — constraint-based runbook
│   │   ├── jira_agent.py             # Agent 4 — real Jira REST API
│   │   └── notification_agent.py     # Agent 5 — Slack Block Kit + Jira details
│   │
│   ├── graph/
│   │   └── pipeline.py               # LangGraph nodes, edges, threading.Event HITL
│   │
│   ├── vectorstore/
│   │   ├── store.py                  # ChromaDB init + semantic retrieval
│   │   └── seed_data.py              # 7 historical playbooks + SOPs
│   │
│   ├── api/
│   │   └── routes.py                 # FastAPI endpoints + SSE stream
│   │
│   └── schemas.py                    # All Pydantic models (AgentState, etc.)
│
├── streamlit_app.py                  # Full Streamlit UI (purple dashboard)
├── Dockerfile                        # Docker image for HF Spaces deployment
├── supervisord.conf                  # Runs FastAPI (port 8000) + Streamlit (port 7860)
├── sample_logs/
│   ├── scenario1_k8s_oom_db_cascade.log
│   ├── scenario2_kafka_lag_redis_failure.log
│   └── scenario3_nodejs_memleak_disk_pressure.log
│
├── seed_vectorstore.py               # Run once to populate ChromaDB
├── test_jira.py                      # Validate Jira credentials
├── test_slack.py                     # Validate Slack webhook
├── requirements.txt
├── .env.example                      # Config template (no real secrets)
└── setup.sh                          # One-command local setup
```

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/sandeep-git/C7-G10-multiagent-devops-AI
cd C7-G10-multiagent-devops-AI

# 2. Create virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — add your OPENROUTER_API_KEY (required) + Jira + Slack (optional)

# 5. Seed the vector store (run once)
python seed_vectorstore.py

# 6. (Optional) Test Jira + Slack connections
python test_jira.py
python test_slack.py

# 7. Start the backend (Terminal 1)
uvicorn backend.api:app --port 8000 --reload

# 8. Start the UI (Terminal 2)
streamlit run streamlit_app.py --server.port 8501
```

Open **http://localhost:8501** in your browser.

---

## Environment Variables

| Variable              | Required | Description                                                  |
|-----------------------|----------|--------------------------------------------------------------|
| `OPENROUTER_API_KEY`  | ✅ Yes   | API key from openrouter.ai/keys                              |
| `OPENROUTER_MODEL`    | No       | Model ID (default: `anthropic/claude-sonnet-4-5`)            |
| `OPENROUTER_SITE_URL` | No       | Your app URL sent as HTTP-Referer to OpenRouter              |
| `CHROMA_PATH`         | No       | Path for ChromaDB storage (default: `./chroma_db`)           |
| `JIRA_BASE_URL`       | No       | e.g. `https://yoursite.atlassian.net`                        |
| `JIRA_EMAIL`          | No       | Atlassian account email                                      |
| `JIRA_API_TOKEN`      | No       | From `id.atlassian.com/manage-profile/security/api-tokens`   |
| `JIRA_PROJECT_KEY`    | No       | Short project key e.g. `JIRA` or `OPS`                      |
| `SLACK_WEBHOOK_URL`   | No       | From api.slack.com/apps → Incoming Webhooks                  |
| `SLACK_CHANNEL`       | No       | Channel to post to e.g. `#devops-ai-incidents`               |
| `BACKEND_URL`         | No       | FastAPI URL for Streamlit (default: `http://localhost:8000`) |

---

## Sample Log Files

Three ready-to-upload scenarios in `sample_logs/`:

| File                                         | Scenario                                     | Expected Severity |
|----------------------------------------------|----------------------------------------------|-------------------|
| `scenario1_k8s_oom_db_cascade.log`           | Kubernetes OOMKilled → DB connection cascade | 🔴 CRITICAL (5)   |
| `scenario2_kafka_lag_redis_failure.log`      | Kafka consumer lag + Redis auth failure      | 🔴 CRITICAL (5)   |
| `scenario3_nodejs_memleak_disk_pressure.log` | Node.js memory leak + K8s disk pressure      | 🔴 CRITICAL (5)   |

---

## API Reference

| Method | Endpoint                     | Description                                   |
|--------|------------------------------|-----------------------------------------------|
| POST   | `/api/analyze`               | Start pipeline with pasted logs (JSON body)   |
| POST   | `/api/analyze/upload`        | Start pipeline with uploaded log file         |
| GET    | `/api/runs/{run_id}`         | Get current state of a run                    |
| GET    | `/api/runs/{run_id}/stream`  | SSE stream of live state updates              |
| POST   | `/api/runs/{run_id}/approve` | Submit HITL decision (`approved`/`rejected`)  |
| GET    | `/api/health`                | Health check                                  |

---

## Deployment

### Hugging Face Spaces (Docker)

The app is deployed at: **https://sandeepg06-devops-incident-suite.hf.space**

The `Dockerfile` builds a single image running both services via `supervisord`:
- **FastAPI** on port `8000` (internal)
- **Streamlit** on port `7860` (public — HF Spaces default)

Add your secrets in **Space Settings → Variables and Secrets**:
```
OPENROUTER_API_KEY, JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN,
JIRA_PROJECT_KEY, SLACK_WEBHOOK_URL, SLACK_CHANNEL
```

### Push updates
```bash
git add .
git commit -m "your message"
git push hf main      # deploys to HF Spaces
git push github main  # updates GitHub repo
```

---

## How the State Flows

Every piece of data between agents is a typed Pydantic model stored in `AgentState` (in-memory dict):

```
raw_logs (str)
    │
    ▼ Agent 1
log_analysis (LogAnalysisResult)
    │
    ▼ Agent 2  ←── ChromaDB RAG retrieval
remediation_strategy (RemediationStrategy)
    │
    ▼ Agent 3
runbook (ActionableRunbook)
    │
    ▼ HITL Gate (threading.Event blocks here)
    │  approval_status = "approved" | "rejected"
    │
    ▼ Agent 4
jira_result (JiraPayload)  →  external_links["jira"]
    │
    ▼ Agent 5  ←── receives jira_result for Slack Block Kit
slack_result (SlackNotification)  →  external_links["slack"]
    │
   END
```

All agent-to-agent communication is **enforced via Pydantic schemas** — no raw text is passed between agents, preventing hallucination bleed-through.
