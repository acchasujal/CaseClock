# DECISION_LOG.md

Every major decision made in developing this product, so future work (human or AI) doesn't re-litigate settled questions without new evidence. Ordered chronologically by when the decision was reached in the project's planning history.

---

### D1 — PS1 over PS2

**Problem:** Choose between PS1 (Conversational AI for Crime Database) and PS2 (Crime Analytics & Visualization Platform).
**Alternatives considered:** PS2 initially looked lower-competition based on a single observed low-star public repo — this evidence was later explicitly retracted as too weak (one repo isn't a proven competitive landscape).
**Chosen approach:** PS1, anchored on statutory-deadline tracking as the core differentiator rather than generic NL2SQL.
**Reason:** PS2's problem shape (hotspot dashboards) has direct public precedent from a prior KSP-hackathon-family winner, making it a more saturated space than initially assumed. PS1 allows a legally-grounded, harder-to-research differentiator (BNSS deadline tracking).
**Trade-offs:** PS1 as literally stated is chatbot-shaped, which is easy to imitate at a surface level; the deadline-tracking mechanism underneath is the actual moat.
**Lessons learned:** Weak single-data-point evidence (one repo) should not drive a strategic pivot; this was caught and corrected before being finalized.

---

### D2 — Reject single composite "risk score" for dependency tracking

**Problem:** How should case risk be computed and displayed?
**Alternatives considered:** A single opaque composite score (days-remaining × evidence-completeness % × caseload factor).
**Chosen approach:** Named, specific dependencies (FSL/CDR/statement/sign-off) mapped to the specific clock each threatens.
**Reason:** A composite score doesn't survive a knowledgeable judge asking "risk of what, exactly, and why is it high?" A named-dependency view does. Also more accurately reflects how an IO actually reasons about a case.
**Trade-offs:** Named-dependency modeling is more complex to build convincingly than a single score; if it proves too complex, the fallback is the simpler single-clock/single-score version.

---

### D3 — Multiple concurrent statutory clocks, not one

**Problem:** Initial design assumed a single 60/90-day chargesheet clock per case.
**New evidence:** Deeper BNSS research revealed multiple, distinct, concurrent clocks: pre-FIR preliminary inquiry (14 days, offence-conditional), investigation/chargesheet clock (60/90 days), document-supply-to-accused clock (14 days post-filing, Section 230), further-investigation clock (90 days, Section 193(9)).
**Chosen approach:** Model clocks as a configurable rules table keyed by offence category, supporting multiple concurrent `ClockInstance` records per case.
**Reason:** A product only tracking the single most-cited clock looks naive to a legally literate judge or prosecutor who knows the other clocks exist.
**Known limitation:** Exact section number for the default-bail trigger is inconsistently cited across secondary sources (176(2) vs 187(2) BNSS) — flagged as unverified, must be checked against bare statute text before final submission.

---

### D4 — Unified investigation graph over parallel feature modules

**Problem:** Official PS1 brief requires network analysis, pattern discovery, socio-demographic insight, profiling, decision support, financial-link analysis, forecasting — risk of building each as an independent system.
**Chosen approach:** One property graph (Case, Person, Section, Location, Officer, Dependency, ClockInstance as nodes) where every mandated capability is a query/traversal over the same structure.
**Reason:** Directly counters this team's documented recurring failure mode across prior hackathons (mock/parallel systems that don't fully integrate — see D9). Also structurally guarantees internal consistency: a chatbot and a network view built on separate stores can silently disagree; a single graph cannot.
**Trade-offs:** Requires disciplined engineering to resist "just add a separate table for speed" under deadline pressure — explicitly called out as the most likely future mistake.

---

### D5 — Honest labeling over full-coverage claims for financial-link analysis and forecasting

**Problem:** Official brief explicitly requires financial-transaction link analysis and crime forecasting/early warning; organizer-provided schema contains neither financial entities nor sufficient data for real forecasting.
**Chosen approach:** Build both as clearly-labeled, minimal stubs — synthetic `FinancialAccount`/`Transaction` nodes explicitly stated as "not real KSP data," and a rule-based threshold alert explicitly stated as "not a predictive ML model."
**Reason:** Claiming full depth on capabilities the actual schema can't support is a bigger credibility risk than honestly scoping them down — a judge's follow-up question ("is this real data?") is a single-question path to destroying trust in every other claim made in the demo.
**Rejected alternative:** Silently building a convincing-looking but fabricated financial network graph without labeling it — rejected as the single most damaging possible mistake identified across all planning rounds.

---

### D6 — Rule-based similarity and profiling instead of embedding/ML-based

**Problem:** How should case-similarity and offender-profiling features work?
**Chosen approach:** Structured feature match (shared section/location/time-window) for similarity; templated summary of graph-derived facts (prior FIR count, section diversity) for profiling — never free-generated prose about a person.
**Reason:** Preserves explainability (every result traces to specific shared attributes) and avoids the fairness/defamation exposure of an LLM generating claims about a specific person's risk or guilt.
**Trade-offs:** Lower recall than an embedding-based approach; deliberately accepted given the judging panel's stated emphasis on explainable AI.

---

### D7 — Refusal-gate testing is mandatory before any demo claim about it

**Problem:** The conversational layer's refusal-on-low-confidence behavior is central to the product's trust narrative, but has never been tested against a real question set.
**Decision:** No demo claim about refusal reliability may be made until a held-out test set (10–15 questions, answerable + ambiguous) is run and scored.
**Status:** **Unresolved as of this writing** — flagged repeatedly across planning sessions, not yet executed. This is the single most-repeated open item in the project's history.

---

### D8 — Scale test against 1–2 lakh records is mandatory before any scalability claim

**Problem:** Organizer explicitly states solutions should handle 1–2 lakh records without breaking; no load test has been run.
**Decision:** No scalability claim (in deck, pitch, or documentation) may be made until this test is actually executed with a measured latency figure.
**Status:** **Unresolved as of this writing** — flagged across multiple planning sessions.

---

### D9 — Root-cause pattern: overbuilt pipelines and mock-mode fallbacks under deadline pressure

**Problem:** Across this team's prior hackathon submissions (HackerRank Orchestrate — non-importable pipeline, circular mock evaluation logic; MuleShield — metric overclaiming later corrected; ConflictSense — mock Azure AI Search layer discovered on live repo inspection; Infosys audit — discrepancy between claimed real dataset and synthetic generator found in repo), a consistent failure pattern emerges: ambitious architecture claimed, incomplete or faked execution delivered under time pressure.
**Decision:** This documentation system (`EXECUTION_RULES.md` anti-hallucination rules, explicit MVP/Finals/Roadmap labeling throughout `FEATURE_REGISTRY.md`) exists specifically as a structural countermeasure to this pattern, not as generic engineering hygiene.
**Implication for future work:** Any claim in code, docs, or the deck that isn't verifiably true of the actual current build should be treated as a defect to fix immediately, not a cosmetic issue.

---

### D10 — Cross-case pattern-linkage "AI copilot" explicitly excluded, even from roadmap

**Problem:** A tempting "wow factor" addition — an AI feature that infers links between unrelated cases/suspects.
**Decision:** Excluded even as a stated future roadmap item, not just deferred.
**Reason:** The legal and reputational downside of a false suspect/case linkage generated by an LLM vastly outweighs demo value; this is the single feature most likely to be misused or successfully challenged by a prosecutor in a real deployment context.

---

### D12 — Engineering organization: four lanes, not developer headcount

**Problem:** Prior planning (`ENGINEERING_OPERATING_MANUAL.md` Task 6) split ownership across 3 developers, contradicting `PROJECT_CONTEXT.md`'s stated 4-person team — an unresolved contradiction flagged but not fixed at the time.
**Alternatives considered:** (a) Fix the headcount mismatch by simply adding a 4th named-developer lane matching the original Person A–D split from `IMPLEMENTATION_PLAN.md`'s earlier parallel-work-streams table. (b) Reorganize entirely around function (lane) rather than name, with AI and Integration merged under one owner.
**Chosen approach:** (b) — four engineering lanes: Backend Core, Frontend, Graph Intelligence, AI + Architecture + Integration (the last owned by Sujal).
**Reason:** AI and Integration are unusually tightly coupled in this architecture — the conversational layer's grounding depends on stable contracts from every other lane, and integration bugs are most diagnosable by whoever also owns the AI layer's expected inputs/outputs. Merging them under one owner reduces coordination overhead and directly targets D9's failure pattern (disconnected pipelines), since the integration owner is structurally forced to understand every other lane's output, not just their own.
**Trade-offs:** Lane 4 (Sujal) now sits on the critical path for two of the three remaining Catalyst spikes (AppSail, QuickML) plus all cross-lane integration — a concentration-of-risk trade accepted deliberately in exchange for reduced drift, not an oversight. If Lane 4 falls behind, there is no equivalent backup owner for integration review.
**Consequences:** `ENGINEERING_OPERATING_MANUAL.md` Task 6, `IMPLEMENTATION_PLAN.md`'s Parallel Work Streams table, and `TASK.md`'s ownership tracking are all updated to lane-based assignment in the same session this decision was made, per `EXECUTION_RULES.md`'s documentation-update rule.
**Known limitation:** This resolves the 3-vs-4 contradiction structurally but does not by itself reduce total engineering risk — it relocates coordination risk from "ambiguous ownership" to "single point of failure in Lane 4," which is a different risk, not a smaller one.

---

### D11 — Wow-moment demo design: pair deterministic escalation with a scripted (not open-floor) refusal demonstration

**Problem:** Selecting the single highest-impact demo moment.
**Alternatives considered:** Inviting judges to ask an unscripted live question (highest emotional ceiling, highest uncontrolled risk given D7's unresolved status).
**Chosen approach:** A live, staged threshold-crossing escalation immediately followed by a scripted correct-answer-then-refusal pair on the same case/screen.
**Reason:** Demonstrates the product's actual stated philosophy (deterministic where possible, honestly uncertain where not) in under 30 seconds, without exposing an untested refusal gate to fully unscripted input.
**Contingency:** Revisit the open-floor version only after D7 is resolved with a passing test score.

---

### D13 — Migration from Long-Lived Lane Branches to GitHub Flow

**Problem:** Long-lived lane integration branches (`lane1`–`lane4`) introduce significant merge conflict risks during final integration phases, create redundant PR hops, and diverge over time as different lanes complete features.
**Alternatives considered:** 
1. Maintain the 4 long-lived lane branches and perform periodic weekly synchronization merges.
2. Traditional Git Flow with a `develop` branch.
3. Git Flow with direct task merges into lane branches and lane merges to develop.
**Chosen approach:** GitHub Flow directly to `main` with short-lived feature branches (`lane{N}/task-name`).
**Reason:** Direct merges to `main` (backed by status-checked consolidated CI) enforce continuous integration, preventing "big-bang" integration conflicts in the final week. Task branches remain short-lived (under 2 days), encouraging rapid cycles, clear scope, and immediate regression visibility.
**Trade-offs:** Puts higher emphasis on the reliability of the consolidated CI pipeline on the `main` branch. A broken `main` is visible to all developers, but mitigated by a strict "revert first, diagnose second" recovery strategy.
