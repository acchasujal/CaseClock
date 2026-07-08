"""Dependency factory for named blockers and stale workflow items."""

from __future__ import annotations

from datetime import timedelta
from random import Random
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.graph.entities import Dependency
from backend.app.core.graph.enums import GraphEntityType

from synthetic_data.configs import SyntheticDataConfig, SyntheticNodeRecord, build_faker, choose_weighted, stable_uuid, utc_now
from synthetic_data.factories.case_factory import CaseBlueprint
from synthetic_data.factories.officer_factory import OfficerProfile


class DependencyRecord(BaseModel):
    node: SyntheticNodeRecord
    case_id: UUID
    dependency_type: str
    status: str
    requested_at: object
    due_at: object
    resolved_at: object | None = None
    assigned_to_officer_id: UUID | None = None
    days_stale: int = 0

    model_config = ConfigDict(arbitrary_types_allowed=True)


def build_dependency_records(
    config: SyntheticDataConfig,
    rng: Random,
    case_blueprints: list[CaseBlueprint],
    officers: list[OfficerProfile],
) -> list[DependencyRecord]:
    fake = build_faker(config.seed + 31)
    cases = [blueprint.case for blueprint in case_blueprints]
    dependency_types = ["FSL report", "CDR report", "witness statement", "supervisory sign-off", "document retrieval"]
    dependency_weights = [0.40, 0.23, 0.17, 0.10, 0.10]
    status_choices = [("pending", 0.55), ("resolved", 0.30), ("escalated", 0.15)]

    records: list[DependencyRecord] = []
    for index in range(config.dependency_count):
        case = rng.choice(cases)
        dependency_type = rng.choices(dependency_types, weights=dependency_weights, k=1)[0]
        status = choose_weighted(rng, status_choices)
        requested_at = case.entity.created_at + timedelta(days=rng.randint(0, 14))
        due_at = requested_at + timedelta(days=rng.randint(7, 45))
        resolved_at = None
        if status == "resolved":
            resolved_at = requested_at + timedelta(days=rng.randint(1, max(2, (due_at - requested_at).days - 1)))
        assigned_officer = rng.choice(officers)
        days_stale = max(0, (utc_now() - due_at).days) if status == "pending" else max(0, (resolved_at - requested_at).days if resolved_at else 0)
        dependency_id = stable_uuid("dependency", str(case.id), dependency_type, str(index))
        records.append(
            DependencyRecord(
                node=SyntheticNodeRecord(
                    entity_type=GraphEntityType.DEPENDENCY,
                    entity=Dependency(id=dependency_id, created_at=requested_at, updated_at=resolved_at or due_at),
                    properties={
                        "case_id": str(case.id),
                        "dependency_type": dependency_type,
                        "status": status,
                        "requested_at": requested_at,
                        "due_at": due_at,
                        "resolved_at": resolved_at,
                        "assigned_to_officer_id": str(assigned_officer.node.id),
                        "days_stale": days_stale,
                        "notes": fake.sentence(nb_words=8),
                    },
                ),
                case_id=case.id,
                dependency_type=dependency_type,
                status=status,
                requested_at=requested_at,
                due_at=due_at,
                resolved_at=resolved_at,
                assigned_to_officer_id=assigned_officer.node.id,
                days_stale=days_stale,
            )
        )
    return records