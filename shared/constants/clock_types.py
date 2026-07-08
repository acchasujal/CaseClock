"""
shared/constants/clock_types.py

Offence-category → clock-type mapping table.
This is a LOAD-BEARING module. Every other component (clock engine, graph aggregation,
frontend display) depends on this being correct.

RULES (per EXECUTION_RULES.md):
- Never modify this file without a DECISION_LOG.md entry.
- Every BNSS section reference must be marked [VERIFIED] or [UNVERIFIED].
- Do not add an offence category without verifying it against bare BNSS/BNS text.
- The missing-mapping edge case (offence_category not in this dict) must be handled
  by callers — never silently assume a default.

CURRENT STATUS: All entries are [UNVERIFIED] until checked against bare statute text.
The default-bail trigger section number (176(2) vs 187(2) BNSS) is explicitly unresolved.
"""

from enum import Enum
from dataclasses import dataclass


class ClockType(str, Enum):
    """Statutory clock types per BNSS. [UNVERIFIED — verify section numbers before demo]"""

    # Investigation/chargesheet deadline clocks
    INVESTIGATION_60_DAY = "investigation_60_day"   # Non-serious offences [UNVERIFIED]
    INVESTIGATION_90_DAY = "investigation_90_day"   # Serious offences [UNVERIFIED]

    # Post-filing clocks (may run concurrently with investigation clock)
    DOCUMENT_SUPPLY = "document_supply"             # Supplying docs to accused [UNVERIFIED]
    FURTHER_INVESTIGATION = "further_investigation" # Post-chargesheet further investigation [UNVERIFIED]


@dataclass(frozen=True)
class ClockRule:
    """A single clock rule: clock type, duration in days, and verification status."""
    clock_type: ClockType
    duration_days: int
    bnss_reference: str  # Must include [VERIFIED] or [UNVERIFIED] suffix
    notes: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# OFFENCE CATEGORY → CLOCK RULE MAPPING
#
# Keys are offence category strings as they will appear in the CaseMaster table.
# Values are the applicable ClockRule.
#
# ALL ENTRIES BELOW ARE STUBS — they must be verified against BNSS/BNS text
# before any clock calculation claim is made in demo or documentation.
# ──────────────────────────────────────────────────────────────────────────────

CLOCK_RULES: dict[str, ClockRule] = {
    "serious_offence": ClockRule(
        clock_type=ClockType.INVESTIGATION_90_DAY,
        duration_days=90,
        bnss_reference="BNSS §[UNVERIFIED — verify section number before asserting]",
        notes="Serious offences per BNSS. Category boundary [UNVERIFIED].",
    ),
    "non_serious_offence": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="BNSS §[UNVERIFIED — verify section number before asserting]",
        notes="Non-serious offences per BNSS. Category boundary [UNVERIFIED].",
    ),
    # Offence categories used in synthetic data
    "theft": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="BNSS §[UNVERIFIED]",
        notes="Theft [UNVERIFIED].",
    ),
    "burglary": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="BNSS §[UNVERIFIED]",
        notes="Burglary [UNVERIFIED].",
    ),
    "robbery": ClockRule(
        clock_type=ClockType.INVESTIGATION_90_DAY,
        duration_days=90,
        bnss_reference="BNSS §[UNVERIFIED]",
        notes="Robbery [UNVERIFIED].",
    ),
    "vehicle_theft": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="BNSS §[UNVERIFIED]",
        notes="Vehicle theft [UNVERIFIED].",
    ),
    "assault": ClockRule(
        clock_type=ClockType.INVESTIGATION_90_DAY,
        duration_days=90,
        bnss_reference="BNSS §[UNVERIFIED]",
        notes="Assault [UNVERIFIED].",
    ),
    "public_order": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="BNSS §[UNVERIFIED]",
        notes="Public order offence [UNVERIFIED].",
    ),
    "fraud": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="BNSS §[UNVERIFIED]",
        notes="Fraud [UNVERIFIED].",
    ),
    "forgery": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="BNSS §[UNVERIFIED]",
        notes="Forgery [UNVERIFIED].",
    ),
    "harassment": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="BNSS §[UNVERIFIED]",
        notes="Harassment [UNVERIFIED].",
    ),
    "narcotics": ClockRule(
        clock_type=ClockType.INVESTIGATION_90_DAY,
        duration_days=90,
        bnss_reference="BNSS §[UNVERIFIED]",
        notes="Narcotics offence [UNVERIFIED].",
    ),
    # Post-filing clock rules (for document supply & further investigation stage lookup)
    "document_supply": ClockRule(
        clock_type=ClockType.DOCUMENT_SUPPLY,
        duration_days=30,
        bnss_reference="BNSS §[UNVERIFIED]",
        notes="Document supply to accused [UNVERIFIED].",
    ),
    "further_investigation": ClockRule(
        clock_type=ClockType.FURTHER_INVESTIGATION,
        duration_days=30,
        bnss_reference="BNSS §[UNVERIFIED]",
        notes="Further investigation [UNVERIFIED].",
    ),
}


def get_clock_rule(offence_category: str) -> ClockRule:
    """
    Look up the clock rule for an offence category.

    Raises KeyError if the offence_category is not in the mapping table.
    Callers MUST handle this — never silently assume a default clock type.
    Per EXECUTION_RULES.md: "every deterministic component needs unit tests
    with the offence category not in mapping table edge case."
    """
    if offence_category not in CLOCK_RULES:
        raise KeyError(
            f"No clock rule found for offence category '{offence_category}'. "
            f"Known categories: {list(CLOCK_RULES.keys())}. "
            f"Add a verified entry to shared/constants/clock_types.py before proceeding."
        )
    return CLOCK_RULES[offence_category]
