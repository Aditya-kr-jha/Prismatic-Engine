"""
Weekly Schedule Template for Prismatic Engine.

Defines the "perfect week" structure — 21 slots mapped to days, times, pillars, and formats.
This is the STATIC part. The schedule generator HYDRATES it with real dates.

Distribution Strategy:
- 3 posts per day (morning / midday / evening)
- Each pillar appears 2-3 times per week
- Formats distributed: ~7 Quotes, ~7 Carousels, ~7 Reels
- High-engagement slots (Tue/Thu evening) get viral-friendly pillars

Timing Strategy (IST assumed):
- 08:00 → Morning commute / coffee scroll
- 12:00 → Lunch break engagement
- 18:00 → Evening wind-down (highest engagement)
"""

from typing import Dict, List

from pydantic import BaseModel, ConfigDict

from app.db.enums import ContentPillar, Format


# ════════════════════════════════════════════════════════════════════════════════
# SLOT TEMPLATE MODEL
# ════════════════════════════════════════════════════════════════════════════════


class SlotTemplate(BaseModel):
    """Immutable definition of a single posting slot."""

    model_config = ConfigDict(frozen=True)

    slot_number: int  # 1-21
    day_of_week: str  # "monday", "tuesday", etc.
    time: str  # "08:00", "12:00", "18:00"
    pillar: ContentPillar
    format: Format
    priority: int = 2  # 1 = high, 2 = normal, 3 = experimental
    notes: str = ""  # Internal notes for this slot


# ════════════════════════════════════════════════════════════════════════════════
# DAY OFFSET MAPPING (for date calculation)
# ════════════════════════════════════════════════════════════════════════════════

DAY_OFFSETS: Dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


# ════════════════════════════════════════════════════════════════════════════════
# THE MASTER TEMPLATE: 21 Slots Per Week
# ════════════════════════════════════════════════════════════════════════════════

WEEKLY_SLOTS_TEMPLATE: tuple[SlotTemplate, ...] = (
    # ═══════════════════════════════════════════════════════════════════════════
    # MONDAY — Week opener, Productivity focus
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=1,
        day_of_week="monday",
        time="08:00",
        pillar=ContentPillar.PRODUCTIVITY,
        format=Format.QUOTE,
        priority=1,
        notes="Monday motivation. Quick, punchy quote to start the week.",
    ),
    SlotTemplate(
        slot_number=2,
        day_of_week="monday",
        time="12:00",
        pillar=ContentPillar.NEUROSCIENCE,
        format=Format.CAROUSEL,
        priority=2,
        notes="Educational lunch content. Science-backed insights.",
    ),
    SlotTemplate(
        slot_number=3,
        day_of_week="monday",
        time="18:00",
        pillar=ContentPillar.SELF_WORTH,
        format=Format.REEL,
        priority=1,
        notes="Evening emotional hook. High engagement window.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # TUESDAY — Relationships & Dark Psychology (high engagement day)
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=4,
        day_of_week="tuesday",
        time="08:00",
        pillar=ContentPillar.RELATIONSHIPS,
        format=Format.QUOTE,
        priority=2,
        notes="Relatable relationship truth.",
    ),
    SlotTemplate(
        slot_number=5,
        day_of_week="tuesday",
        time="12:00",
        pillar=ContentPillar.DARK_PSYCHOLOGY,
        format=Format.CAROUSEL,
        priority=1,
        notes="Dark psychology deep-dive. High save rate expected.",
    ),
    SlotTemplate(
        slot_number=6,
        day_of_week="tuesday",
        time="18:00",
        pillar=ContentPillar.HEALING_GROWTH,
        format=Format.REEL,
        priority=1,
        notes="Tuesday evening — emotional content performs well.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # WEDNESDAY — Mid-week balance, Philosophy & Self-Care
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=7,
        day_of_week="wednesday",
        time="08:00",
        pillar=ContentPillar.PHILOSOPHY,
        format=Format.QUOTE,
        priority=2,
        notes="Philosophical reflection to break the week.",
    ),
    SlotTemplate(
        slot_number=8,
        day_of_week="wednesday",
        time="12:00",
        pillar=ContentPillar.PRODUCTIVITY,
        format=Format.CAROUSEL,
        priority=2,
        notes="Actionable productivity framework.",
    ),
    SlotTemplate(
        slot_number=9,
        day_of_week="wednesday",
        time="18:00",
        pillar=ContentPillar.SELF_CARE,
        format=Format.REEL,
        priority=2,
        notes="Mid-week self-care reminder.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # THURSDAY — Peak engagement day, Dark Psychology & Neuroscience
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=10,
        day_of_week="thursday",
        time="08:00",
        pillar=ContentPillar.NEUROSCIENCE,
        format=Format.QUOTE,
        priority=2,
        notes="Brain fact to start the day.",
    ),
    SlotTemplate(
        slot_number=11,
        day_of_week="thursday",
        time="12:00",
        pillar=ContentPillar.RELATIONSHIPS,
        format=Format.CAROUSEL,
        priority=1,
        notes="Relationship dynamics breakdown.",
    ),
    SlotTemplate(
        slot_number=12,
        day_of_week="thursday",
        time="18:00",
        pillar=ContentPillar.DARK_PSYCHOLOGY,
        format=Format.REEL,
        priority=1,
        notes="Thursday evening viral slot. Dark psychology reel.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # FRIDAY — Lighter tone, Self-Worth & Healing
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=13,
        day_of_week="friday",
        time="08:00",
        pillar=ContentPillar.SELF_WORTH,
        format=Format.QUOTE,
        priority=2,
        notes="Friday confidence boost.",
    ),
    SlotTemplate(
        slot_number=14,
        day_of_week="friday",
        time="12:00",
        pillar=ContentPillar.HEALING_GROWTH,
        format=Format.CAROUSEL,
        priority=2,
        notes="Growth mindset content for weekend reflection.",
    ),
    SlotTemplate(
        slot_number=15,
        day_of_week="friday",
        time="18:00",
        pillar=ContentPillar.PHILOSOPHY,
        format=Format.REEL,
        priority=2,
        notes="Philosophical reel to end the work week.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # SATURDAY — Weekend mode, Self-Care & Relationships
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=16,
        day_of_week="saturday",
        time="09:00",  # Slightly later on weekends
        pillar=ContentPillar.SELF_CARE,
        format=Format.QUOTE,
        priority=2,
        notes="Weekend self-care affirmation.",
    ),
    SlotTemplate(
        slot_number=17,
        day_of_week="saturday",
        time="13:00",
        pillar=ContentPillar.NEUROSCIENCE,
        format=Format.REEL,
        priority=2,
        notes="Science reel for weekend scrollers.",
    ),
    SlotTemplate(
        slot_number=18,
        day_of_week="saturday",
        time="19:00",
        pillar=ContentPillar.RELATIONSHIPS,
        format=Format.CAROUSEL,
        priority=2,
        notes="Saturday evening relationship content.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # SUNDAY — Reflection day, Philosophy & Healing
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=19,
        day_of_week="sunday",
        time="09:00",
        pillar=ContentPillar.HEALING_GROWTH,
        format=Format.QUOTE,
        priority=2,
        notes="Sunday healing affirmation.",
    ),
    SlotTemplate(
        slot_number=20,
        day_of_week="sunday",
        time="13:00",
        pillar=ContentPillar.SELF_WORTH,
        format=Format.CAROUSEL,
        priority=2,
        notes="Self-worth deep-dive for Sunday reflection.",
    ),
    SlotTemplate(
        slot_number=21,
        day_of_week="sunday",
        time="19:00",
        pillar=ContentPillar.PRODUCTIVITY,
        format=Format.REEL,
        priority=1,
        notes="Sunday evening prep-for-Monday reel. High intent audience.",
    ),
)


# ════════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════════


def get_slot_by_number(slot_number: int) -> SlotTemplate:
    """Get a specific slot template by its number (1-21)."""
    for slot in WEEKLY_SLOTS_TEMPLATE:
        if slot.slot_number == slot_number:
            return slot
    raise ValueError(f"Invalid slot number: {slot_number}. Must be 1-21.")


def get_slots_by_day(day_of_week: str) -> List[SlotTemplate]:
    """Get all slots for a specific day."""
    day_lower = day_of_week.lower()
    return [slot for slot in WEEKLY_SLOTS_TEMPLATE if slot.day_of_week == day_lower]


def get_slots_by_pillar(pillar: ContentPillar) -> List[SlotTemplate]:
    """Get all slots assigned to a specific pillar."""
    return [slot for slot in WEEKLY_SLOTS_TEMPLATE if slot.pillar == pillar]


def get_slots_by_format(fmt: Format) -> List[SlotTemplate]:
    """Get all slots assigned to a specific format."""
    return [slot for slot in WEEKLY_SLOTS_TEMPLATE if slot.format == fmt]


def get_high_priority_slots() -> List[SlotTemplate]:
    """Get slots marked as high priority (priority=1)."""
    return [slot for slot in WEEKLY_SLOTS_TEMPLATE if slot.priority == 1]


# ════════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ════════════════════════════════════════════════════════════════════════════════


class ValidationResult(BaseModel):
    """Result of template validation."""

    total_slots: int
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    distribution: Dict[str, Dict[str, int]]


def validate_template() -> ValidationResult:
    """
    Validate the template for consistency.

    Checks:
    - Exactly 21 slots
    - No duplicate slot numbers
    - Slot numbers are 1-21
    - Distribution analysis
    """
    errors: List[str] = []
    warnings: List[str] = []
    distribution: Dict[str, Dict[str, int]] = {
        "by_pillar": {},
        "by_format": {},
        "by_day": {},
    }

    # Check slot count
    if len(WEEKLY_SLOTS_TEMPLATE) != 21:
        errors.append(f"Expected 21 slots, found {len(WEEKLY_SLOTS_TEMPLATE)}")

    # Check for duplicate slot numbers
    slot_numbers = [s.slot_number for s in WEEKLY_SLOTS_TEMPLATE]
    if len(slot_numbers) != len(set(slot_numbers)):
        errors.append("Duplicate slot numbers found")

    # Check slot numbers are 1-21
    expected_slots = set(range(1, 22))
    actual_slots = set(slot_numbers)
    if expected_slots != actual_slots:
        missing = expected_slots - actual_slots
        extra = actual_slots - expected_slots
        if missing:
            errors.append(f"Missing slot numbers: {missing}")
        if extra:
            errors.append(f"Invalid slot numbers: {extra}")

    # Distribution analysis
    for slot in WEEKLY_SLOTS_TEMPLATE:
        # By pillar
        pillar_name = slot.pillar.value
        distribution["by_pillar"][pillar_name] = (
            distribution["by_pillar"].get(pillar_name, 0) + 1
        )

        # By format
        format_name = slot.format.value
        distribution["by_format"][format_name] = (
            distribution["by_format"].get(format_name, 0) + 1
        )

        # By day
        distribution["by_day"][slot.day_of_week] = (
            distribution["by_day"].get(slot.day_of_week, 0) + 1
        )

    # Warn if distribution is uneven
    format_counts = list(distribution["by_format"].values())
    if format_counts and max(format_counts) - min(format_counts) > 2:
        warnings.append("Format distribution is uneven")

    return ValidationResult(
        total_slots=len(WEEKLY_SLOTS_TEMPLATE),
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        distribution=distribution,
    )


if __name__ == "__main__":
    # Quick validation when run directly
    import json

    result = validate_template()
    print(json.dumps(result.model_dump(), indent=2))
