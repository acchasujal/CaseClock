"""Clock factory for active, near-deadline, and expired statutory clocks."""

from __future__ import annotations

from datetime import timedelta
from random import Random
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.graph.entities import ClockInstance
from backend.app.core.graph.enums import GraphEntityType

from shared.constants.clock_types import ClockType, get_clock_rule

from synthetic_data.configs import SyntheticDataConfig, SyntheticNodeRecord, build_faker, clock_type_choices, choose_weighted, stable_uuid, utc_now
from synthetic_data.factories.case_factory import CaseBlueprint


class ClockRecord(BaseModel):
    node: SyntheticNodeRecord
    case_id: UUID
    clock_type: ClockType
    start_date: object
    deadline_date: object
    status: str
    days_remaining: int

    model_config = ConfigDict(arbitrary_types_allowed=True)


def build_clock_records(
    config: SyntheticDataConfig,
    rng: Random,
    case_blueprints: list[CaseBlueprint],
) -> list[ClockRecord]:
    fake = build_faker(config.seed + 53)
    records: list[ClockRecord] = []
    snapshot = utc_now()
    clock_types = list(clock_type_choices())

    for index, blueprint in enumerate(case_blueprints):
        primary_clock_type = get_clock_rule(blueprint.offence_category).clock_type
        records.append(_make_clock_record(fake, blueprint, primary_clock_type, index, snapshot, rng))
        if index % 3 == 0:
            secondary_clock_type = clock_types[2 if index % 2 == 0 else 3]
            records.append(_make_clock_record(fake, blueprint, secondary_clock_type, index + 500, snapshot, rng))

    return records


def _make_clock_record(fake, blueprint: CaseBlueprint, clock_type: ClockType, index: int, snapshot, rng: Random) -> ClockRecord:
    case = blueprint.case
    
    if clock_type == ClockType.DOCUMENT_SUPPLY:
        rule = get_clock_rule("document_supply")
    elif clock_type == ClockType.FURTHER_INVESTIGATION:
        rule = get_clock_rule("further_investigation")
    else:
        rule = get_clock_rule(blueprint.offence_category)

    clock_duration = rule.duration_days
    bnss_reference = rule.bnss_reference

    if blueprint.risk_band == "overdue":
        days_remaining = -rng.randint(1, 20)
    elif blueprint.risk_band == "red":
        days_remaining = rng.randint(0, 6)
    elif blueprint.risk_band == "amber":
        days_remaining = rng.randint(7, 14)
    else:
        days_remaining = rng.randint(15, 45)
    deadline_date = snapshot + timedelta(days=days_remaining)
    start_date = deadline_date - timedelta(days=clock_duration)
    status = _clock_status(days_remaining)
    clock_id = stable_uuid("clock", str(case.id), clock_type.value, str(index))
    created_at = start_date
    return ClockRecord(
        node=SyntheticNodeRecord(
            entity_type=GraphEntityType.CLOCK_INSTANCE,
            entity=ClockInstance(id=clock_id, created_at=created_at, updated_at=deadline_date),
            properties={
                "case_id": str(case.id),
                "clock_type": clock_type.value,
                "start_date": start_date,
                "deadline_date": deadline_date,
                "status": status,
                "days_remaining": days_remaining,
                "bnss_reference": bnss_reference,
                "stage": blueprint.case_stage,
            },
        ),
        case_id=case.id,
        clock_type=clock_type,
        start_date=start_date,
        deadline_date=deadline_date,
        status=status,
        days_remaining=days_remaining,
    )


def _clock_status(days_remaining: int) -> str:
    if days_remaining < 0:
        return "overdue"
    if days_remaining < 7:
        return "red"
    if days_remaining < 15:
        return "amber"
    return "green"