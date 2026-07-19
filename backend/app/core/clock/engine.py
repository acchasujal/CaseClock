"""Deterministic statutory clock calculations for CaseClock."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from shared.constants.clock_types import ClockType, get_clock_rule
from shared.contracts.api import ClockInstanceResponse, ClockStatus


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def clock_status(days_remaining: int) -> ClockStatus:
    if days_remaining < 0:
        return ClockStatus.OVERDUE
    if days_remaining < 7:
        return ClockStatus.RED
    if days_remaining <= 14:
        return ClockStatus.AMBER
    return ClockStatus.GREEN


class ClockEngine:
    """Computes clock response objects without using AI or mutable state."""

    def __init__(self, reference_time: datetime | None = None) -> None:
        self.reference_time = reference_time or datetime.now(timezone.utc)
        if self.reference_time.tzinfo is None:
            self.reference_time = self.reference_time.replace(tzinfo=timezone.utc)

    def from_clock_node(self, node_id: str, properties: dict[str, Any]) -> ClockInstanceResponse:
        start_date = _parse_datetime(properties.get("start_date")) or self.reference_time
        deadline_date = _parse_datetime(properties.get("deadline_date")) or start_date
        days_remaining = (deadline_date.date() - self.reference_time.date()).days
        status = clock_status(days_remaining)

        return ClockInstanceResponse(
            id=node_id,
            case_id=str(properties.get("case_id", "")),
            clock_type=str(properties.get("clock_type", ClockType.INVESTIGATION_60_DAY.value)),
            start_date=start_date,
            deadline_date=deadline_date,
            days_remaining=days_remaining,
            status=status,
            bnss_reference=str(properties.get("bnss_reference") or "BNSS reference [UNVERIFIED]"),
        )

    def from_case(self, case_id: str, properties: dict[str, Any]) -> ClockInstanceResponse:
        offence_category = str(properties.get("offence_category", ""))
        rule = get_clock_rule(offence_category)
        start_date = _parse_datetime(properties.get("reported_at")) or self.reference_time
        deadline_date = start_date + timedelta(days=rule.duration_days)
        days_remaining = (deadline_date.date() - self.reference_time.date()).days

        return ClockInstanceResponse(
            id=f"computed-clock-{case_id}",
            case_id=case_id,
            clock_type=rule.clock_type.value,
            start_date=start_date,
            deadline_date=deadline_date,
            days_remaining=days_remaining,
            status=clock_status(days_remaining),
            bnss_reference=rule.bnss_reference,
        )
