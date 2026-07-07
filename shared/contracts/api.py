"""
shared/contracts/api.py

Authoritative Python-side API contract types for CaseClock.
This file is owned by Lane 4 (Sujal). No other lane may modify it without Lane 4 sign-off.

RULE: If you need a type that doesn't exist here, open an issue tagged risk/contract-change.
Do NOT define local types that duplicate or diverge from these — import from here instead.

Kept in sync with shared/contracts/api.ts (TypeScript mirror).
Every change is logged in shared/contracts/CHANGELOG.md.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    IO = "IO"     # Investigating Officer
    SHO = "SHO"   # Station House Officer
    SP = "SP"     # Superintendent of Police / DCP


class ClockStatus(str, Enum):
    GREEN = "green"    # > 14 days remaining
    AMBER = "amber"    # 7–14 days remaining
    RED = "red"        # < 7 days remaining
    OVERDUE = "overdue"  # Deadline passed without chargesheet


class DependencyStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


# ── Clock Instance ─────────────────────────────────────────────────────────────

class ClockInstanceResponse(BaseModel):
    """A single statutory deadline instance attached to a case."""
    id: str
    case_id: str
    clock_type: str             # from shared/constants/clock_types.ClockType
    start_date: datetime        # Date of arrest / triggering event
    deadline_date: datetime     # Computed deadline (start + duration_days)
    days_remaining: int         # Computed at query time, not stored
    status: ClockStatus
    bnss_reference: str         # Must include [VERIFIED] or [UNVERIFIED]


# ── Dependency ─────────────────────────────────────────────────────────────────

class DependencyResponse(BaseModel):
    """A named, specific outstanding evidentiary item blocking chargesheet filing."""
    id: str
    case_id: str
    name: str               # e.g. "FSL report", "CDR analysis", "Section 183 statement"
    status: DependencyStatus
    days_stale: int         # How long this dependency has been unresolved
    assigned_to: Optional[str] = None


# ── Case ──────────────────────────────────────────────────────────────────────

class CaseSummaryResponse(BaseModel):
    """Lightweight case representation for the risk-ranked worklist."""
    id: str
    fir_number: str
    station_name: str
    offence_category: str
    clock: ClockInstanceResponse
    unresolved_dependency_count: int
    risk_rank: int          # Computed: lower = more urgent


class CaseDetailResponse(BaseModel):
    """Full case object for the Case Detail screen."""
    id: str
    fir_number: str
    station_name: str
    offence_category: str
    clocks: list[ClockInstanceResponse]
    dependencies: list[DependencyResponse]
    # Network and similarity populated by separate endpoints to avoid over-fetching
    # co_accused populated from graph traversal — never LLM-inferred


# ── Escalation ────────────────────────────────────────────────────────────────

class EscalationResponse(BaseModel):
    """An auto-generated escalation notice."""
    id: str
    case_id: str
    triggered_at: datetime
    reason: str             # Templated from graph-derived facts, never LLM prose
    routed_to_rank: str     # Supervisor rank derived from Officer/Unit hierarchy
    routed_to_officer_id: str
    resolved: bool


# ── Copilot ───────────────────────────────────────────────────────────────────

class CopilotQueryRequest(BaseModel):
    """NL query from the investigator."""
    query: str
    case_id: Optional[str] = None   # If scoped to a specific case
    user_role: UserRole


class CopilotQueryResponse(BaseModel):
    """
    Grounded copilot response.
    If confidence is low, the system refuses rather than guesses.
    Refusal is a first-class, tested behavior — not an afterthought.
    """
    answer: Optional[str] = None    # None if refused
    refused: bool
    refusal_reason: Optional[str] = None   # Templated, not LLM-generated
    reasoning_path: Optional[list[str]] = None   # Node/edge path that produced the answer
    confidence: float       # 0.0–1.0; below threshold → refused


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
