# TASK.md

Live execution plan. Read after `ARCHITECTURE.md`. This file reflects actual current state, not aspiration — if it says something isn't built, it isn't built, regardless of what any deck or prior planning document implies.

## Current State (as of this writing)

**Repository bootstrapped.** Initial folder structure scaffolded. Colapsed graph and copilot directories into the backend (`backend/app/core/graph` and `backend/app/core/copilot`). Authoritative contracts created (`shared/contracts/api.py` and `api.ts`), along with `shared/constants/clock_types.py`. CI pipelines consolidated into `.github/workflows/ci.yml`. CODEOWNERS set up. Strategical docs audited and consolidated (ER_DIAGRAM_NOTES merged into ARCHITECTURE, TEAM_PLAYBOOK merged into EXECUTION_RULES, ENGINEERING_OPERATING_MANUAL archived/deleted with Catalyst details moved to deployment/README.md).

## Engineering Organization

The project is organized around four engineering lanes, not developer headcount (see `DECISION_LOG.md` D12).

| Lane                                             | Owner focus                                                                                              | Current status                           |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| Lane 1 — Backend Core                            | Clock/Dependency/Escalation engines, DB, Auth, APIs                                                      | IN PROGRESS (FastAPI + in-memory backend APIs working) |
| Lane 2 — Frontend                                | React app, all screens                                                                                   | IN PROGRESS (React shell builds; still mock-first by default) |
| Lane 3 — Graph Intelligence                      | Aggregation, Similarity, Pattern/Risk/Forecasting (rule-based only, per D5)                              | GRAPH FOUNDATION REVIEW COMPLETE         |
| Lane 4 — AI + Architecture + Integration (Sujal) | Copilot, refusal gate, synthetic data, API contracts, Catalyst deployment, CI/CD, cross-lane integration | IN PROGRESS (Bootstrap + Ops Setup done) |

## Outstanding Items Carried Over From Initial Planning (highest priority — do not treat as optional)

1. **Refusal-gate test set** (D7 in `DECISION_LOG.md`) — 10–15 questions, answerable + ambiguous, must be run and scored before any demo claim about refusal reliability. Owner: **Lane 4**. Not started.
2. **Scale test at 1–2 lakh synthetic records** (D8) — the synthetic data generator exists (`synthetic_data/`) but has only been run at ~500 record scale. The scale-volume run against 1–2 lakh records has not been executed. Owner: **Lane 4** (scale generator extension) + **Lane 1** (query performance under test). Not started.
3. **Zoho Catalyst capability verification** — IN PROGRESS:
   - QuickML capability spike: DONE (safety evaluation, model validation, prompt safety, and architect decision finalized. QuickML is restricted to intent parsing and entity extraction only).
   - AppSail, Data Store, and SmartBrowz: NOT STARTED.
4. **BNSS section-number verification** — default-bail trigger section (176(2) vs 187(2)) unverified against bare statute text. Owner: **Lane 1** (feeds the Clock Engine's mapping table). Not started.

## Next Action

See `IMPLEMENTATION_PLAN.md` for the full build sequence. Update this file at the start and end of every work session — mark items done, add blockers, never let this file go stale relative to actual repository state.

## Status Key

`NOT STARTED` / `IN PROGRESS` / `BLOCKED (reason)` / `DONE (verified how)`

| Item                                | Status                                                              |
| ----------------------------------- | ------------------------------------------------------------------- |
| Repository scaffold                 | DONE (Bootstrap complete, files structured)                         |
| Catalyst capability verification    | DONE (QuickML, AppSail, Slate, SmartBrowz verified; Zia Speech unavailable — see spikes and D14) |
| Graph schema & algorithms           | DONE (Foundation models, 134 analytical/traversal tests, and deterministic Entity Resolution module integrated and verified with 142 passing tests) |
| Legal Clock Engine                  | IN PROGRESS (Deterministic engine implemented and API-tested against synthetic data; Catalyst persistence pending) |
| Dependency Tracker                  | IN PROGRESS (Dependency normalization/update API implemented with in-memory adapter; Catalyst persistence pending) |
| Escalation Rule Engine              | IN PROGRESS (Rule-based escalation generation implemented and API-tested; Catalyst persistence/audit log pending) |
| Synthetic data generator            | DONE (synthetic_data module generates and exports JSON/CSV)         |
| Conversational layer + refusal gate | NOT STARTED (Integration blocked by Catalyst, core logic unblocked) |
| Refusal-gate test set execution     | NOT STARTED                                                         |
| Scale test (1–2 lakh records)       | NOT STARTED                                                         |
| Frontend shell                      | IN PROGRESS (Vite/React shell builds; API base URL and mock toggle added) |
| Catalyst deployment                 | NOT STARTED (Spike verified capability, production deployment wiring still pending) |

## Latest Dev 1 Session Update — 2026-07-18

- Added runnable FastAPI entry point at `backend/app/main.py`.
- Added backend dependency manifest at `backend/requirements.txt`.
- Added deterministic clock, dependency, and escalation engines under `backend/app/core/`.
- Added in-memory backend repository seeded from `artifacts/synthetic_graph/synthetic_graph.json`; this is the current adapter boundary before Catalyst Data Store wiring.
- Added frontend-compatible API routes: `/health`, `/worklist`, `/cases/{case_id}`, `/cases/{case_id}/network`, `/escalations`, `/deps/{dependency_id}`, `/copilot/query`.
- Added local JSON-backed runtime state for dependency/escalation changes and append-only audit events; runtime state is ignored under `artifacts/runtime_state/`.
- Added `/audit` diagnostic endpoint for demo/audit verification.
- Fixed graph route integration by adding `GraphService.find_paths_between`.
- Fixed CI/release workflows so tests and builds fail the workflow instead of being ignored.
- Added focused backend API and clock-engine tests.
- Verification: `python -m pytest -v --tb=short` passes with 179 tests; `npm ci`, `npm run test:run`, and `npm run build` pass in `frontend/`.
