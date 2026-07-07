# TASK.md

Live execution plan. Read after `ARCHITECTURE.md`. This file reflects actual current state, not aspiration — if it says something isn't built, it isn't built, regardless of what any deck or prior planning document implies.

## Current State (as of this writing)

**Repository bootstrapped.** Initial folder structure scaffolded. Colapsed graph and copilot directories into the backend (`backend/app/core/graph` and `backend/app/core/copilot`). Authoritative contracts created (`shared/contracts/api.py` and `api.ts`), along with `shared/constants/clock_types.py`. CI pipelines consolidated into `.github/workflows/ci.yml`. CODEOWNERS set up. Strategical docs audited and consolidated (ER_DIAGRAM_NOTES merged into ARCHITECTURE, TEAM_PLAYBOOK merged into EXECUTION_RULES, ENGINEERING_OPERATING_MANUAL archived/deleted with Catalyst details moved to deployment/README.md).

## Engineering Organization

The project is organized around four engineering lanes, not developer headcount (see `DECISION_LOG.md` D12).

| Lane | Owner focus | Current status |
|---|---|---|
| Lane 1 — Backend Core | Clock/Dependency/Escalation engines, DB, Auth, APIs | NOT STARTED |
| Lane 2 — Frontend | React app, all screens | NOT STARTED |
| Lane 3 — Graph Intelligence | Aggregation, Similarity, Pattern/Risk/Forecasting (rule-based only, per D5) | NOT STARTED |
| Lane 4 — AI + Architecture + Integration (Sujal) | Copilot, refusal gate, synthetic data, API contracts, Catalyst deployment, CI/CD, cross-lane integration | IN PROGRESS (Bootstrap + Ops Setup done) |

## Outstanding Items Carried Over From Planning (highest priority — do not treat as optional)

1. **Refusal-gate test set** (D7 in `DECISION_LOG.md`) — 10–15 questions, answerable + ambiguous, must be run and scored before any demo claim about refusal reliability. Owner: **Lane 4**. Not started.
2. **Scale test at 1–2 lakh synthetic records** (D8) — no synthetic dataset generator exists yet either. Owner: **Lane 4** (generator) + **Lane 1** (query performance under test). Not started.
3. **Zoho Catalyst capability verification** — four spikes, not one: (a) AppSail Python/FastAPI support — owner **Lane 4**; (b) Data Store recursive-query support for graph traversal — owner **Lane 1**; (c) QuickML general grounded-completion support — owner **Lane 4**.
(d) Catalyst SmartBrowz spike
Can it generate downloadable PDFs from HTML? Owner: Lane 4 Priority: Medium
Status: NOT STARTED
All three block Phase 2 of `IMPLEMENTATION_PLAN.md`. Not started.
4. **BNSS section-number verification** — default-bail trigger section (176(2) vs 187(2)) unverified against bare statute text. Owner: **Lane 1** (feeds the Clock Engine's mapping table). Not started.

## Next Action

See `IMPLEMENTATION_PLAN.md` for the full build sequence. Update this file at the start and end of every work session — mark items done, add blockers, never let this file go stale relative to actual repository state.

## Status Key
`NOT STARTED` / `IN PROGRESS` / `BLOCKED (reason)` / `DONE (verified how)`

| Item | Status |
|---|---|
| Repository scaffold | DONE (Bootstrap complete, files structured) |
| Catalyst capability verification | NOT STARTED |
| Graph schema implementation | NOT STARTED |
| Legal Clock Engine | NOT STARTED |
| Dependency Tracker | NOT STARTED |
| Escalation Rule Engine | NOT STARTED |
| Synthetic data generator | NOT STARTED |
| Conversational layer + refusal gate | NOT STARTED |
| Refusal-gate test set execution | NOT STARTED |
| Scale test (1–2 lakh records) | NOT STARTED |
| Frontend shell | NOT STARTED |
| Catalyst deployment | NOT STARTED |
