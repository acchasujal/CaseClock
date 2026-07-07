/**
 * shared/contracts/api.ts
 *
 * Authoritative TypeScript-side API contract types for CaseClock.
 * This file is owned by Lane 4 (Sujal). No other lane may modify it without Lane 4 sign-off.
 *
 * RULE: Import types from here — do NOT redeclare them in frontend/src/types/.
 * If you need a type that doesn't exist here, open an issue tagged risk/contract-change.
 *
 * Kept in sync with shared/contracts/api.py (Python mirror).
 * Every change is logged in shared/contracts/CHANGELOG.md.
 */

// ── Enums ────────────────────────────────────────────────────────────────────

export type UserRole = "IO" | "SHO" | "SP";

export type ClockStatus = "green" | "amber" | "red" | "overdue";

export type DependencyStatus = "pending" | "resolved" | "escalated";

// ── Clock Instance ────────────────────────────────────────────────────────────

export interface ClockInstanceResponse {
  id: string;
  case_id: string;
  clock_type: string;        // from shared/constants/clock_types.ClockType
  start_date: string;        // ISO 8601
  deadline_date: string;     // ISO 8601
  days_remaining: number;    // Computed at query time
  status: ClockStatus;
  bnss_reference: string;    // Must include [VERIFIED] or [UNVERIFIED]
}

// ── Dependency ────────────────────────────────────────────────────────────────

export interface DependencyResponse {
  id: string;
  case_id: string;
  name: string;              // e.g. "FSL report", "CDR analysis"
  status: DependencyStatus;
  days_stale: number;
  assigned_to?: string;
}

// ── Case ──────────────────────────────────────────────────────────────────────

export interface CaseSummaryResponse {
  id: string;
  fir_number: string;
  station_name: string;
  offence_category: string;
  clock: ClockInstanceResponse;
  unresolved_dependency_count: number;
  risk_rank: number;         // Lower = more urgent
}

export interface CaseDetailResponse {
  id: string;
  fir_number: string;
  station_name: string;
  offence_category: string;
  clocks: ClockInstanceResponse[];
  dependencies: DependencyResponse[];
}

// ── Escalation ────────────────────────────────────────────────────────────────

export interface EscalationResponse {
  id: string;
  case_id: string;
  triggered_at: string;      // ISO 8601
  reason: string;            // Templated from graph-derived facts, never LLM prose
  routed_to_rank: string;
  routed_to_officer_id: string;
  resolved: boolean;
}

// ── Copilot ───────────────────────────────────────────────────────────────────

export interface CopilotQueryRequest {
  query: string;
  case_id?: string;
  user_role: UserRole;
}

export interface CopilotQueryResponse {
  answer?: string;           // undefined if refused
  refused: boolean;
  refusal_reason?: string;   // Templated, not LLM-generated
  reasoning_path?: string[]; // Node/edge path that produced the answer
  confidence: number;        // 0.0–1.0
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  role: UserRole;
}
