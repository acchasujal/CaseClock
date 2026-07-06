# EXECUTION_RULES.md

This document governs how any AI coding agent (or human engineer) must think and act while working on this repository. Read `PROJECT_CONTEXT.md` first — this file assumes you already know why the project exists.

## Mandatory Reasoning Workflow (every task, no exceptions)

1. **Understand** — restate the task in your own words. What is actually being asked?
2. **Challenge assumptions** — does this task assume something not yet verified (e.g., that Catalyst supports a feature, that a schema field exists, that entity resolution works)? State the assumption explicitly before proceeding.
3. **Read project context** — check `PROJECT_CONTEXT.md` and `DECISION_LOG.md` for whether this has been decided or discussed before. Do not re-litigate settled decisions without new evidence.
4. **Read architecture** — check `ARCHITECTURE.md` for where this fits.
5. **Search existing implementation** — grep the actual repository before writing new code. Duplicate implementations are a documented recurring failure mode for this team (see `DECISION_LOG.md` — mock/parallel systems in prior hackathon projects).
6. **Avoid duplication** — if similar logic exists, extend it, don't fork it.
7. **Plan** — write the plan before writing code, especially for anything touching the clock engine, dependency tracker, or graph schema (these are load-bearing; errors here are legal-accuracy risks, not just bugs).
8. **Implement** — smallest correct change. Do not scope-creep into roadmap items listed in `PROJECT_CONTEXT.md`'s Non-Goals.
9. **Review** — re-read your own diff against the anti-hallucination rules below before considering it done.
10. **Test** — every deterministic component (clock rules, escalation triggers) needs unit tests with real edge cases (offence category not in mapping table, missing dependency data). The refusal gate needs an actual test set of answerable/ambiguous questions — this has been flagged as unresolved across multiple planning sessions and is the highest-priority testing gap in the project.
11. **Reflect** — did this change require updating any of the seven docs? If architecture changed, update `ARCHITECTURE.md` and log the decision in `DECISION_LOG.md` in the same session.

## Anti-Hallucination Rules (absolute, non-negotiable)

- **Never invent API endpoints, database tables, or fields that don't exist in the actual codebase or the organizer-provided schema.** If a needed field doesn't exist (e.g., a unique cross-case person identifier), say so and propose a documented workaround — do not silently assume it exists.
- **Never fake functionality.** If the FSL/CDR dependency data is not available in synthetic form yet, the UI must show an honest empty/pending state, not fabricated plausible-looking values.
- **Never claim a capability is "AI-detected" or "ML-based" when it is actually a rule-based aggregation or threshold check.** This project's stated principle is deterministic-before-generative — mislabeling a rule engine as ML is a direct violation of the product's own philosophy and a known judging-panel red flag from prior evaluation of this team's projects.
- **Never silently remove a working feature.** If a feature must be cut for scope reasons, it must be moved to the Non-Goals/roadmap section of `PROJECT_CONTEXT.md` and logged in `DECISION_LOG.md`, not deleted without a trace.
- **Never fabricate a legal citation.** Any BNSS/BNS section number used in code comments, UI copy, or documentation must be marked `[VERIFIED]` or `[UNVERIFIED — check against bare statute text]`. As of this writing, the default-bail section number (176(2) vs 187(2) BNSS) is UNVERIFIED and must not be asserted confidently in any user-facing or demo material until checked.
- **Never generate free-text prose about a specific person's culpability, risk of reoffending, or guilt.** Profiling/risk-scoring outputs must be templated from graph-derived facts (e.g., "3 prior FIRs as accused, same section category") — never open-ended LLM generation about a person.
- **Always search existing code first** before implementing anything that touches the graph model, clock engine, or NL layer.

## Coding Philosophy

- Prefer deterministic, auditable logic wherever a decision doesn't genuinely require language understanding.
- Prefer simple, maintainable code over clever abstractions — this team's documented failure mode is overbuilt, disconnected pipelines that don't fully execute under deadline pressure, not lack of sophistication.
- Every escalation, clock calculation, and refusal must be explainable by tracing a concrete path through the graph — if you can't explain why the system produced an output by pointing at specific nodes/edges/rules, the design is wrong, not just the explanation.

## Debugging Methodology

1. Reproduce with the smallest possible synthetic case.
2. Check whether the bug is in the deterministic layer (clock/escalation rules) or the generative layer (NL/copilot) — these have different failure modes and different fixes.
3. For deterministic-layer bugs: trace the exact rule that fired incorrectly; these are usually mapping-table errors (offence category → wrong clock type).
4. For generative-layer bugs: check whether the refusal gate should have fired but didn't (under-refusal, the more dangerous failure) versus fired when it shouldn't have (over-refusal, the more visible-but-safer failure).
5. Never patch a generative-layer bug by adding more prompt instructions alone — check whether the deterministic pre/post-processing gate should be doing the check instead.

## Error Recovery Process

If a change breaks an existing test or demo path: revert first, diagnose second. Do not attempt forward-fixes under time pressure without understanding root cause — this is precisely the pattern that produced circular-mock-logic and non-importable pipelines in this team's prior hackathon submissions.

## Refactoring Rules

- Refactor the clock engine or graph schema only with an explicit entry in `DECISION_LOG.md` — these are the two components every other feature depends on.
- Never refactor and add a feature in the same change.

## Code Review Checklist (self-review before considering any task done)

- [ ] Does this match an existing decision in `DECISION_LOG.md`, or does it contradict one? If it contradicts one, is that intentional and logged?
- [ ] Does this introduce a parallel/duplicate system instead of extending the unified graph?
- [ ] Is anything claimed (AI-detected, real-time, production-grade) actually true of this implementation?
- [ ] Are legal citations marked `[VERIFIED]` or `[UNVERIFIED]`?
- [ ] Would this survive a technically literate judge asking "show me where this data actually comes from"?

## Documentation Update Rules

Any architectural change updates `ARCHITECTURE.md` and `DECISION_LOG.md` in the same commit/session — not deferred to "later." Any new or cut feature updates `FEATURE_REGISTRY.md`. `TASK.md` is updated at the start and end of every work session, not just at milestones.

## Testing Expectations

- Deterministic components (clock engine, escalation rules): unit tests covering every offence-category mapping and at least one missing-mapping edge case.
- Refusal gate: a held-out set of 10–15 questions (mix of answerable and deliberately ambiguous) run and scored before any demo claim about refusal behavior is made — this is currently outstanding, see `TASK.md`.
- Scale: a load test against synthetic data approaching the organizer's stated 1–2 lakh record target, with a measured (not asserted) latency number — currently outstanding, see `TASK.md`.

## Mandatory Self-Review Questions (ask before marking any task complete)

1. Did I invent anything that isn't actually in the schema, the code, or a logged decision?
2. Would this claim survive being fact-checked live by a skeptical, technically literate person?
3. Did I update the documentation that this change makes stale?
4. Is this the smallest correct change, or did I scope-creep into roadmap territory?
