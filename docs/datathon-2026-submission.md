# CaseClock — KSP Datathon 2026 Submission

## Event

KSP Datathon 2026

## Final prototype brief

CaseClock is an Investigation Decision Intelligence Platform designed for Karnataka State Police to turn fragmented case data into timely, explainable action. It continuously tracks BNSS statutory deadlines, detects evidentiary blockers, prioritises escalations and helps IOs, SHOs and SPs understand what needs attention and why. Its investigation graph connects cases, persons, evidence and relationships for network analysis, similar-case discovery and pattern intelligence, while an evidence-grounded Copilot supports constrained natural-language investigation queries. Autonomous deadline sweeps continue when officers are offline, with human confirmation retained for consequential actions. The prototype is built around Zoho Catalyst-compatible AppSail, Slate, Data Store, Job Scheduling, QuickML/Zia and File Store adapters; provider-dependent capabilities are clearly marked below.

## Official links

- Repository: https://github.com/acchasujal/CaseClock
- Deployed prototype: https://caseclock-frontend-zaruqrfp.onslate.in/
- Demo video: https://drive.google.com/file/d/1zmdwMHbuCU8Pvqoz40mblGX8S9lQ7v5L/view?usp=sharing
- Prototype deck: https://storage.googleapis.com/vision-hack2skill-production/innovator/USER00953434/1785087100169-CaseClockPS1TeamBruh.pdf

## Feature summary

CaseClock combines a deterministic statutory clock engine, named dependency tracking, automatic escalation rules, a unified investigation graph, similar-case retrieval, graph-derived patterns, role-aware workflows and a refusal-gated Case Copilot. The demonstration dataset is synthetic and contains no real police PII.

## Architecture summary

The React/Vite frontend calls a FastAPI backend through shared Python/TypeScript contracts. Backend services separate deterministic legal and operational decisions from natural-language intent parsing. The graph layer uses indexed nodes and adjacency lists for network, traversal, similarity and pattern operations. Audit events record relevant views, refusals, dependency changes and sweeps.

## Zoho Catalyst integration summary

| Capability | Status | Evidence boundary |
|---|---|---|
| AppSail backend | Implemented/config-dependent | AppSail-compatible startup and deployment configuration exist; live deployment was not smoke-tested in this finalization run. |
| Slate frontend | Implemented/config-dependent | Production build passes; the submission provides the Slate URL. |
| Data Store | Implemented/config-dependent | Catalyst repository adapter and OAuth configuration path exist; live Data Store access was not reverified locally. |
| Job Scheduling | Implemented/config-dependent | Cron service and authenticated deadline-sweep route are tested locally; scheduler execution is provider/configuration-dependent. |
| QuickML | Implemented/config-dependent | Client, structured intent extraction and controlled error handling exist; tests use mocked provider boundaries and no live latency claim is made. |
| File Store + Zia OCR | Implemented/config-dependent | Authenticated adapter and document route exist; provider credentials and live OCR were not verified in this run. |

## Prototype benchmark summary

Measured locally on synthetic data with fixed seed/reference time:

- 6,667 mixed-state statutory clocks: 97.017 ms p50, 108.567 ms p95.
- 4,000 synthetic cases: 22,296 graph entities and 45,448 relationships.
- Depth-2 graph query: 21.523 ms mean, 29.431 ms p95 across 200 queries.
- Local autonomous sweep: 375 cases, 500 clocks, 3.69 ms, zero errors.
- Local API benchmark: 100% success across five representative endpoints, 100 requests per endpoint after warm-up.
- Frontend: 35/35 tests passing and production build passing.

Full methods and machine-readable results: [`benchmark-report.md`](benchmark-report.md), [`benchmark-results.json`](benchmark-results.json), [`../scripts/benchmark_caseclock.py`](../scripts/benchmark_caseclock.py).

These are local prototype measurements, not production Catalyst SLOs.

## Verification status

- Working tree was clean before final documentation edits.
- Repository currently collects 517 backend tests. Completed targeted gates passed; the aggregate Windows pytest runner did not emit a final summary, so this document does not claim 517/517.
- Frontend tests: 35/35 passed.
- Frontend production build: passed.
- Benchmark reproduction: passed locally.
- Security scan: no tracked credential values found; credential references are environment-variable based or test placeholders.

## Limitations

- Synthetic data only; no real KSP records or PII are included.
- Live AppSail, Slate, Data Store, QuickML, File Store and Zia calls were not all reverified during this finalization run.
- No AI accuracy, entity-resolution F1, retrieval precision/recall/MRR, production throughput, officer productivity, investigation-time savings or Core Web Vitals are claimed.
- Entity resolution remains a deterministic prototype mechanism without genuine labelled ground truth.
