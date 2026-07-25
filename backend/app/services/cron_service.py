"""backend/app/services/cron_service.py

Application service for scheduled statutory clock deadline sweeps.

Orchestrates existing domain engines and repositories without duplicating legal
deadline formulas or creating parallel persistence paths.
"""

from __future__ import annotations

import logging
import time
from uuid import uuid4
from typing import Any

from backend.app.services.audit_service import AuditService, AuditEventType
from shared.contracts.api import ClockStatus

logger = logging.getLogger(__name__)

INACTIVE_CASE_STAGES = {"closed", "disposed", "charge_sheet_filed"}


class CronService:
    """Orchestrates scheduled statutory clock recalculation and escalation checks."""

    def __init__(self, repository: Any, audit_service: AuditService) -> None:
        self._repo = repository
        self._audit = audit_service

    def run_deadline_sweep(self) -> dict[str, Any]:
        """Execute one complete scheduled deadline sweep.

        Returns:
            Structured execution summary dictionary.
        """
        start_time = time.perf_counter()
        run_id = f"cron-run-{uuid4().hex[:12]}"
        
        cases_scanned = 0
        clocks_evaluated = 0
        state_transitions = 0
        escalations_created = 0
        errors = 0

        # Retrieve active case IDs from repository
        case_ids = getattr(self._repo, "case_ids", [])
        if not case_ids and hasattr(self._repo, "nodes"):
            case_ids = [
                node_id
                for node_id, node in self._repo.nodes.items()
                if node.get("entity_type") == "Case"
            ]

        for case_id in case_ids:
            try:
                case_node = self._repo.nodes.get(case_id, {})
                stage = str(case_node.get("case_stage", "")).lower()
                if stage in INACTIVE_CASE_STAGES:
                    continue

                cases_scanned += 1

                # Reuse existing case clock and dependency calculation
                clocks = self._repo._case_clocks(case_id, case_node)
                dependencies = self._repo._case_dependencies(case_id)
                clocks_evaluated += len(clocks)

                # Check for critical or overdue transitions
                officer_id = self._repo.case_to_officer.get(case_id) if hasattr(self._repo, "case_to_officer") else None
                generated_escalations = self._repo.escalation_engine.evaluate_case(
                    case_id, clocks, dependencies, officer_id
                )

                for esc in generated_escalations:
                    is_new = self._repo.record_escalation(esc)
                    if is_new:
                        escalations_created += 1
                        state_transitions += 1
                        self._audit.record(
                            AuditEventType.DEPENDENCY_UPDATED,
                            actor_id="system-cron",
                            case_id=case_id,
                            escalation_id=esc.id,
                            reason=esc.reason,
                            run_id=run_id,
                        )

            except Exception as exc:
                errors += 1
                logger.error(
                    "Error scanning case %s during cron sweep %s: %s",
                    case_id,
                    run_id,
                    exc,
                    exc_info=True,
                )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Operational log entry for this cron run
        self._audit.record(
            AuditEventType.WORKLIST_VIEWED,
            actor_id="system-cron",
            run_id=run_id,
            cases_scanned=cases_scanned,
            clocks_evaluated=clocks_evaluated,
            state_transitions=state_transitions,
            escalations_created=escalations_created,
            errors=errors,
            duration_ms=duration_ms,
        )

        return {
            "status": "ok",
            "run_id": run_id,
            "cases_scanned": cases_scanned,
            "clocks_evaluated": clocks_evaluated,
            "state_transitions": state_transitions,
            "escalations_created": escalations_created,
            "errors": errors,
            "duration_ms": duration_ms,
        }
