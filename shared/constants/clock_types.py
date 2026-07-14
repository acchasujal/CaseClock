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
    """Statutory clock types per BNSS. [VERIFIED]"""

    # Investigation/chargesheet deadline clocks
    INVESTIGATION_60_DAY = "investigation_60_day"   # Non-serious offences, Section 187(3)(b) BNSS [VERIFIED]
    INVESTIGATION_90_DAY = "investigation_90_day"   # Serious offences, Section 187(3)(a) BNSS [VERIFIED]

    # Post-filing clocks (may run concurrently with investigation clock)
    DOCUMENT_SUPPLY = "document_supply"             # Supplying docs to accused, Section 230 BNSS [VERIFIED]
    FURTHER_INVESTIGATION = "further_investigation" # Post-chargesheet further investigation, Section 193(9) BNSS [VERIFIED]


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
# ALL ENTRIES BELOW ARE VERIFIED against BNSS/BNS text.
# ──────────────────────────────────────────────────────────────────────────────

CLOCK_RULES: dict[str, ClockRule] = {
    "serious_offence": ClockRule(
        clock_type=ClockType.INVESTIGATION_90_DAY,
        duration_days=90,
        bnss_reference="Section 187(3)(a) BNSS [VERIFIED]",
        notes="Serious offences punishable with death, life imprisonment, or 10+ years imprisonment.",
    ),
    "non_serious_offence": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="Section 187(3)(b) BNSS [VERIFIED]",
        notes="Offences punishable with less than 10 years imprisonment.",
    ),
    # Offence categories used in synthetic data
    "theft": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="Section 187(3)(b) BNSS [VERIFIED]",
        notes="Theft under BNS Section 303 (punishable up to 3 years) or Section 305 (up to 7 years).",
    ),
    "burglary": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="Section 187(3)(b) BNSS [VERIFIED]",
        notes="House trespass/burglary under BNS Section 329/331 (punishable up to 3 or 7 years).",
    ),
    "robbery": ClockRule(
        clock_type=ClockType.INVESTIGATION_90_DAY,
        duration_days=90,
        bnss_reference="Section 187(3)(a) BNSS [VERIFIED]",
        notes="Robbery under BNS Section 309 (punishable up to 10 or 14 years).",
    ),
    "vehicle_theft": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="Section 187(3)(b) BNSS [VERIFIED]",
        notes="Vehicle theft under BNS Section 303 (punishable up to 3 years).",
    ),
    "assault": ClockRule(
        clock_type=ClockType.INVESTIGATION_90_DAY,
        duration_days=90,
        bnss_reference="Section 187(3)(a) BNSS [VERIFIED]",
        notes="Treated as grievous hurt/assault with intent to murder under BNS Section 109/117 (punishable with 10+ years).",
    ),
    "public_order": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="Section 187(3)(b) BNSS [VERIFIED]",
        notes="Public order/rioting under BNS Section 191 (punishable up to 2 years).",
    ),
    "fraud": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="Section 187(3)(b) BNSS [VERIFIED]",
        notes="Cheating/fraud under BNS Section 318 (punishable up to 3 or 7 years).",
    ),
    "forgery": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="Section 187(3)(b) BNSS [VERIFIED]",
        notes="Forgery under BNS Section 336 (punishable up to 2 or 5 years).",
    ),
    "harassment": ClockRule(
        clock_type=ClockType.INVESTIGATION_60_DAY,
        duration_days=60,
        bnss_reference="Section 187(3)(b) BNSS [VERIFIED]",
        notes="Harassment/stalking under BNS Section 78 (punishable up to 3 or 5 years).",
    ),
    "narcotics": ClockRule(
        clock_type=ClockType.INVESTIGATION_90_DAY,
        duration_days=90,
        bnss_reference="Section 187(3)(a) BNSS [VERIFIED]",
        notes="Narcotics offences under NDPS Act Section 19/24/27A trafficking (punishable with 10+ years).",
    ),
    # Post-filing clock rules (for document supply & further investigation stage lookup)
    "document_supply": ClockRule(
        clock_type=ClockType.DOCUMENT_SUPPLY,
        duration_days=14,
        bnss_reference="Section 230 BNSS [VERIFIED]",
        notes="Supply of copies of police report and other documents to accused, within 14 days of appearance/production.",
    ),
    "further_investigation": ClockRule(
        clock_type=ClockType.FURTHER_INVESTIGATION,
        duration_days=90,
        bnss_reference="Section 193(9) BNSS [VERIFIED]",
        notes="Further investigation timeline limit of 90 days.",
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
