# CaseClock

> Statutory-deadline-aware investigation tracking for Karnataka State Police  
> Built for KSP Datathon 2026 (PS1 — Intelligent Conversational AI)

[![CI Backend](https://github.com/acchasujal/CaseClock/actions/workflows/ci-backend.yml/badge.svg)](https://github.com/acchasujal/CaseClock/actions/workflows/ci-backend.yml)
[![CI Frontend](https://github.com/acchasujal/CaseClock/actions/workflows/ci-frontend.yml/badge.svg)](https://github.com/acchasujal/CaseClock/actions/workflows/ci-frontend.yml)
[![CI Integration](https://github.com/acchasujal/CaseClock/actions/workflows/ci-integration.yml/badge.svg)](https://github.com/acchasujal/CaseClock/actions/workflows/ci-integration.yml)

---

## What This Is

One unified investigation graph. Every organizer-required capability (network analysis, pattern discovery, conversational query) is a different lens on the same graph, anchored by real statutory-deadline tracking under BNSS.

Read [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) for full context. Read [`docs/TASK.md`](docs/TASK.md) for what is actually built vs. not built — that file is the only source of truth on real progress.

---

## Repository Structure

```
CaseClock/
├── backend/        # Lane 1 — FastAPI, Clock/Dependency/Escalation engines, Auth, API
├── frontend/       # Lane 2 — React app (Worklist, Case Detail, Escalation, Rollup)
├── graph/          # Lane 3 — Aggregation, Similarity, Synthetic data generator
├── ai/             # Lane 4 — Copilot, Refusal gate, Catalyst deployment
├── shared/
│   ├── contracts/  # API contract types (Python + TypeScript) — owned by Lane 4
│   └── constants/  # clock_types.py — offence-category → clock-type mapping
├── tests/          # Integration + scale tests
├── scripts/        # Seed data, refusal testset runner, deploy verifier
├── deployment/     # Catalyst AppSail + Slate configs
├── docs/           # All project documentation (13 docs)
└── .github/        # CI workflows, issue templates, PR template, CODEOWNERS
```

---

## Lane Ownership

| Lane | Owns | Branch |
|---|---|---|
| 1 — Backend Core | `backend/`, `shared/constants/` | `lane1` |
| 2 — Frontend | `frontend/` | `lane2` |
| 3 — Graph Intelligence | `graph/` | `lane3` |
| 4 — AI + Architecture + Integration | `ai/`, `shared/contracts/`, `deployment/`, `.github/` | `lane4` |

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
# Backend unit tests
pytest backend/tests/unit/ -v

# All tests (integration)
pytest backend/tests/ graph/tests/ ai/tests/ -v
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
| [`EXECUTION_RULES.md`](docs/EXECUTION_RULES.md) | How to work on this repo |
| [`DECISION_LOG.md`](docs/DECISION_LOG.md) | Architecture decisions and trade-offs |
| [`FEATURE_REGISTRY.md`](docs/FEATURE_REGISTRY.md) | Feature status and scope labels |
| [`TEAM_PLAYBOOK.md`](docs/TEAM_PLAYBOOK.md) | Daily operations |
| [`HACKATHON_MASTER_GUIDE.md`](docs/HACKATHON_MASTER_GUIDE.md) | Submission strategy |
