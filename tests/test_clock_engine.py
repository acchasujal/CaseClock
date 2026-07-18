from datetime import datetime, timezone

import pytest

from backend.app.core.clock.engine import ClockEngine, clock_status
from shared.contracts.api import ClockStatus


def test_clock_status_thresholds():
    assert clock_status(-1) == ClockStatus.OVERDUE
    assert clock_status(0) == ClockStatus.RED
    assert clock_status(7) == ClockStatus.AMBER
    assert clock_status(15) == ClockStatus.GREEN


def test_clock_engine_computes_rule_from_case():
    engine = ClockEngine(datetime(2026, 7, 18, tzinfo=timezone.utc))

    clock = engine.from_case(
        "case-1",
        {
            "offence_category": "theft",
            "reported_at": "2026-07-01T00:00:00+00:00",
        },
    )

    assert clock.clock_type == "investigation_60_day"
    assert clock.days_remaining == 43
    assert clock.bnss_reference.endswith("[VERIFIED]")


def test_clock_engine_does_not_guess_unknown_mapping():
    engine = ClockEngine(datetime(2026, 7, 18, tzinfo=timezone.utc))

    with pytest.raises(KeyError):
        engine.from_case("case-1", {"offence_category": "unknown_category"})
