# CaseClock Prototype Performance Report

## Environment

- Commit: `0a5589c` (`git status` clean except pre-existing untracked `backend/` dependency folders).
- OS: Windows 11 (`10.0.26200`)
- Python: 3.13.1; pytest 8.4.2
- Node/Vite: Node version was not emitted by the build command; Vite 6.4.3
- Measurements are local prototype measurements, not production SLOs.
- `git fetch origin` / `git pull --rebase origin main` were attempted but could not write `.git/FETCH_HEAD` because of local permission restrictions; the branch was already up to date.

## Dataset / Workload

- Deterministic synthetic graph generated with `SyntheticDataConfig(seed=42)`.
- Deadline benchmark sizes: 100, 500, 1,000 and 5,000 cases. The generator produces multiple clock records per case.
- Existing scale test: 4,000 cases, 22,296 nodes and 45,448 edges (67,744 records total).
- No genuine labelled entity-resolution or retrieval ground truth was found. Precision, recall, F1, Precision@K, Recall@K and MRR are therefore not reported.
- Catalyst/QuickML/Zia provider calls were not benchmarked; repository tests use mocks/stubs for external integrations.

## Methodology

- `scripts/benchmark_caseclock.py` generates data in memory, warms the clock path once, then performs 7 timed runs per workload. It reports p50, p95, mean and throughput.
- Clock correctness is checked through the deterministic engine and existing expected-output tests; the scale benchmark validates graph loading and traversal invariants.
- The existing `tests/scale/test_scale_performance.py` runs 100 depth-2 network queries and reports average latency.
- Frontend evidence comes from `npm.cmd run build`; gzip sizes are emitted by Vite.

## Results

### Statutory deadline engine — synthetic performance benchmark

| Cases | Clocks | p50 runtime | p95 runtime | p50 throughput |
|---:|---:|---:|---:|---:|
| 100 | 134 | 0.512 ms | 0.742 ms | 261,514 clocks/s |
| 500 | 667 | 4.618 ms | 6.270 ms | 144,435 clocks/s |
| 1,000 | 1,334 | 10.234 ms | 14.100 ms | 130,346 clocks/s |
| 5,000 | 6,667 | 91.931 ms | 233.739 ms | 72,522 clocks/s |

All generated clock responses in this run were deterministic `green` statuses for the fixed reference date. This is a correctness/throughput result for the local pure-Python calculation path, not a claim about Catalyst or end-to-end API latency.

### Graph / network intelligence — synthetic scale test

- 4,000 cases; 22,296 nodes; 45,448 edges; 67,744 total records.
- GraphLoader load: 0.316 s; graph validation: 0.115 s.
- 100 depth-2 `get_case_network` traversals: 2.661 s total; 26.61 ms average/query.
- Entity-resolution smoke benchmark: 10 queries over the scale graph in 1.413 s. No labelled accuracy metric is claimed.

### Frontend production build

- Build: passed (`tsc && vite build`); Vite reported 2,657 transformed modules.
- Largest emitted JS chunk: `vendor-recharts` 423.95 kB / 114.55 kB gzip.
- Main application JS chunk: 238.67 kB / 72.70 kB gzip.
- Main CSS chunk: 32.82 kB / 6.70 kB gzip.

## Correctness Evidence

- Relevant deterministic/backend correctness suites: **146/146 passed** in 18.31 s, covering graph foundation, phases 1–4, authentication/audit, system status, Catalyst repository fallback, clock engine, cron sweep, document intelligence contracts, and backend core API.
- The repository collected 516 tests overall. A full-suite invocation did not reach a final summary in this Windows environment; it progressed through the document-intelligence portion before the runner terminated. Therefore the full suite is not presented as 516/516 passing.
- Tests are regression/correctness evidence, not AI accuracy evidence.

## Scalability

The controlled clock benchmark shows increasing runtime with workload size and remains below 100 ms p50 for 5,000 cases / 6,667 clocks on this machine. The graph scale test demonstrates 67,744 in-memory records and 26.61 ms average depth-2 network traversal. These are synthetic local measurements and should not be extrapolated to production data volume.

## Limitations

- No reproducible API p50/p95 benchmark was claimed because a stable live server/database fixture was not available in the benchmark run.
- No live Catalyst deadline sweep evidence was available; the sweep is covered functionally by tests but not benchmarked against a live provider.
- No real labelled entity-resolution or similar-case ground truth exists in the repository; do not claim accuracy, precision, recall, F1, Precision@K, Recall@K or MRR.
- QuickML, Zia OCR and other external services were not benchmarked: external provider/configuration availability was not established.
- Browser performance/Core Web Vitals, users saved, investigation time saved and production scale were not measured.

## Reproduction Commands

```powershell
$env:PYTHONPATH='.'
python scripts\benchmark_caseclock.py
pytest -q --disable-warnings --basetemp .pytest-run tests\test_graph_foundation.py tests\test_phase1_foundation.py tests\test_phase2_schema_seed.py tests\test_phase3_auth_audit.py tests\test_phase4_services.py tests\test_system_status.py tests\test_catalyst_env_fallback.py tests\test_catalyst_repository.py tests\test_clock_engine.py tests\test_cron_job.py tests\test_document_intelligence.py tests\test_backend_core_api.py
pytest -q tests\scale\test_scale_performance.py -s --disable-warnings
cd frontend
npm.cmd run build
```

