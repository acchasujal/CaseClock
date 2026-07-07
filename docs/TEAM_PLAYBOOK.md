# TEAM_PLAYBOOK.md

The only document you need open daily. For *why* the product exists, read `PROJECT_CONTEXT.md` once. For deep architecture, `ARCHITECTURE.md`. This file is operations only.

## Philosophy (one line each)

Deterministic before generative. One graph, many lenses — never a parallel data store. Refuse rather than guess. Never claim what isn't built (`TASK.md` is the only source of truth on real progress).

## Engineering Lanes

| Lane | Owns |
|---|---|
| 1 — Backend Core | Clock/Dependency/Escalation engines, DB, Auth, APIs |
| 2 — Frontend | React app, all screens |
| 3 — Graph Intelligence | Aggregation, Similarity, Pattern/Risk, rule-based Forecasting |
| 4 — AI + Architecture + Integration (**Sujal**) | Copilot, refusal gate, synthetic data, API contracts, Catalyst deployment, CI/CD, all cross-lane integration and merge review |

Full reasoning: `DECISION_LOG.md` D12.

## Daily Workflow

1. Pull `main`. Check `TASK.md` for current status and blockers.
2. Before coding: read the relevant section of `EXECUTION_RULES.md`'s reasoning workflow — understand → challenge assumptions → search existing code → plan → implement → review → test.
3. Work on a branch (see naming below). Small commits.
4. Update `TASK.md` at end of session — mark what moved, what's blocked.

## Git Workflow

- **Branch naming:** `<lane>/<short-task>` — e.g. `lane1/clock-engine`, `lane4/refusal-gate`.
- **Commits:** imperative mood, scoped — `clock: add offence-category mapping table`.
- **PRs:** every merge to `main` goes through a PR, even solo work. Lane 4 (Sujal) reviews any PR touching a contract boundary (API shape, graph schema).
- **Merge:** squash-merge, one clean commit per feature.
- **Emergency merge (deadline-critical, reviewer unavailable):** the lane owner may self-merge, but must post a note in the next sync and log any architecture-relevant change in `DECISION_LOG.md` retroactively, same day — never silently.
- **Conflict resolution:** lane owner has final say inside their lane; cross-lane conflicts go to Lane 4, resolved in a 10-minute sync, not an async thread.

## Coding Workflow

- Search before writing — don't duplicate existing logic (`EXECUTION_RULES.md` rule 5).
- Deterministic logic (clock, escalation) never touched without a `DECISION_LOG.md` entry first.
- No free-generated prose about a specific person's guilt/risk — templated facts only.

## Testing Workflow

- Deterministic modules: unit tests, including the "missing mapping" edge case — never a silent guess.
- Refusal gate: the 10–15 question test set (`DECISION_LOG.md` D7) must be run and scored before any demo claim about it. Status: **not yet done** — check `TASK.md`.
- Scale: 1–2 lakh record test (`DECISION_LOG.md` D8) with a *measured* latency number, not an estimate. Status: **not yet done**.

## Deployment / Catalyst Workflow

Stack: AppSail (backend), Slate (frontend), Data Store (DB), Authentication, SmartBrowz (PDF), Cron (staleness checks), Pipelines (CI/CD). Full per-service reasoning: `ENGINEERING_OPERATING_MANUAL.md` Task 2.

**Three spikes must happen before real feature work starts, in this order:**
1. AppSail Python/FastAPI support — Lane 4
2. Data Store recursive-query support — Lane 1
3. QuickML general grounded-completion support (not just RAG) — Lane 4, **highest compliance risk in the stack**

Deploy early — a walking skeleton (one dummy endpoint + one dummy page) goes live on Catalyst before any real feature is built. Never leave first deployment to the final week.

## AI Workflow (using Claude / Codex / Copilot / Gemini / etc.)

Paste this at the start of every AI coding session in this repo:

```
Read PROJECT_CONTEXT.md, EXECUTION_RULES.md, ARCHITECTURE.md, and TASK.md before responding.
Follow EXECUTION_RULES.md's anti-hallucination rules strictly.
Search existing code before writing new code — do not duplicate.
If this task requires a schema or API contract change, stop and flag it — do not proceed silently.
```

**Required context every AI must read:** the four files above. No exceptions, regardless of which tool.

## Quality Checklist (before marking anything done)

- [ ] Matches or intentionally contradicts (and logs) an existing `DECISION_LOG.md` entry
- [ ] No parallel/duplicate system introduced
- [ ] Nothing claimed (AI-detected, real-time, production-grade) that isn't actually true of this code
- [ ] Legal citations marked `[VERIFIED]` or `[UNVERIFIED]`
- [ ] Would survive a skeptical judge asking "where does this data actually come from"

## Definition of Done

Code merged to `main`, tested per the module's acceptance criteria in `FEATURE_REGISTRY.md`, `TASK.md` updated, and — if architecture changed — `ARCHITECTURE.md`/`DECISION_LOG.md` updated in the same session.

## Before Asking a Teammate

Check `TASK.md` and `DECISION_LOG.md` first — the answer may already be logged.

## Before Asking AI

Have you searched the existing codebase? Do you know which lane owns this? Vague questions produce vague (and sometimes hallucinated) answers — be specific about the file/module.

## Before Merging

Run the Quality Checklist above. If it touches Clock/Escalation logic or the graph schema, get a second pair of eyes even if it delays the merge.

## Hackathon Submission Checklist

- [ ] Prototype Brief, GitHub, Catalyst deployment, demo video, deck — all present
- [ ] Refusal-gate test executed and scored
- [ ] Scale test executed and scored
- [ ] BNSS citations verified or explicitly marked unverified
- [ ] No unlabeled synthetic stub (financial, forecasting) presented as real
- [ ] Fresh-clone deployment verified

Full detail: `HACKATHON_MASTER_GUIDE.md` Section 14.
