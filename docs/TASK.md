# TASK.md

Live execution plan. Read after `ARCHITECTURE.md`. This file reflects actual current state, not aspiration — if it says something isn't built, it isn't built, regardless of what any deck or prior planning document implies.

## Current State (as of this writing)

**No repository scaffold exists yet.** No backend, no frontend, no deployed Catalyst instance. Six planning documents exist (`README.md`, `PROJECT_CONTEXT.md`, `EXECUTION_RULES.md`, `FEATURE_REGISTRY.md`, `ARCHITECTURE.md`, `DECISION_LOG.md`). This file and `IMPLEMENTATION_PLAN.md` are the first artifacts oriented toward actual code.

## Outstanding Items Carried Over From Planning (highest priority — do not treat as optional)

1. **Refusal-gate test set** (D7 in `DECISION_LOG.md`) — 10–15 questions, answerable + ambiguous, must be run and scored before any demo claim about refusal reliability. Not started.
2. **Scale test at 1–2 lakh synthetic records** (D8) — not started; no synthetic dataset generator exists yet either.
3. **Zoho Catalyst capability verification** — confirm what data-store/graph support actually exists on Catalyst before committing to a storage approach in `ARCHITECTURE.md`. Not started.
4. **BNSS section-number verification** — default-bail trigger section (176(2) vs 187(2)) unverified against bare statute text. Not started.

## Next Action

See `IMPLEMENTATION_PLAN.md` for the full build sequence. Update this file at the start and end of every work session — mark items done, add blockers, never let this file go stale relative to actual repository state.

## Status Key
`NOT STARTED` / `IN PROGRESS` / `BLOCKED (reason)` / `DONE (verified how)`

| Item | Status |
|---|---|
| Repository scaffold | NOT STARTED |
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
