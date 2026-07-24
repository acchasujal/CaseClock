# TASK.md

Live execution plan. Read after `ARCHITECTURE.md`. This file reflects actual current state, not aspiration — if it says something isn't built, it isn't built, regardless of what any deck or prior planning document implies.

## Current State (as of this writing)

**Repository bootstrapped.** Initial folder structure scaffolded. Colapsed graph and copilot directories into the backend (`backend/app/core/graph` and `backend/app/core/copilot`). Authoritative contracts created (`shared/contracts/api.py` and `api.ts`), along with `shared/constants/clock_types.py`. CI pipelines consolidated into `.github/workflows/ci.yml`. CODEOWNERS set up. Strategical docs audited and consolidated (ER_DIAGRAM_NOTES merged into ARCHITECTURE, TEAM_PLAYBOOK merged into EXECUTION_RULES, ENGINEERING_OPERATING_MANUAL archived/deleted with Catalyst details moved to deployment/README.md).

## Engineering Organization

The project is organized around four engineering lanes, not developer headcount (see `DECISION_LOG.md` D12).

| Lane                                             | Owner focus                                                                                              | Current status                           |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| Lane 1 — Backend Core                            | Clock/Dependency/Escalation engines, DB, Auth, APIs                                                      | IN PROGRESS (FastAPI APIs + Catalyst Data Store adapter working in tests) |
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

## Completed

- **Repository scaffold**: Initial folder structure scaffolded. Colapsed graph and copilot directories into the backend. Authoritative contracts and CI pipelines consolidated.
- **Synthetic Graph Generation**: Fully functional [synthetic_data](file:///c:/Users/dyara/CaseClock/synthetic_data/) module that generates nodes and edges for cases, persons, officers, dependencies, evidence, and clocks.
- **Graph Infrastructure**:
  - **Graph Repository**: [graph_repository.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/repositories/graph_repository.py) implemented as a bridge between persistent database and in-memory GraphStore.
  - **Graph Loader**: [graph_loader.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/graph_loader.py) constructed to parse node/edge records.
  - **Graph Validation**: Reference, structure, and type checks implemented inside [GraphLoader](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/graph_loader.py).
- **Graph & Analytical Algorithms**:
  - **Graph Algorithms**: Low-level indices and graph construction helper utilities implemented in [utils.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/utils.py).
  - **Similarity Algorithms**: Deterministic similarity match and Jaccard distance calculation in [similarity.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/similarity.py).
  - **Traversal Algorithms**: BFS, multi-hop lookups, dependency and clock traversals in [traversals.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/traversals.py).
  - **Pattern Detection Algorithms**: Repeat accused, shared phone/vehicle/address clusters, high-workload officers, and hotspots in [pattern_detection.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/pattern_detection.py).
  - **Aggregation & Statistics**: District, station, and category rollups in [aggregation.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/aggregation.py); graph metrics, density, and component sizes in [statistics.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/statistics.py).
  - **Clustering Algorithms**: NetworkX-based component detection, degree and betweenness centralities in [clustering.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/clustering.py).
  - **Entity Resolution**: Deterministic, phonetic normalization, Jaccard bigram scoring, and boost rules implemented in [entity_resolution.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/entity_resolution.py).
- **Graph Intelligence Services**:
  - **Graph Service**: [graph_service.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/services/graph_service.py) coordinates subgraphs, co-accused, summaries, and central figures.
  - **Similarity Service**: [similarity_service.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/services/similarity_service.py) coordinates similar case lookups, direct comparisons, and pairwise matrices.
  - **Network Service**: [network_service.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/services/network_service.py) exposes single-node lookups and case/person/officer traversals.
  - **Hotspot Service**: [hotspot_service.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/services/hotspot_service.py) combines temporal, spatial, and network alerts into dashboard-ready payloads.
  - **Offender Service**: [offender_service.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/services/offender_service.py) handles repeat offender tracking, resolved offender profiles, and factual summaries.
- **Service Integration**: Exposing all services via FastAPI routers in [graph_routes.py](file:///c:/Users/dyara/CaseClock/backend/app/api/graph_routes.py) factory.
- **Unit Tests**: Full test suite verifying loader, repository, services, and algorithms with 193 passing tests (100% success rate).

## Completed

- **Repository scaffold**: Initial folder structure scaffolded. Colapsed graph and copilot directories into the backend. Authoritative contracts and CI pipelines consolidated.
- **Synthetic Graph Generation**: Fully functional [synthetic_data](file:///c:/Users/dyara/CaseClock/synthetic_data/) module that generates nodes and edges for cases, persons, officers, dependencies, evidence, and clocks.
- **Graph Infrastructure**:
  - **Graph Repository**: [graph_repository.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/repositories/graph_repository.py) implemented as a bridge between persistent database and in-memory GraphStore.
  - **Graph Loader**: [graph_loader.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/graph_loader.py) constructed to parse node/edge records.
  - **Graph Validation**: Reference, structure, and type checks implemented inside [GraphLoader](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/graph_loader.py).
- **Graph & Analytical Algorithms**:
  - **Graph Algorithms**: Low-level indices and graph construction helper utilities implemented in [utils.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/utils.py).
  - **Similarity Algorithms**: Deterministic similarity match and Jaccard distance calculation in [similarity.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/similarity.py).
  - **Traversal Algorithms**: BFS, multi-hop lookups, dependency and clock traversals in [traversals.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/traversals.py).
  - **Pattern Detection Algorithms**: Repeat accused, shared phone/vehicle/address clusters, high-workload officers, and hotspots in [pattern_detection.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/pattern_detection.py).
  - **Aggregation & Statistics**: District, station, and category rollups in [aggregation.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/aggregation.py); graph metrics, density, and component sizes in [statistics.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/statistics.py).
  - **Clustering Algorithms**: NetworkX-based component detection, degree and betweenness centralities in [clustering.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/clustering.py).
  - **Entity Resolution**: Deterministic, phonetic normalization, Jaccard bigram scoring, and boost rules implemented in [entity_resolution.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/entity_resolution.py).
- **Graph Intelligence Services**:
  - **Graph Service**: [graph_service.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/services/graph_service.py) coordinates subgraphs, co-accused, summaries, and central figures.
  - **Similarity Service**: [similarity_service.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/services/similarity_service.py) coordinates similar case lookups, direct comparisons, and pairwise matrices.
  - **Network Service**: [network_service.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/services/network_service.py) exposes single-node lookups and case/person/officer traversals.
  - **Hotspot Service**: [hotspot_service.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/services/hotspot_service.py) combines temporal, spatial, and network alerts into dashboard-ready payloads.
  - **Offender Service**: [offender_service.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/services/offender_service.py) handles repeat offender tracking, resolved offender profiles, and factual summaries.
- **Service Integration**: Exposing all services via FastAPI routers in [graph_routes.py](file:///c:/Users/dyara/CaseClock/backend/app/api/graph_routes.py) factory.
- **Unit Tests**: Full test suite verifying loader, repository, services, and algorithms with 193 passing tests (100% success rate).

| Item                                | Status                                                              |
| ----------------------------------- | ------------------------------------------------------------------- |
| Repository scaffold                 | DONE (Bootstrap complete, files structured)                         |
| Catalyst capability verification    | DONE (QuickML, AppSail, Slate, SmartBrowz verified; Zia Speech unavailable — see spikes and D14) |
| Graph schema & algorithms           | DONE (Foundation models, 134 analytical/traversal tests, and deterministic Entity Resolution module integrated and verified with 142 passing tests) |
| Legal Clock Engine                  | IN PROGRESS (Deterministic engine implemented and API-tested against synthetic and Catalyst-shaped data; BNSS section verification pending) |
| Dependency Tracker                  | IN PROGRESS (Dependency normalization/update API implemented with in-memory and Catalyst Data Store adapters; live SDK auth verification pending) |
| Escalation Rule Engine              | IN PROGRESS (Rule-based escalation generation implemented; Catalyst escalation/audit write adapter added and fake-SDK tested) |
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
- Imported Catalyst Data Store seed data in development: `cases` (500), `clock_instances` (667), `dependencies` (150), `graph_nodes` (3554), and `graph_edges` (5000 development-limit rows), all with zero import failures.
- Added `CatalystBackendRepository` at `backend/app/db/catalyst.py` to load Catalyst Data Store rows into the same backend API shape, update dependency status, and persist audit/escalation rows where Catalyst writes are available.
- Added `CASECLOCK_REPOSITORY=local|catalyst` backend switch and documented SDK env placeholders in `configs/.env.example`.
- Added fake-SDK Catalyst repository tests so CI verifies the adapter without live Catalyst credentials.
- Verification: `python -m pytest -q` passes with 181 tests; touched-file ruff passes. Full repository ruff still reports pre-existing lint issues in older graph tests.
