# ENGINEERING_OPERATING_MANUAL.md

Source of truth for execution. Does not duplicate `EXECUTION_RULES.md` (AI reasoning behavior) or `IMPLEMENTATION_PLAN.md` (build sequence) — this document governs team/tooling coordination and the Catalyst architecture decision specifically.

**Update:** The 3-vs-4-person contradiction flagged in the original version of this document is now resolved. The project is organized around four **engineering lanes**, not developer headcount — this matches `PROJECT_CONTEXT.md`'s 4-person team and removes the ownership ambiguity Task 6 originally had to guess around. See `DECISION_LOG.md` D12. Task 6 below is rewritten accordingly.

---

## TASK 1 — Documentation Audit

| Doc | Purpose | Keep/Merge/Split/Delete | Maintenance cost |
|---|---|---|---|
| `README.md` | Entry point, setup | Keep | Low — update on structural change only |
| `PROJECT_CONTEXT.md` | Why the project exists | Keep | Low — rarely changes |
| `EXECUTION_RULES.md` | AI agent reasoning rules | Keep | Low — stable |
| `ARCHITECTURE.md` | Conceptual system design | Keep | Medium — update on real architecture change (must sync with `DECISION_LOG.md`) |
| `FEATURE_REGISTRY.md` | What to build, per feature | Keep | Medium — update when scope changes |
| `DECISION_LOG.md` | Why decisions were made | Keep | Low — append-only |
| `IMPLEMENTATION_PLAN.md` | Build sequence | Keep | Low after Phase 2 freeze — mostly historical after that |
| `TASK.md` | Live build status | Keep — **highest-traffic doc, update every session** | High, by design |
| `HACKATHON_MASTER_GUIDE.md` | Pitch/demo/deck strategy | Keep, but freeze content edits until `TASK.md` shows real progress — editing this further right now has near-zero marginal value | Medium |
| `PROTOTYPE_SUBMISSION_GUIDE.md` | Organizer's required deliverable list (external, not ours) | Keep as reference, do not edit (source is the organizer) | None |

**Weakness found in the existing set:** no single document currently states *engineering* operating procedure (branch strategy, quality gates, Catalyst service map) — that gap is what this document fills. **Recommendation: exactly one new document (this one), nothing else.** A `CATALYST.md` split-out was considered and rejected — Task 2's findings are referenced by `ARCHITECTURE.md` and `TASK.md` anyway; a separate file would drift out of sync with both.

---

## TASK 2 — Catalyst Architecture Decision (most important)

**Constraint that matters most here:** near-zero Catalyst experience, ~3 weeks to submission, and an explicit organizer statement that using a third-party alternative when a Catalyst-native equivalent exists "may affect the validity of your submission." This is not a soft preference — it's a stated compliance risk.

**Recommendation: (B) — Catalyst deployment + selected, high-ROI services.** Not (A): the compliance-risk language above makes "deployment only" a real submission-validity risk wherever a Catalyst-native service directly covers a capability we need. Not (C): maximizing Catalyst usage with zero prior experience, on a 3-week clock, risks spending the majority of remaining time learning unfamiliar paradigms instead of building Case Clock's actual differentiator (the clock/dependency/escalation logic) — this is a direct rerun of the overbuilding failure pattern in `DECISION_LOG.md` D9, just relocated to infrastructure instead of features.

### Service-by-service decision

| # | Capability | Service | Use/Skip | Reason | Complexity | Judge value | ROI |
|---|---|---|---|---|---|---|---|
| 1 | Serverless functions | Catalyst Serverless | **Skip as primary backend** | Forces rewriting the FastAPI app into function-handler paradigm — high rework risk for near-zero payoff over AppSail | High (unfamiliar model) | Low-Medium | Low |
| 2/3 | Full web app, managed runtime | Catalyst AppSail | **Use** | Runs the existing FastAPI app close to as-is (managed runtime, not a rewrite) — lowest-risk path to a compliant, Catalyst-native backend given the team's actual FastAPI experience. **[Unverified — spike immediately]** whether AppSail's managed runtime supports Python/FastAPI directly; if not, this recommendation reverses to Serverless Functions with Python support, or Docker/OCI custom runtime | Medium | High | High |
| 4 | Frontend/SPA hosting | Catalyst Slate / Web Client Hosting | **Use** | React SPA fits directly; effectively static hosting, minimal learning curve | Low | Medium | High |
| 5 | Custom domain/SSL | Domain Mappings | **Skip for MVP** | Cosmetic, not judged | Low | Low | Low |
| 6 | Relational database | Catalyst Data Store | **Use** | Hosts the graph-as-adjacency-table pattern from `ARCHITECTURE.md`. **[Unverified — top-priority spike]**: confirm SQL capability supports the recursive/multi-hop queries the graph traversal needs (co-accused, similarity). If it doesn't, `ARCHITECTURE.md`'s storage assumption needs revision before Phase 2 of `IMPLEMENTATION_PLAN.md` proceeds | Medium | High | High |
| 7 | NoSQL | Catalyst NoSQL | **Skip** | Running two data paradigms (relational + NoSQL) for one MVP graph adds complexity with no identified need | Low avoided | Low | Low |
| 8 | Object storage | Stratus | **Skip for MVP** | No confirmed blob-storage need in `FEATURE_REGISTRY.md`; revisit only if PDF export requires server-side archival rather than on-demand generation | Low | Low | Low |
| 9 | Cache | Catalyst Cache | **Skip until scale test shows a real bottleneck** | Matches `ARCHITECTURE.md`'s own stated principle against speculative caching | Low avoided | Low | Low |
| 10 | Full-text search | Data Store | **Skip** | Our copilot pattern is grounded structured-query generation, not free-text search retrieval — different mechanism, no fit | — | Low | Low |
| 11 | LLM serving / RAG | QuickML | **Use, cautiously — [Unverified, high-priority spike]** | Row 11 in the organizer's table implies QuickML is the *required* path for any LLM capability; using an external LLM API directly is the single highest compliance risk in this whole stack if QuickML can't do what we need. Must verify immediately whether QuickML supports general grounded-completion calls (not just document-RAG) suitable for our structured query-generation pattern (`DECISION_LOG.md` D6 — deliberately not embedding/RAG-based, for explainability). If QuickML is RAG-only and doesn't fit, document the gap explicitly in `DECISION_LOG.md` and accept the flagged compliance risk rather than silently using an external provider | High (unverified) | Very High if compliant | Critical — resolve before Phase 5 of `IMPLEMENTATION_PLAN.md` |
| 12/13 | AutoML / tabular | Zia AutoML | **Skip** | No tabular prediction model in scope — forecasting is deliberately rule-based (D5), not ML | — | Low | Low |
| 14 | OCR/Face/Image | Zia Services | **Skip** | Not in `FEATURE_REGISTRY.md` | — | Low | Low |
| 15 | Voice / speech-to-text / translation | Zia Services | **Use — Finals scope, not MVP-blocking** | Directly covers two explicit brief requirements (voice, Kannada) with lower build risk than custom STT/TTS/translation | Medium | High (directly named in brief) | High, deferred |
| 16 | PDF/report generation | SmartBrowz | **Use — MVP scope** | Directly covers `FEATURE_REGISTRY.md` #13 (PDF export of conversation history), avoids building a custom PDF renderer | Low | Medium | High |
| 17 | Auth | Catalyst Authentication | **Use** | Replaces the custom 3-role auth skeleton planned in `IMPLEMENTATION_PLAN.md` Phase 1 with a native service — reduces Phase 1 build time and is judge-visible native usage | Low-Medium | Medium | High |
| 18 | API Gateway | API Gateway | **Assess during Phase 0 spike, not decided yet** | Only clearly useful if AppSail doesn't already expose endpoints cleanly; don't add a routing layer with no confirmed need | Low | Low-Medium | Medium |
| 19 | OAuth/Connections | Connections | **Skip** | No third-party integration in scope | — | Low | Low |
| 20 | Cron | Catalyst Cron | **Use** | Genuine architectural fit — periodic staleness/escalation recomputation instead of only on-demand checks; a real "production-grade" signal for judges | Low | Medium | High |
| 21 | Signals (events) | Signals | **Skip for MVP** | Direct function calls or Cron polling achieve the same outcome without orchestration overhead; candidate for Finals "production evolution" slide only | — | Low (MVP) | Low (MVP) |
| 22 | Circuits (workflow orchestration) | Circuits | **Skip** | Overengineering for a sequential rule engine — directly against `EXECUTION_RULES.md`'s preference for simple maintainable code | — | Low | Low |
| 23 | Transactional email | Mail | **Use — Finals scope** | Real demo value: escalation notices that actually send, not just render on-screen | Low | Medium-High | Medium, deferred |
| 24 | Push notifications | Push Notifications | **Skip** | No mobile app in scope | — | Low | Low |
| 25 | CI/CD | Pipelines | **Use** | Directly satisfies `IMPLEMENTATION_PLAN.md` Phase 0's CI requirement natively rather than a third-party CI tool | Low | Medium | High |

### Final Stack Decision

```
Frontend  → React → Catalyst Slate / Web Client Hosting
Backend   → FastAPI (Python) → Catalyst AppSail managed runtime  [SPIKE: confirm Python/FastAPI support]
Database  → Catalyst Data Store (relational, graph-as-adjacency-table)  [SPIKE: confirm recursive query support]
Auth      → Catalyst Authentication (3-role: IO/SHO/SP)
LLM       → Catalyst QuickML  [SPIKE: confirm general grounded-completion support, not RAG-only]
PDF       → Catalyst SmartBrowz
Scheduling → Catalyst Cron (staleness/escalation recomputation)
CI/CD     → Catalyst Pipelines
Finals-only additions → Zia Services (voice/translation), Catalyst Mail
Explicitly skipped for MVP → NoSQL, Stratus, Cache, Signals, Circuits, Push Notifications, Connections, Zia AutoML/OCR
```

**Three spikes must happen before Phase 2 of `IMPLEMENTATION_PLAN.md` proceeds, in this priority order:** (1) AppSail Python/FastAPI support, (2) Data Store recursive-query support for graph traversal, (3) QuickML's actual LLM-serving capability. All three are currently `[Unverified]` — none should be assumed in `ARCHITECTURE.md` until confirmed. This directly extends `IMPLEMENTATION_PLAN.md` step 009 rather than replacing it.

---

## TASK 3 — Team Workflow (compressed, operational)

| Element | Decision |
|---|---|
| Repository | Single monorepo (`/frontend`, `/backend`, `/shared`, `/ai`, `/synthetic_data`, `/tests`, `/scripts`, `/docs`, `/configs`) — matches `README.md`'s target structure, avoids cross-repo coordination overhead for a small team |
| Branches | `main` (always deployable) + one short-lived feature branch per task, named `<initials>/<task-id>` (e.g., `sg/clock-engine`) |
| PR | Every merge to `main` via PR, even solo — enforces the self-review checklist in `EXECUTION_RULES.md` as a gate, not a suggestion |
| Merge | Squash-merge, one commit per feature, clean history |
| Release | No formal release process needed pre-submission — `main` is deployed continuously (see Task 7) |
| Testing | Unit tests required for anything touching Clock/Dependency/Escalation logic before merge (per `EXECUTION_RULES.md`); frontend/UI changes reviewed visually |
| Bug fixing | Revert-first, diagnose-second, per `EXECUTION_RULES.md`'s error-recovery process — no forward-patching under time pressure |
| Communication | Daily async status update against `TASK.md`'s status table — not a separate status doc | 
| Decision-making | Any architecture-level decision requires a `DECISION_LOG.md` entry before implementation starts, not after |
| Conflict resolution | Whoever owns the lane (see Task 6) has final say on implementation detail within it; cross-lane conflicts escalate to Lane 4 (Sujal, integration owner) via a 10-minute sync, not an async thread |

---

## TASK 4 — AI Workflow (multi-tool consistency)

**The core risk this team faces that most don't:** different AI tools (Claude, Codex, Copilot, Gemini, GPT, Antigravity) with different default behaviors, each producing code for the same repo. Without a shared contract, this produces exactly the architecture drift `DECISION_LOG.md` D9 already documents as this team's recurring failure mode — just multiplied by tool count instead of caused by time pressure alone.

**Shared AI Context:** Every AI tool session must be pointed at `PROJECT_CONTEXT.md` + `EXECUTION_RULES.md` + `ARCHITECTURE.md` + `TASK.md` before generating code — regardless of which tool. This is a process requirement on the *human*, not something enforceable by the tools themselves.

**Shared Rules:** `EXECUTION_RULES.md` is the single behavioral contract all tools must be instructed to follow — anti-hallucination rules, search-before-write, deterministic-before-generative. Paste it into the system/custom-instructions field of whichever tool is in use; do not rely on the tool reading the repo unprompted.

**Shared Contracts:** The API contract (once Phase 3 defines it) and the graph schema (once Phase 2 freezes it) are the two artifacts no AI tool is allowed to silently alter — any tool proposing a schema/contract change must produce a `DECISION_LOG.md` entry, reviewed by the module owner, before merge.

**Shared Coding Standards:** One linter/formatter config per language, committed to the repo (Task 9's `/configs`), so every tool's output is normalized to the same style regardless of what it generated natively.

**Shared Prompt Templates (paste at the start of any AI session in this repo):**
```
Read PROJECT_CONTEXT.md, EXECUTION_RULES.md, ARCHITECTURE.md, and TASK.md before responding.
Follow EXECUTION_RULES.md's anti-hallucination rules strictly.
Search existing code before writing new code — do not duplicate.
If this task requires a schema or API contract change, stop and flag it — do not proceed silently.
```

**AI Debug Workflow:** Follow `EXECUTION_RULES.md`'s debugging methodology exactly (reproduce minimally → classify deterministic vs. generative layer → root-cause before patching) — identical regardless of which AI tool is assisting.

**AI Refactor Workflow:** Any AI-proposed refactor of the clock engine or graph schema requires a human-reviewed `DECISION_LOG.md` entry before merge — no tool refactors these two components autonomously.

**AI Documentation Workflow:** Whichever tool makes an architectural change updates `ARCHITECTURE.md` and `DECISION_LOG.md` in the same session, and the human merging the PR verifies this happened — treat an undocumented architecture change as a blocking review comment, not a follow-up task.

---

## TASK 5 — High-ROI Documents Only

| Doc | Owner | Updated when | Maintainer | Generated |
|---|---|---|---|---|
| `TASK.md` | Whoever's working | Every session, start and end | Human (AI can draft, human confirms status) | Manual |
| `DECISION_LOG.md` | Module owner | Every architecture decision | Human | Manual |
| `ARCHITECTURE.md` | Module owner | On real architecture change only | Human, AI-drafted | Manual |
| `README.md` | Anyone | On structural change | Human | Manual |
| All others (`PROJECT_CONTEXT.md`, `EXECUTION_RULES.md`, `FEATURE_REGISTRY.md`, `IMPLEMENTATION_PLAN.md`, `HACKATHON_MASTER_GUIDE.md`) | Frozen | Rarely — only on genuine scope/strategy change | Human | Manual |

**Explicitly rejected:** a separate `API_CONTRACTS.md` and `DATABASE_SCHEMA.md` (per the earlier round in this thread) — auto-generate these directly from code/schema once they exist, rather than hand-maintaining documents that will drift from reality under time pressure.

---

## TASK 6 — Ownership Split (superseded — now lane-based, see `DECISION_LOG.md` D12)

| Lane | Owns | Catalyst spike ownership | Does not touch |
|---|---|---|---|
| **Lane 1 — Backend Core** | Clock Engine, Dependency Engine, Escalation Engine, Database, Authentication, Backend APIs, Validation, Business Logic | Catalyst Data Store spike (recursive-query capability) | Frontend, Graph Intelligence internals, NL layer |
| **Lane 2 — Frontend** | React app, Dashboard, Case Detail, Timeline, Dependency Graph UI, Analytics UI, Charts, Components, Theme, PDF UI | Catalyst Slate hosting | Backend business logic |
| **Lane 3 — Graph Intelligence** | Relationship Analysis, Pattern Detection, Aggregation, Similarity Engine, Graph Algorithms, Risk Analysis, Crime Analytics, Forecasting | — | Clock/Escalation logic (Lane 1), NL layer (Lane 4). **Forecasting here means the rule-based threshold alert per `DECISION_LOG.md` D5 — not an ML model; scope creep into real predictive ML is an explicit non-goal for this lane.** |
| **Lane 4 — AI + Architecture + Integration (Owner: Sujal)** | Conversational Copilot, Prompt System, Grounding, Refusal Gate, Explainability, Synthetic Data Generator, AI Evaluation, QuickML Integration, Shared Types, API Contracts, Repository Architecture, Documentation, Catalyst Deployment, CI/CD, Merge Reviews, Integration, Release, Demo Integration | Catalyst AppSail spike, QuickML spike (both highest-priority, per prior spike-priority ordering) | Does not own feature logic inside Lanes 1–3, only their contracts/integration points |

**Reasoning carried over from the new decision (`DECISION_LOG.md` D12):** AI and Integration are tightly coupled — keeping both under one owner (Lane 4) reduces coordination overhead and directly targets this team's documented D9 failure pattern (disconnected pipelines), since the person most exposed to every other lane's output is the one responsible for making sure it actually integrates.

**Note on the two remaining Catalyst spikes:** Data Store (Lane 1) and AppSail + QuickML (Lane 4) are still `[Unverified]` per the original Task 2 findings — lane ownership doesn't change that status, it only clarifies who's accountable for resolving it.

---

## TASK 7 — Integration Strategy

Merge to `main` at least once daily per lane, smaller PRs preferred over large ones. **Integration owner: Lane 4 (Sujal)** reviews any PR that touches a contract boundary — this is now explicit in the lane definition, not inferred from who happens to own the API layer. API/schema evolution requires the `DECISION_LOG.md` entry from Task 4 before the PR is opened, not during review. Frontend/backend coordination happens against the real deployed API (per `IMPLEMENTATION_PLAN.md`'s "no prolonged mock-only development" principle), not indefinitely against a mock contract.

---

## TASK 8 — Quality Gates

| Gate | Checklist |
|---|---|
| Commit | Passes local lint/type-check |
| Push | CI (Pipelines) green |
| PR | Self-review checklist from `EXECUTION_RULES.md` completed; `DECISION_LOG.md` updated if architecture changed |
| Merge | At least one other person's eyes on it, even briefly |
| Deployment | Clean-clone deploy succeeds (per `IMPLEMENTATION_PLAN.md` Phase 8 acceptance criteria) |
| Demo | Full flow rehearsed twice, fallback recording ready |
| Submission | Full checklist in `HACKATHON_MASTER_GUIDE.md` Section 14 |

---

## TASK 9 — Repository Structure

Matches `README.md`'s target structure exactly — no changes needed:
```
/backend  (/graph /clock_engine /dependency /escalation /aggregation /similarity /nl_layer /api /auth /config /logging /errors /validation)
/frontend (/case_detail /worklist /pattern_rollup /escalation_queue /copilot)
/shared   (types/contracts shared between frontend and backend, if the stack supports it)
/ai       (prompt templates, refusal-gate test set, grounding logic docs)
/synthetic_data (/generator /seed /scale_test)
/tests
/scripts  (deployment, spike scripts for the 3 Catalyst verifications above)
/docs     (this entire documentation set)
/configs  (shared lint/format config)
/assets   (deck, demo video source files — not code)
```

---

## TASK 10 — This Document Is the Manual

Sections 1–9 above constitute the operating manual. Restated as a linear path:

**Day 1:** Resolve the 3-vs-4-person contradiction. Run the three Catalyst spikes (AppSail, Data Store recursion, QuickML) in priority order. Log findings in `TASK.md` and, if any assumption in `ARCHITECTURE.md` breaks, log the correction in `DECISION_LOG.md` immediately.
**Days 2–on:** Follow `IMPLEMENTATION_PLAN.md`'s numbered sequence, using the ownership split (Task 6, corrected for real headcount) and the AI workflow contract (Task 4) for every session, on every tool.
**Ongoing:** `TASK.md` updated every session. Quality gates (Task 8) enforced at every merge, not just before submission.

**Risk register:** unchanged from `HACKATHON_MASTER_GUIDE.md` Section 12, plus one addition specific to this document — **multi-tool AI drift**, mitigated only by the shared-context discipline in Task 4, which depends entirely on humans actually pasting the context every session. This is a process risk, not a technical one, and is the single most likely new failure mode this manual introduces if skipped.

**Critical path:** unchanged from `IMPLEMENTATION_PLAN.md`, with the three Catalyst spikes now explicitly inserted before step 019 (schema design) rather than left implicit inside step 009.

---

## VERDICT

Use Catalyst AppSail + Data Store + Authentication + SmartBrowz + Cron + Pipelines for MVP, QuickML pending a compliance-critical spike, Zia Voice/Mail deferred to Finals — Option B, not A or C.

## KEY INSIGHT

The QuickML compliance question is a bigger unresolved risk right now than anything in the workflow/ownership tasks — a wrong guess here doesn't just cost engineering time, it risks the organizer's stated "may affect validity of submission" penalty on the entire conversational-AI core of the product.

## MOST LIKELY MISTAKE

Treating this document as complete before running the three spikes — every recommendation in Task 2 is conditional on verification that hasn't happened yet.

## BIGGEST RISK

The 3-vs-4-person contradiction is now resolved via lane-based ownership (`DECISION_LOG.md` D12), but this shifts the risk rather than eliminating it: Lane 4 (Sujal) now sits on the critical path for both remaining spikes (AppSail, QuickML) plus all integration — a single point of failure if that lane falls behind, worth naming explicitly rather than assuming lanes alone solve coordination risk.

## BEST ALTERNATIVE

If AppSail turns out not to support Python/FastAPI cleanly, fall back to Catalyst Serverless Functions with a Python runtime, accepting the rewrite cost — worse than AppSail, still better than a third-party host given the compliance-risk language in the organizer's service table.

## NEXT BEST ACTION

Run the AppSail, Data Store, and QuickML spikes today, owned per the lane table in Task 6 — all three still block Phase 2 of `IMPLEMENTATION_PLAN.md` and none has been started per `TASK.md`.

## CONFIDENCE

High on the Option B reasoning and the general service-selection logic. Low on three specific items (AppSail Python support, Data Store recursive query support, QuickML's actual serving capability) — all marked `[Unverified]` and none should be treated as settled until spiked.
