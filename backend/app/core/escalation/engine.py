"""Rule-based escalation generation for clock/dependency risk."""

from __future__ import annotations

from datetime import datetime, timezone

from shared.contracts.api import ClockInstanceResponse, DependencyResponse, EscalationResponse


class EscalationEngine:
    """Creates deterministic escalation notices from clocks and blockers."""

    def __init__(self, reference_time: datetime | None = None) -> None:
        self.reference_time = reference_time or datetime.now(timezone.utc)
        if self.reference_time.tzinfo is None:
            self.reference_time = self.reference_time.replace(tzinfo=timezone.utc)

    def evaluate_case(
        self,
        case_id: str,
        clocks: list[ClockInstanceResponse],
        dependencies: list[DependencyResponse],
        officer_id: str | None = None,
    ) -> list[EscalationResponse]:
        if not clocks:
            return []

        urgent_clock = min(clocks, key=lambda clock: clock.days_remaining)
        pending = [dep for dep in dependencies if dep.status.value != "resolved"]
        stale = [dep for dep in pending if dep.days_stale >= 7]

        if urgent_clock.days_remaining > 14 and not stale:
            return []
        if not pending and urgent_clock.days_remaining >= 0:
            return []

        lead_dependency = max(pending or dependencies, key=lambda dep: dep.days_stale, default=None)
        if lead_dependency is None:
            reason = (
                f"Case {case_id} has {urgent_clock.days_remaining} day(s) remaining on "
                f"{urgent_clock.clock_type}; no blocker is recorded."
            )
        else:
            reason = (
                f"{lead_dependency.name} has been pending for {lead_dependency.days_stale} day(s), "
                f"with {urgent_clock.days_remaining} day(s) remaining on {urgent_clock.clock_type}."
            )

        routed_rank = "SP" if urgent_clock.days_remaining < 0 else "SHO"
        return [
            EscalationResponse(
                id=f"esc-{case_id}-{urgent_clock.id}",
                case_id=case_id,
                triggered_at=self.reference_time,
                reason=reason,
                routed_to_rank=routed_rank,
                routed_to_officer_id=officer_id or routed_rank,
                resolved=False,
            )
        ]
