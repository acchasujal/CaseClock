# CaseClock

> Statutory-deadline-aware investigation tracking for Karnataka State Police  
> Built for KSP Datathon 2026 (PS1 — Intelligent Conversational AI)

[![CI](https://github.com/acchasujal/CaseClock/actions/workflows/ci.yml/badge.svg)](https://github.com/acchasujal/CaseClock/actions/workflows/ci.yml)

---

## What This Is

One unified investigation graph. Every organizer-required capability (network analysis, pattern discovery, conversational query) is a different lens on the same graph, anchored by real statutory-deadline tracking under BNSS.

Read [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) for full context. Read [`docs/TASK.md`](docs/TASK.md) for what is actually built vs. not built — that file is the only source of truth on real progress.

---

## Repository Structure

```
CaseClock/
├── backend/
│   ├── app/
│   │   ├── api/            # Route handlers
│   │   ├── core/
│   │   │   ├── clock/      # Legal Clock Engine (LOAD BEARING)
│   │   │   ├── dependency/ # Dependency Tracker
│   │   │   ├── escalation/ # Escalation Rule Engine
│   │   │   ├── graph/      # Graph traversals, aggregation, similarity (Lane 3)
│   │   │   ├── copilot/    # NL grounding, refusal gate (Lane 4)
│   │   │   └── auth/
│   │   ├── db/             # Storage adapter (Catalyst Data Store)
│   │   ├── catalyst/       # Catalyst SDK wrappers — QuickML, SmartBrowz, Zia
│   │   └── main.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── refusal_testset/
├── frontend/               # Lane 2 — React app (Worklist, Case Detail, Escalation, Rollup)
├── shared/                 # Cross-lane contracts & constants
│   ├── contracts/          # API contract types (Python + TypeScript) — owned by Lane 4
│   └── constants/          # clock_types.py — offence-category → clock-type mapping (Lane 1)
├── tests/
│   └── scale/              # 1-2 lakh record load tests only
├── scripts/                # Seed data, refusal testset runner, deploy verifier
├── deployment/             # Catalyst AppSail + Slate configs
├── docs/                   # Consolidated project documentation
└── .github/                # CI workflows, issue templates, PR template, CODEOWNERS
```

---

## Lane Ownership

Lanes represent **ownership domains**, not Git branches. Development uses **GitHub Flow** with short-lived feature branches targeting `main` directly. Ownership boundaries remain lane-based regardless of branch names.

| Lane | Owns | Key Directories/Files |
|---|---|---|
| 1 — Backend Core | Clock/Dependency/Escalation, Auth, APIs, Constants | `backend/app/core/clock/`, `backend/app/core/dependency/`, `backend/app/core/escalation/`, `backend/app/core/auth/`, `shared/constants/` |
| 2 — Frontend | React UI, dashboard, timeline, charts, analytics | `frontend/` |
| 3 — Graph Intelligence | Aggregations, similarity, pattern/risk/forecasting | `backend/app/core/graph/` |
| 4 — AI + Architecture + Integration | Copilot, refusal gate, contracts, Catalyst deployment, CI/CD | `backend/app/core/copilot/`, `backend/app/catalyst/`, `shared/contracts/`, `deployment/`, `.github/`, `docs/` |

---

## Getting Started (Local)

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Run tests
```bash
# Run all backend unit and integration tests
pytest backend/tests/ -v
```

---

## Key Rules

Before writing any code, read [`docs/EXECUTION_RULES.md`](docs/EXECUTION_RULES.md).

**Critical anti-hallucination rules (enforced in every PR):**
- Never invent a schema field, API endpoint, or table that doesn't exist
- Never label a rule engine as AI/ML
- Never generate free-text about a specific person's guilt or risk
- All BNSS citations marked `[VERIFIED]` or `[UNVERIFIED]`

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). All PRs must pass the checklist in [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

Contract changes (`shared/contracts/`) require Lane 4 (Sujal) review. Clock/escalation/graph schema changes require a `DECISION_LOG.md` entry before the PR.

---

## Deployment

Mandatory on Zoho Catalyst (AppSail + Slate) per organizer eligibility rules.  
Deployment configs: [`deployment/`](deployment/).  
Current deployment URL: *to be added after M0 walking skeleton is live.*

---

## Docs

| Document | Purpose |
|---|---|
| [`PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) | Why the product exists |
| [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture |
| [`TASK.md`](docs/TASK.md) | What is actually built (source of truth) |
| [`EXECUTION_RULES.md`](docs/EXECUTION_RULES.md) | How to work on this repo (ops + AI rules) |
| [`DECISION_LOG.md`](docs/DECISION_LOG.md) | Architecture decisions and trade-offs |
| [`FEATURE_REGISTRY.md`](docs/FEATURE_REGISTRY.md) | Feature status and scope labels |
| [`HACKATHON_MASTER_GUIDE.md`](docs/HACKATHON_MASTER_GUIDE.md) | Submission strategy (frozen) |
| [`PROTOTYPE_SUBMISSION_GUIDE.md`](docs/PROTOTYPE_SUBMISSION_GUIDE.md) | Deliverable list |
