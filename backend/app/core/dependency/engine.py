"""Dependency tracker calculations for named evidentiary blockers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from shared.contracts.api import DependencyResponse, DependencyStatus


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class DependencyEngine:
    """Normalizes dependency graph nodes into API contract responses."""

    def __init__(self, reference_time: datetime | None = None) -> None:
        self.reference_time = reference_time or datetime.now(timezone.utc)
        if self.reference_time.tzinfo is None:
            self.reference_time = self.reference_time.replace(tzinfo=timezone.utc)

    def from_node(self, node_id: str, properties: dict[str, Any]) -> DependencyResponse:
        status = str(properties.get("status", DependencyStatus.PENDING.value))
        requested_at = _parse_datetime(properties.get("requested_at"))
        resolved_at = _parse_datetime(properties.get("resolved_at"))

        if status == DependencyStatus.RESOLVED.value:
            days_stale = 0
        elif requested_at is not None:
            days_stale = max((self.reference_time.date() - requested_at.date()).days, 0)
        else:
            days_stale = int(properties.get("days_stale") or 0)

        if resolved_at is not None:
            days_stale = 0

        return DependencyResponse(
            id=node_id,
            case_id=str(properties.get("case_id", "")),
            name=str(properties.get("name") or properties.get("dependency_type") or "Unspecified dependency"),
            status=DependencyStatus(status),
            days_stale=days_stale,
            assigned_to=self._assigned_to(properties),
        )

    def _assigned_to(self, properties: dict[str, Any]) -> str | None:
        assigned_to = properties.get("assigned_to")
        if assigned_to:
            return str(assigned_to)
        officer_id = properties.get("assigned_to_officer_id")
        if officer_id:
            return f"Officer {officer_id}"
        return None
