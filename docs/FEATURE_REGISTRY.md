# FEATURE_REGISTRY.md

Every planned feature, described by intent (purpose, users, workflow, acceptance criteria) — not implementation. Cross-reference `ARCHITECTURE.md` for how these map onto the unified graph, and `TASK.md` for build status.

Status legend: **MVP** (must exist for hackathon submission) / **Finals** (post-shortlist refinement) / **Roadmap** (explicitly not built, stated aspiration only).

---

## 1. Legal Clock Engine — MVP

**Purpose:** Compute which statutory clock(s) apply to a case and how many days remain.
**Users:** IO (primary), SHO/SP (rollup).
**Business value:** Converts an invisible, memory-dependent deadline into a visible, system-owned fact.
**Inputs:** Offence category/section, FIR date, current date, case stage.
**Outputs:** One or more active `ClockInstance` records with deadline and days-remaining.
**Workflow:** On case ingestion, look up offence category in the clock-rules mapping table; instantiate applicable clock(s) — investigation/chargesheet (60/90 day), and post-filing clocks (document-supply, further-investigation) once case reaches that stage.
**Edge cases:** Offence category not found in mapping table → case must be excluded from auto-escalation and separately flagged as "clock undetermined," never silently defaulted to a guessed value.
**Dependencies:** Accurate offence-category → clock-type mapping table (must be built and verified against BNSS text, not assumed).
**Acceptance criteria:** Every case in the synthetic dataset resolves to a clock or an explicit "undetermined" flag — never a silent null.
**Known risks:** Exact statutory section number for default bail is unverified (see `PROJECT_CONTEXT.md`) — do not hardcode into user-facing text until checked.

## 2. Dependency Tracker — MVP

**Purpose:** Track named, specific outstanding evidentiary items per case (FSL, CDR, witness statement, supervisory sign-off), replacing a single opaque "risk score" (a prior design explicitly rejected — see `DECISION_LOG.md`).
**Users:** IO (updates status), SHO/SP (views blockers).
**Inputs:** Dependency type, requested date, status (pending/returned), owner.
**Outputs:** Per-case list of named blockers with staleness indicator.
**Workflow:** IO logs a dependency when requested; status updates manually (not assumed automatable, given documented low digital-literacy adoption risk) or via synthetic-data simulation for demo purposes.
**Edge cases:** Case with no logged dependency but flagged at-risk → must show "reason undetermined," never a fabricated reason.
**Acceptance criteria:** Every at-risk case shows at least one named, real dependency or an explicit undetermined flag.

## 3. Escalation Rule Engine — MVP

**Purpose:** Deterministically notify the correct supervisor when a case crosses a risk threshold (days remaining + unresolved dependency + staleness).
**Users:** SHO/SP (recipients), IO (source case).
**Workflow:** Rule-based trigger (not LLM-based) fires when configured conditions align; auto-drafts a plain-language escalation note addressed by correct rank (per organizer's stated DGP/IGP/DIG/SP hierarchy).
**Edge cases:** Clock mapping missing for a case → excluded from auto-escalation, flagged separately (never mis-escalated on a guessed clock).
**Acceptance criteria:** Escalation event is logged immutably in the audit log; the live demo threshold-crossing must be reproducible, not a one-off scripted animation.

## 4. Risk-Ranked Worklist — MVP

**Purpose:** Sort an IO's cases by risk + staleness instead of FIR number/date.
**Users:** IO (daily use).
**Acceptance criteria:** Ranking updates when dependency status changes; ties broken by days-remaining.

## 5. Criminal Network Analysis — MVP (co-accused only), Finals (broader link types)

**Purpose:** Surface shared accused/victim links across cases (PS1-mandated "criminal network analysis").
**Workflow:** 1–2 hop traversal over the unified graph: `Person —[ACCUSED_IN]→ Case`, derive `CO_ACCUSED_WITH` when two people share a Case.
**Edge cases:** Relies on entity resolution (see `PROJECT_CONTEXT.md` — unresolved risk). MVP synthetic dataset must deliberately engineer some repeat entities across cases, or this feature has nothing real to show.
**Acceptance criteria:** At least one demo case shows a genuine, non-trivial (not same-case) cross-case link.
**Known limitations:** No fuzzy name matching in MVP — only exact/near-exact synthetic matches.

## 6. Crime Pattern & Trend Analytics — MVP

**Purpose:** Aggregate cases by crime type × district × time (PS1-mandated "crime pattern discovery").
**Workflow:** Grouped aggregation query over the same `Case` nodes used by the clock engine — no separate analytics store.
**Acceptance criteria:** District rollup screen shows at least one real, non-trivial pattern in synthetic data (e.g., a seasonal spike).

## 7. Socio-Demographic Insight — MVP (shallow, explicitly labeled)

**Purpose:** Aggregate available demographic attributes (age, gender — the only fields the organizer schema actually provides) against case type/location.
**Known limitation:** Organizer schema has no income/education/migration fields. This feature must be presented as shallow-but-honest, not implied to be deep sociological correlation analysis — a documented judging-panel risk if overclaimed.

## 8. Offender Profiling / Lead Prioritization — MVP (rule-based, narrowly framed)

**Purpose:** Surface repeat-offender signal (count of prior `ACCUSED_IN` edges, section diversity, recency) as an investigative lead signal — never a guilt or reoffense-risk inference.
**Acceptance criteria:** Output text is templated from graph facts only ("3 prior FIRs, same section category") — never open-ended generated prose about the person. This is an anti-hallucination and fairness requirement, not a style preference.

## 9. Case Similarity Discovery — MVP (structured similarity only)

**Purpose:** Find similar past cases by shared section combination, location, and time window.
**Workflow:** Rule-based feature match (Jaccard/cosine over structured attributes) — explicitly not a deep embedding model, so it stays explainable.
**Acceptance criteria:** Every similarity result displays the specific shared features that produced the ranking.

## 10. Conversational Copilot (English) — MVP

**Purpose:** Grounded natural-language query over the graph, satisfying PS1's core conversational-AI requirement.
**Workflow:** NL input → deterministic grounding/verification gate → query execution → path-annotated response, OR refusal if confidence is low.
**Acceptance criteria:** A held-out test set (10–15 questions, answerable + ambiguous) is run and scored before any demo claim about refusal reliability is made. **This has not yet been done as of this writing — see `TASK.md`.**

## 11. Kannada Language Support — Finals (thin wrapper, explicitly labeled)

**Purpose:** Satisfy PS1's explicit bilingual requirement.
**Known limitation:** Implemented as a translation-layer wrapper around the English grounded-query engine, not deep bilingual NLU. Must be labeled as such in the deck to avoid overclaiming.

## 12. Voice Interaction — Finals

**Purpose:** Satisfy PS1's explicit voice-interaction requirement.
**Workflow:** Browser-native speech-to-text/text-to-speech wrapped around the existing NL layer — no new reasoning component.

## 13. Conversation History PDF Export — MVP (trivial)

**Purpose:** Satisfy PS1's explicit requirement to save conversation history in PDF, locally.
**Workflow:** Store `ConversationLog` per session; render and export on demand.

## 14. Role-Based Access (shallow) — MVP (3 roles), Roadmap (full ABAC)

**Purpose:** Satisfy PS1's explicit RBAC/governance requirement.
**MVP scope:** Three roles — IO/SHO/SP — gating which screens and case scopes are visible. Not full attribute-based access control.

## 15. Audit Log — MVP (basic), Roadmap (full compliance-grade)

**Purpose:** Immutable log of views/edits/escalations — supports explainability and governance requirements.
**MVP scope:** Append-only log of key events (escalation fired, case viewed, copilot query + answer/refusal).

## 16. Financial Transaction Link Analysis — Finals (explicitly labeled synthetic stub)

**Purpose:** Satisfy PS1's explicit financial-crime-link requirement.
**Known limitation:** Organizer-provided schema contains no financial/transaction entities at all. This feature requires wholly synthetic `FinancialAccount`/`Transaction` nodes built for demo purposes only. Must be labeled on-slide as "synthetic extension, not real KSP data" — the single highest overclaiming risk in the entire feature set if mislabeled.

## 17. Crime Forecasting / Early Warning — Finals (rule-based threshold alert only)

**Purpose:** Satisfy PS1's explicit forecasting/early-warning requirement.
**Known limitation:** Implemented as a threshold-crossing alert on trend aggregation (e.g., case count in a subcategory exceeds a rolling baseline), explicitly NOT a predictive ML model, due to well-documented feedback-loop bias risks in predictive policing generally. Must be narrated honestly in the demo as a deliberate choice, not a limitation to hide.

## Excluded from MVP (Roadmap only — see `PROJECT_CONTEXT.md` Non-Goals)

Prosecutor workflow, mobile app, offline mode, full ABAC, cross-case pattern-linkage copilot (deliberately excluded even from roadmap discussion due to legal-exposure risk from false linkage), real entity resolution, real Kannada NLU depth.
