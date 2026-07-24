# Backend Implementation Plan

## 1. Executive Summary

CaseClock has a working FastAPI prototype backed by a deterministic synthetic graph artifact, plus a substantially implemented deterministic graph-intelligence library. The remaining work is not to replace these foundations. It is to turn them into a secure, persistent Catalyst AppSail backend while preserving the current shared contracts and frontend behavior.

The canonical runtime design is:

```text
Catalyst Authentication -> FastAPI API -> application services -> repositories
                                            |                 |
                                  deterministic engines     Catalyst Data Store
                                            |
                                      GraphStore snapshot -> existing graph algorithms
```

All legal clocks, dependency status, escalation decisions, graph traversals, similarity, entity-resolution decisions, and factual summaries remain deterministic. QuickML may parse natural-language intent only; it never performs legal reasoning, executes a query, determines guilt, predicts conduct, or creates a risk score. Catalyst Data Store is the persistence source of truth; `GraphStore` is a validated, rebuildable read model.

This document supersedes earlier backend implementation planning where they conflict. It preserves existing public response shapes in `shared/contracts/api.py` and `api.ts` unless a contract change is explicitly approved and recorded.

## 2. Current Backend State

### Completed and reusable

- FastAPI app factory, CORS for local Vite origins, `/health`, core routes, and graph routes are present.
- `InMemoryBackendRepository` loads `artifacts/synthetic_graph/synthetic_graph.json`, derives worklists, details, networks, escalations, a constrained copilot reply, audit events, and persists prototype dependency patches to JSON.
- Clock, dependency, and escalation engines exist and are deterministic.
- Graph model, validation loader, `GraphStore`, traversal, aggregation, pattern, similarity, clustering/statistics, entity resolution, serializers, repository boundary, and services are implemented and tested.
- Synthetic generator produces stable UUID-based graph artifacts with repeated people and relationship patterns.
- Shared Python/TypeScript API contracts exist and frontend core hooks use `/worklist`, `/cases/{id}`, `/cases/{id}/network`, `/escalations`, `/deps/{id}`, and `/copilot/query`.
- Catalyst validation confirms AppSail hosting (Node/Express spike), Slate hosting, HTTPS/CORS, and SmartBrowz HTML-to-PDF. QuickML intent parsing has been spiked with GLM-4.7-Flash at temperature `0.0` and thinking disabled.

### Partially completed

- Core API is prototype-grade: it has no real authentication/authorization, persistence adapter, pagination, server-side filters, request correlation, or durable audit trail.
- Dependency updates exist, but have no actor identity, optimistic concurrency, transaction, immutable event history, or authorization.
- Escalations are recomputed on read and manual escalations live in prototype JSON; they are not persisted idempotently as immutable events.
- The copilot route has a minimal keyword refusal and template fallback; it is not the proposed intent-parser/allow-list executor.
- Graph routes are wired to an artifact-derived in-memory `GraphStore`; `GraphRepository.load_from_db` is explicitly a stub.
- `GraphStore` is built directly in `InMemoryBackendRepository`, bypassing `GraphLoader`; this must be corrected for persistent loading so validation is never skipped.

### Missing

- Catalyst Data Store schema, migration/seed tooling, real repository implementations, and Data Store capability report.
- Catalyst Authentication verification and backend token validation.
- Production AppSail package/configuration for this Python FastAPI service. The validated AppSail spike is Node.js, not FastAPI.
- Durable audit, conversation, escalation, and export flows.
- A complete copilot intent schema, QuickML adapter, fallback behavior, and refusal test set.
- Backend endpoints for the frontend’s placeholder district rollup and real patterns data.
- API response models for graph endpoints, OpenAPI stability tests, rate limits, structured error envelope, operational logging, and measured performance tests.

### Technical debt and evidence

- Test run on 2026-07-19 collected 203 tests: 202 passed; one test could not create the OS pytest temporary directory due to permissions. This is an environment failure, not an asserted product failure, but CI must run the full suite in a writable temporary directory.
- `backend/requirements.txt` omits `networkx`, although clustering imports it; dependencies must be made explicit.
- `clock_status` defines red as `< 7`, while comments/frontend wording imply red includes 0–6 and amber 7–14. Preserve that code behavior and test boundaries; correct prose to match.
- `CaseSummaryResponse` selects the minimum `days_remaining`, which correctly implements the intended primary-clock urgency rule despite stale prose saying “non-overdue.”
- The prototype role worklist limit (`IO` first 100, `SHO` first 250) is positional and does not implement ownership. Replace it with explicit authorization predicates, not different arbitrary limits.
- Current audit timestamps use wall-clock `datetime.now` while engines use an injected reference time. Production services must accept an injected `Clock` for deterministic tests and use UTC consistently.

## 3. Target Backend Architecture

### Modules and boundaries

| Layer | Responsibility | Must not do |
|---|---|---|
| `api/` | HTTP parsing, auth dependency, response mapping, error translation | business rules or direct Data Store queries |
| `core/*` engines | Pure deterministic calculation and validation | HTTP, Catalyst SDK, mutable database state |
| `services/` | Orchestrate repositories and engines; define transaction/use-case boundaries | encode raw SQL/SDK calls |
| `repositories/` | Typed Data Store reads/writes and mapping to domain records | rules, authorization policy decisions |
| `graph/` | Existing validated read model and deterministic algorithms | write canonical facts or depend on FastAPI |
| `catalyst/` | Small adapters for Data Store, Auth, QuickML, SmartBrowz | domain decisions |
| `auth/` | Principal extraction and role/scope policy | persistence or UI role simulation |

### Dependency graph

`api -> auth + services -> repositories + core engines`; `services -> graph repository -> GraphLoader -> GraphStore -> graph algorithms`; `repositories/catalyst adapters -> Catalyst SDK/HTTP`. Shared contracts may be imported by API and engines. No core engine or graph algorithm may import FastAPI, Catalyst, or frontend code.

### Conventions

- Python 3.11+ type hints, Pydantic v2 DTOs, UTC-aware ISO-8601 timestamps, UUID strings externally.
- `snake_case` JSON fields remain exactly as `shared/contracts/api.py`; never silently camel-case.
- All list ordering is explicit and stable; use `(primary_sort, id)` tie breakers.
- Raise typed domain exceptions (`NotFound`, `Conflict`, `Forbidden`, `Validation`, `ExternalServiceUnavailable`) and translate them once in API middleware.
- An entity property is canonical only in its entity table. Relationships are canonical only in `graph_edge`; derived edges are never persisted as facts.
- Keep existing graph algorithms and services. Add adapters, tests, bounded caches, and response DTOs rather than reimplementing their logic.

## 4. Domain Model

### Canonical entities

`Case` is the investigation hub. `Person` is identity-level and roles are edges (`ACCUSED_IN`, `VICTIM_IN`, `COMPLAINANT_IN`, `WITNESS_IN`). `Officer` belongs to `Unit`; exactly one active `INVESTIGATED_BY` relationship is required per active case. `Evidence`, `Dependency`, and `ClockInstance` are case-attached. Legal reference entities are `Act`, `Section`, `CrimeHead`, and `CrimeSubHead`. `Court` and `Location` provide context. `EscalationEvent`, `ConversationLog`, and `AuditEvent` are append-only trace records.

### Invariants and lifecycle

- IDs are immutable UUIDs. Cross-table references and every edge endpoint must exist before commit.
- Each canonical edge is unique on `(source_type, source_id, relationship_type, target_type, target_id)`.
- A case can have many clocks. A clock has immutable trigger/start and legal-rule provenance; `deadline_date`, `days_remaining`, and status are derived at read time. Never overwrite a statutory clock merely because the current day changes.
- A clock rule lookup with an unknown offence category is a validation error; no fallback rule is allowed.
- Dependency lifecycle is `pending -> resolved` or `pending -> escalated`; `escalated -> resolved` is permitted. Resolving sets `resolved_at` once and returns `days_stale=0`. Reopening is out of scope; create a new dependency instead.
- `days_stale = max(0, floor(UTC_today - requested_at.UTC_today))` for non-resolved dependencies. Do not trust a stored stale-day value.
- Escalation events are deduplicated by a stable trigger key: `(case_id, trigger_kind, source_entity_id, rule_version, threshold_date)`. Re-evaluation may update no existing event; resolution creates a separate audit event and sets `resolved_at`.
- Entity resolution only returns auto-link eligibility at score `>= 0.70`; below threshold returns review candidates and never writes a merge/link automatically.
- Conversation/audit records retain the user/principal, request correlation ID, request/response or refusal metadata, source IDs, and timestamp; redact tokens and secrets.

## 5. Data Model and Catalyst Data Store

### Tables

Create singular lowercase tables: `case`, `person`, `officer`, `unit`, `court`, `location`, `act`, `section`, `crime_head`, `crime_sub_head`, `evidence`, `dependency`, `clock_instance`, `escalation_event`, `conversation_log`, `audit_event`, and `graph_edge`.

All entity tables have `id UUID PK`, `created_at`, `updated_at`, and only the fields already produced by the synthetic factories or documented in `docs/graph-intelligence/DATA_MODEL.md`. Do not add speculative fields. `graph_edge` has `id`, `source_entity_type`, `source_id`, `relationship_type`, `target_entity_type`, `target_id`, `storage_mode`, `created_at`, `updated_at`, and the uniqueness constraint stated above.

`clock_instance` must include `case_id`, `clock_type`, `start_date`, `deadline_date`, `bnss_reference`, and `rule_version`. `dependency` must include `case_id`, `dependency_type`, `status`, `requested_at`, `due_at nullable`, `resolved_at nullable`, and `assigned_to_officer_id nullable`. `escalation_event` includes the trigger key fields, route, templated reason, `triggered_at`, `resolved`, and `resolved_at nullable`. `conversation_log` and `audit_event` store sanitized JSON metadata only.

### Indexes and queries

- Unique: `case.fir_number` only if Catalyst validation confirms FIR uniqueness in this dataset; otherwise use `(fir_number, police_station, reported_at)` and do not assume nationwide uniqueness.
- Index: case `(police_station, case_stage, reported_at)`, `(district, reported_at)`, `(offence_category, reported_at)`; dependency `(case_id, status, requested_at)`, `(status, requested_at)`; clock `(case_id, deadline_date)`, `(deadline_date)`; escalation `(case_id, resolved, triggered_at)`; audit `(occurred_at)`, `(actor_id, occurred_at)`.
- Edge indexes: `(source_id, relationship_type)`, `(target_id, relationship_type)`, and `(relationship_type, source_id, target_id)`.
- Worklist queries obtain candidate cases with authorization filters, batch-fetch clocks/dependencies, calculate derived values in the service, then perform stable sorting and cursor pagination. Do not issue one query per case.
- Graph snapshot loading fetches typed node rows and edges in bounded batches, then uses `GraphLoader.load_graph()` and validation before publication.

### Migration and seed strategy

1. First run the Data Store capability spike: CRUD, transactions, FK behavior, joins, stable pagination, indexes, recursive-query behavior, bulk import, concurrent reads, and export/import identity preservation.
2. Version migrations in `backend/app/db/migrations/` as ordered, idempotent scripts with a `schema_migration` ledger. Apply through a single CLI command; never mutate production schema on app startup.
3. Seed only through `synthetic_data` exports, with a seed/config manifest and checksum. Upsert entity tables first in dependency order, then edges; validate the imported graph through `GraphLoader` before marking seed complete.
4. If Catalyst lacks transactions, use idempotent batches and a `seed_run` status record; failed batches retry safely. If recursion is unavailable, retain the adjacency schema and do multi-hop traversal in `GraphStore`.

## 6. API Specification

All endpoints require `Authorization: Bearer <Catalyst token>` except `/health`; development-only local auth is prohibited outside explicit test configuration. Responses are JSON. Validation errors are `422`; unauthenticated `401`; unauthorized `403`; absent resource `404`; stale version `409`; rate limit `429`; unavailable Catalyst/QuickML/SmartBrowz `503`. Error body is `{ "code", "message", "request_id", "details?" }`.

Core endpoints retain their current paths and contract responses:

| Endpoint | Purpose, inputs, authorization, and notes |
|---|---|
| `GET /health` | Liveness only; returns status/service/version. No datastore health check or sensitive detail. |
| `GET /worklist` | Risk-ranked visible cases. Query: `cursor?`, `limit=50` (1–100), `station?`, `clock_status?`, `offence_category?`, `dependency_status?`, `sort` in `risk_rank|days_remaining|reported_at`, `direction`. IO only own/assigned cases; SHO unit scope; SP district scope. Return a new paginated envelope only after coordinated frontend contract approval; until then preserve list response and cap server results at 100. Sort: risk rank asc, days asc, FIR/id asc. |
| `GET /cases/{case_id}` | Existing `CaseDetailResponse`; scope-check case. Clocks urgency sorted asc; dependencies stale-days desc then name/id. No over-fetch graph. |
| `GET /cases/{case_id}/network` | Existing React Flow shape. Scope-check case; query `depth=1..4`, `max_nodes=18..200`. Deterministic BFS ordered by edge type then node ID; return truncation metadata only after contract approval. |
| `GET /escalations` | Visible unresolved/resolved events. Query `cursor?`, `limit`, `resolved?`, `case_id?`, `from?`, `to?`; default unresolved first then newest, id tie-break. IO sees own case events; SHO/SP scoped. Preserve list response temporarily; paginate with a contract migration. |
| `PATCH /deps/{dependency_id}` | Body currently `{status}`; add required `version` only after frontend update. IO only dependencies on assigned cases; SHO may escalate/resolve scoped dependencies; SP read-only unless a policy explicitly grants action. Validate state transition, write dependency + audit + event atomically, rebuild/invalidate graph snapshot. Return `DependencyResponse`. |
| `GET /audit` | SHO/SP only; query `cursor?`, `limit=100` (1–500), `case_id?`, `event_type?`, `actor_id?`, `from?`, `to?`. Never expose raw token/query PII outside authorized scope. |
| `POST /copilot/query` | Contract body `query` (1–1000 chars), `case_id?`, `user_role`; server ignores supplied role for authorization and uses principal role. Scope-check case. Return existing `CopilotQueryResponse`; deterministic refusal for unsafe/unsupported/ambiguous intent and no execution on failed schema validation. Rate limit per user. |

Graph endpoints are already mounted at `/api/v1/graph`. They are read-only, authenticated, scope-filtered before graph loading, and preserve their present query bounds:

| Endpoints | Implementation contract |
|---|---|
| `GET /cases/{id}/network`, `/persons/{id}/network` | `depth=1..4`; return serialized validated subgraph. Return 404 only if root is inaccessible/nonexistent. |
| `GET /persons/{id}/co-accused`, `GET /paths?source_id&target_id&max_depth=1..6` | Deterministic traversal; paths are capped and ordered shortest length, then lexicographic node sequence. |
| `GET /cases/{id}/similar?top_k=1..50&min_score=0..1`, `GET /cases/compare?case_a_id&case_b_id` | Existing deterministic feature scoring; exclude inaccessible candidates. |
| `GET /dashboard/summary`, `/dashboard/by-district`, `/dashboard/by-station`, `/dashboard/by-crime-head`, `/dashboard/officer-workload` | Scope-filtered graph aggregates. Add `as_of` in a future response-version, not ad hoc. |
| `GET /hotspots`, `/hotspots/temporal`, `/hotspots/dependency`, `/hotspots/workload`, `/hotspots/network`, `/hotspots/district/{district}` | Rule-derived, factual alerts only; apply district/unit scope and deterministic threshold ordering. |
| `GET /offenders/repeat?min_cases=2..10&top_k=1..200`, `/offenders/{id}/profile` | Factual participation only; no inferred criminality, prediction, or free-text profiling. |
| `GET /stats`, `/components`, `/centrality?top_k=1..100` | Operational graph metrics; centrality is analysis output, not a risk score. Cache snapshot-scoped results. |

Add, after contract approval, `GET /rollup/{district}` because frontend mocks it but the production frontend has no hook yet. It returns only deterministic totals: `total_cases`, `red_clocks`, `amber_clocks`, `stale_dependencies`, and sorted station rankings. Add no endpoint for simulated historical trends; real trends require `audit_event` history.

## 7. Core Engines

### Clock Engine

Inputs: immutable clock row or case offence category plus injected UTC reference time. Output: existing `ClockInstanceResponse`. Workflow: parse aware datetime; resolve verified `CLOCK_RULES` only for computed clocks; calculate calendar-date difference; map `<0 overdue`, `0..6 red`, `7..14 amber`, `>14 green`. Unknown mapping raises a domain validation error and produces an operational alert, never a default. Test time zones, midnight boundaries, malformed timestamps, unknown rules, concurrent clocks, and exact -1/0/6/7/14/15 boundaries.

### Dependency Engine

Inputs: dependency row and reference time. Output: `DependencyResponse`. Compute stale days from `requested_at`; resolved always returns zero. Map `dependency_type` to the existing display name convention and `assigned_to` from recorded party/officer. Validate status transitions in the service, not the DTO mapper. Test null dates, future requests, resolved/escalated states, and same-day behavior.

### Escalation Engine

Inputs: case clocks, dependencies, assigned officer/unit hierarchy, reference time. Output: proposed deterministic escalation events. Retain current triggers: any overdue clock, red clock with pending dependency, and stale pending dependency (current threshold is 14 days). Move threshold values into a single versioned policy module. Route using explicit officer->unit/supervisor data; never use a synthetic fallback such as the literal `SHO`. Persist idempotently in service. Test one trigger per source/day, deduplication, routing gaps, resolution, and repeated cron runs.

### Graph Engine

Use existing `GraphLoader`, `GraphStore`, traversals, aggregates, clustering and services unchanged in principle. Refresh as a versioned immutable snapshot after a committed mutation or a bounded TTL; requests acquire the last complete snapshot, never a half-built one. Loader validation rejects unknown entity/relationship types, duplicate canonical edges, and missing edge endpoints. Test read-after-write refresh, snapshot swap safety, scope filtering, depth/node caps, and serialized output stability.

### Pattern, Search, Similarity, and Entity Resolution

Pattern functions remain the existing repeat accused/phone/vehicle/address, workload, temporal, dependency, and district algorithms. Search is deterministic structured filtering over indexed allowed fields; it is not semantic search. Similarity continues existing feature-weight scoring and exposes component reasons. Entity resolution retains normalization, phonetics, bigram Jaccard, phone suffix, address boost, and `0.70` review threshold. Cache only snapshot-versioned results. Test false-positive guardrails, deterministic ties, normalization/Unicode, empty fields, and isolated nodes.

### Risk and escalation

There is no composite predictive “risk score.” Worklist `risk_rank` is an urgency ordering: the primary clock dominates, unresolved dependency count is a tie component; document its formula or replace it through a contract/version decision only. UI labels derive from clock status. Escalation is a separate policy engine and must state trigger facts and sources.

### Catalyst integration, authentication, QuickML, SmartBrowz

Catalyst adapters expose typed interfaces, short timeouts, bounded retries only for idempotent reads, and structured `503` failures. Auth adapter validates the issued token, issuer/audience/expiry/signature, and maps Catalyst user claims to internal principal ID, role, station/unit/district scopes. QuickML adapter sends a fixed schema prompt at temperature 0, thinking disabled, validates strict JSON and allow-listed fields, then hands a typed intent to deterministic services. On QuickML failure, do not guess: accept only deterministic direct case-ID queries or return a templated unavailable/unsupported response. SmartBrowz receives server-rendered, escaped HTML from authorized factual records and returns a PDF stream; no raw user HTML.

## 8. Algorithm Decisions

| Problem | Chosen approach | Rejected | Complexity / notes |
|---|---|---|---|
| Clock deadline | Calendar-date UTC arithmetic from immutable trigger and rule | LLM, mutable countdown storage | O(1); stable at day boundary. |
| Worklist urgency | Primary minimum `days_remaining`; stable server sort | frontend re-ranking, composite ML score | O(c log c) after batch data fetch. |
| Multi-hop graph | Adjacency lists + bounded BFS in application `GraphStore` | mandatory recursive Data Store SQL, separate graph DB | O(V+E) within requested cap; works if Catalyst lacks recursion. |
| Similar cases | Existing weighted exact/set feature overlap with explanations | embeddings/black-box model | Candidate-index-assisted; current all-pair fallback O(C²). |
| Entity resolution | Existing deterministic phonetic + bigram + phone/address rules, review below .70 | automatic LLM identity merging | O(N) candidates; index normalized phone/name to reduce N. |
| Centrality | Existing NetworkX calculations on snapshot; cache results | per-request recomputation | degree O(V+E); betweenness expensive, use bounded/periodic computation. |
| Escalation | Versioned threshold rules plus idempotent event key | generative alert text, mutable read-time notices | O(clocks+dependencies) per case. |
| Copilot | Strict QuickML intent parse -> Pydantic validation -> deterministic executor | free-form answer generation/RAG | bounded request; no tool calling until separately spiked. |

## 9. Service Layer

Implement `CaseService`, `DependencyService`, `EscalationService`, `WorklistService`, `AuditService`, `CopilotService`, `GraphSnapshotService`, `ExportService`, and `AuthzService`. Existing graph services (`GraphService`, `HotspotService`, `NetworkService`, `OffenderService`, `SimilarityService`) stay as the graph orchestration layer.

Public methods: case detail/network; paged worklist; update dependency; evaluate/list/resolve escalations; append/query audit; parse/execute copilot intent; acquire/refresh graph snapshot; export an authorized case/conversation report; `require_case_access`/`require_scope`. Services own transaction boundaries: dependency mutation, derived escalation upsert, audit append, and snapshot invalidation occur in one transaction when supported; otherwise use an idempotency key and outbox-style pending record. Repositories own persistence only. Cache immutable graph snapshots and expensive aggregate/centrality/similarity results by `(scope, graph_version, parameters)`; invalidate after mutation, never cache authorization decisions across principals.

## 10. Expected Repository Structure

```text
backend/app/
  api/                 # route modules, dependencies, response/error middleware
  auth/                # Principal, Catalyst token verifier, authorization policies
  catalyst/            # datastore/auth/quickml/smartbrowz adapters
  core/clock|dependency|escalation/  # pure existing engines and versioned policies
  core/graph/          # retain existing algorithms, loader, services, repository interfaces
  db/
    migrations/        # ordered schema migrations and migration ledger runner
    repositories/      # Catalyst typed repositories and transaction unit of work
    seed/              # artifact import/validation command
  services/            # application use cases and snapshot coordination
  main.py
shared/contracts/      # authoritative cross-language contracts; reviewed change only
synthetic_data/        # deterministic generator and exports
tests/unit|integration|api|performance|catalyst|e2e/
```

Do not delete `db/in_memory.py` until Catalyst integration tests provide an equivalent test adapter. Move it to an explicit test/development adapter and stop using it as the production default.

## 11. Testing Strategy

- Unit: current engine/graph tests plus every policy boundary, DTO validation, authorization predicate, typed exception, stable ordering, and source explanation.
- Integration: repository CRUD, constraints, transaction/idempotency, migrations, seed import, graph loader validation, snapshot refresh, and audit persistence against Catalyst test environment or a faithful adapter.
- API: every endpoint’s success, 401/403/404/409/422/429/503 path; OpenAPI/contract snapshot comparison with TypeScript contract fixtures.
- Graph: retain 193-style algorithm suite; add scope isolation, capped traversal, no derived-edge persistence, and deterministic serialization tests.
- Clock/escalation: freeze reference time and test every threshold, legal mapping failure, duplicate cron invocation, and time-zone boundary.
- Catalyst: isolated credential-gated tests for Data Store, Auth, QuickML malformed/output/failure cases, SmartBrowz PDF bytes, AppSail port/CORS health.
- Performance: seed 100k then 200k records; measure p50/p95 for worklist, detail, 2-hop network, similar cases, hotspots, and snapshot rebuild; record hardware/service tier and dataset manifest. No scalability claim without results.
- End-to-end: deployed Slate -> AppSail flow with real token, scoped worklist, dependency update, generated escalation, audit record, network, refusal, and PDF export.

## 12. Performance Strategy

Primary bottlenecks are Data Store edge fan-out, whole-graph reload, O(C²) similarity, NetworkX betweenness, and frontend’s current mock-first 5,000-record worklist behavior. Use projection queries and batch fetches; cursor pagination; indexes from Section 5; snapshot versioning; request caps; and bounded TTL caches. Rebuild one immutable graph snapshot after writes or through a background single-flight job, not on every graph request. Pre-index similarity features and normalized identity keys. Compute expensive centrality asynchronously/on refresh and cache by graph version. Add a cache service only after measured evidence; an in-process bounded TTL cache is adequate for hackathon scope and must be invalidated safely per AppSail instance.

## 13. Security

- Catalyst Authentication is mandatory: token verification server-side; frontend localStorage role simulation must be removed once integrated.
- Authorization is data scope, not merely UI role: IO assigned cases; SHO managed unit; SP district. Every case/graph edge returned is filtered by scope.
- Pydantic validates body/query/path values; allow-list sort/filter names and copilot fields; length-limit strings; reject unknown update fields.
- Escape report HTML, never interpolate user query into executable HTML/SQL, parameterize all Data Store calls, and redact sensitive fields from logs.
- Rate-limit copilot and mutating routes by principal/IP; enforce payload limits and request timeouts.
- Store Catalyst credentials/secrets only as environment variables; never log or return them. Rotate on exposure.
- Write append-only audit records for authentication outcomes, reads of case data, mutations, copilot requests/refusals, exports, and authorization failures. Include correlation ID and actor but no bearer token.

## 14. Integration Plan

Frontend: preserve existing core endpoints and response fields; introduce pagination/rollup/pattern contracts only with synchronized `shared/contracts` Python+TypeScript updates, changelog, mocks, hooks, and API tests. Set `VITE_API_BASE_URL` to AppSail HTTPS URL. Attach bearer token centrally in `apiClient` after authentication integration.

Graph: persistent repositories produce typed records; `GraphLoader` builds the sole graph read model. Core mutations invalidate/rebuild it. Graph algorithms remain storage-agnostic.

Catalyst: deploy frontend to Slate; deploy actual FastAPI runtime to AppSail only after a Python deployment spike. Keep Node spike separate. Use Data Store for canonical data, Catalyst Auth for identity, QuickML strictly for intent parsing, and SmartBrowz for authorized factual PDF generation. Zia voice is excluded from primary backend scope because STT/TTS was unavailable.

QuickML: supported intents initially are `case_summary`, `case_blockers`, `case_clock`, `case_network`, `retrieve_cases`, `aggregate`, and `unsupported_request`; each maps to a deterministic service method and allow-listed filters. Add only after the intent schema, prompt fixture suite, and integration-load test exist.

## 15. Phase-by-Phase Implementation Plan (unfinished work only)

### Phase 1 — Production foundation and contract hardening

Objective: make the FastAPI prototype operationally safe without changing completed domain algorithms.

Prerequisites: baseline test environment with writable temp directory; record current OpenAPI and shared-contract fixtures.

Tasks: add settings, UTC clock abstraction, structured errors/request IDs/logging, typed domain exceptions, explicit production/test repository wiring, CORS driven by configured frontend origins, explicit `networkx` dependency, and API response models for graph routes. Define no new public fields without contract review.

Expected files: `backend/app/config.py`, `api/dependencies.py`, `api/errors.py`, `core/time.py`, dependency updates, tests. Acceptance: all existing behavior passes; full test suite passes in CI; invalid inputs yield one error envelope; no production default JSON state path.

### Phase 2 — Catalyst Data Store decision, schema, migrations, and seed

Objective: establish canonical persistence.

Prerequisites: Catalyst Data Store credentials and capability spike environment.

Tasks: execute/report the documented Data Store matrix; implement schema/migration ledger, repository interfaces and Catalyst implementations, bulk synthetic import, graph validation after import, transaction/idempotency strategy based on spike results.

Expected files: `db/migrations/`, `db/repositories/`, `catalyst/datastore.py`, `db/seed/`, Catalyst tests. Acceptance: clean database migrates and imports deterministic artifact; reimport is safe; constraints/indexes tested; validation rejects broken edges; evidence report documents recursion/transaction behavior.

### Phase 3 — Authentication, authorization, and durable audit

Objective: replace client-side role trust with scoped backend enforcement.

Prerequisites: Catalyst Auth token/claim verification spike and officer-to-unit scope data seeded.

Tasks: principal model, verifier, scope policy, auth API dependency, audit repository/service, role-aware worklist/case/graph filtering, frontend bearer-token integration under its contract change.

Expected files: `auth/`, `catalyst/auth.py`, `services/audit_service.py`, repository methods, frontend auth/api-client changes, tests. Acceptance: forged body role does not alter access; cross-scope IDs return 404/403 per policy; every protected action is audited; token expiry/revocation behavior tested.

### Phase 4 — Core workflow persistence

Objective: persist clocks/dependencies/escalations correctly.

Prerequisites: Phases 1–3.

Tasks: replace in-memory worklist/detail/dependency/escalation paths with services/repositories; derive clock/dependency fields at read time; version escalation policy; create idempotent escalation events; add mutation version conflict handling; invalidate snapshots after commit.

Expected files: `services/case_service.py`, `dependency_service.py`, `escalation_service.py`, policy module, repositories, migrations/tests. Acceptance: concurrent duplicate evaluation creates one event; resolution is durable; reloaded data reproduces worklist/detail/escalations; no synthetic fallback routing.

### Phase 5 — Persistent graph read model and API completion

Objective: make all existing graph capabilities operate from Catalyst data safely.

Prerequisites: persisted graph and scope policies.

Tasks: implement `GraphRepository.load_from_db`, route through `GraphLoader`, snapshot coordinator/cache, batch query strategy, response DTOs, missing rollup endpoint after contract approval, and replace frontend mock usage as endpoints become available.

Expected files: graph repository/snapshot services, Catalyst graph queries, API DTOs/routes, contracts/hooks/mocks/tests. Acceptance: graph endpoints preserve deterministic results across refresh; no direct artifact dependency in production; traversal caps/scoping work; rollup uses real audit/history only where available.

### Phase 6 — Copilot and SmartBrowz integration

Objective: deliver constrained, grounded conversational and export paths.

Prerequisites: auth/audit, stable graph snapshot, QuickML API integration/load spike, and approved intent DTO contract.

Tasks: strict intent schemas/prompt fixtures, QuickML adapter, deterministic executor/refusal gate, conversation logging, rate limit, SmartBrowz HTML template and PDF endpoint if frontend scope adopts export.

Expected files: `core/copilot/`, `catalyst/quickml.py`, `catalyst/smartbrowz.py`, services/routes/tests. Acceptance: all refusal testset cases pass; malformed/unsupported QuickML output is refused; no answer lacks source path; QuickML outage fails safely; generated PDF contains only authorized escaped facts.

### Phase 7 — AppSail deployment and measured readiness

Objective: deploy and prove the actual backend, not the Node spike.

Prerequisites: prior phases and a Python FastAPI AppSail deployment spike.

Tasks: AppSail manifest/start command/port handling, environment mapping, production CORS, health/readiness, CI migration/seed checks, deployed E2E suite, 100k/200k performance benchmark, observability dashboards/log queries, runbook.

Expected files: Catalyst deployment config, CI workflow, performance/e2e tests, deployment documentation. Acceptance: Slate-to-AppSail authenticated E2E passes; production secrets are external; p95 metrics and cold-start results are recorded; no unverified scale claim remains.

## 16. Backend Definition of Done

The backend is complete only when all of the following are true:

- Catalyst Data Store is migrated, indexed, seeded, and the validated canonical source of truth; no production path depends on the synthetic JSON artifact or mutable local JSON state.
- Every documented endpoint is authenticated/authorized as applicable, validated, deterministically ordered, audited, and covered by API tests.
- Clock, dependency, escalation, graph, similarity, pattern, and entity-resolution outputs are deterministic, explainable, and preserve the tested current algorithms.
- Graph snapshots are validated from persistent records and are safely refreshed after mutations.
- QuickML is constrained to validated intent parsing; unsafe, unsupported, ambiguous, and unavailable requests refuse safely; the refusal suite passes.
- Frontend contracts are synchronized with Python/TypeScript shared definitions and deployed flows use real backend endpoints instead of mocks for implemented features.
- Catalyst Auth, Data Store, AppSail FastAPI runtime, QuickML integration, and SmartBrowz export behavior are evidenced by integration tests; Zia voice remains optional.
- The full automated test suite passes in CI, deployed end-to-end tests pass, and 100k/200k benchmark results are documented with no unsupported performance claims.
- Secrets are external, audit logs are durable/redacted, no forbidden guilt/reoffense inference exists, and every legal reference remains marked verified/unverified according to repository policy.
