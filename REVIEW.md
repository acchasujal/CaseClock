# lane3-graph-foundation Review

## Purpose
This branch implements the unified investigation graph core models and establishes the modular factories-based synthetic data generator pipeline to model realistic crime/case structures (including repeat offender clustering, shared phone/vehicle numbers, and named dependencies).

## Scope
- `shared/constants/clock_types.py`: Clock rules mapping table.
- `synthetic_data/factories/clock_factory.py`: Generating clock instances.
- `tests/test_graph_foundation.py`: Verification tests.

## Architecture Decisions
- **One Unified Graph:** All deadline clocks, network analysis, profiling, and pattern discovery features are traversals over a single, unified node/edge structure to prevent fragmented databases.
- **Role Gating via Edges:** Roles like accused, victim, and complainant are modeled as edge types (`ACCUSED_IN`, `VICTIM_IN`) rather than duplicating `Person` nodes.

## Major Changes
- **Synchronized Clock Rules:** Added all synthetic offence categories to `CLOCK_RULES` mapping table under `shared/constants/clock_types.py` as unverified placeholders.
- **Refactored Clock Factory:** Bypassed hardcoded durations and resolved all rules dynamically via the shared `get_clock_rule` registry.
- **Added Graph Verification Tests:** Created unit tests for the schema enums, clock rules, invalid category lookup failures, and deterministic generation seeds.

## Tests Executed
- **Pytest Verification:** `python -m pytest` (4 tests passed, 1.02s).
- **Generator Verification:** `python -m synthetic_data.seed` (3,554 nodes and 8,812 edges generated successfully).

## Documentation Updated
- `shared/constants/clock_types.py`
- `docs/TASK.md` (marked Graph Schema and Synthetic Generator as `DONE`)

## Known Limitations
- Node attributes are stored inside a generic `properties: dict[str, Any]` field on Pydantic classes to simplify factory generation during early bootstrap.

## Follow-up Work
- Phase 3 backend execution (implementing the deterministic Legal Clock Engine and Dependency Tracker APIs).

## Merge Status
✅ Ready for review. No merge conflicts.
