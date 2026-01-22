"""
Weekly Schedule Template for Prismatic Engine (COST-OPTIMIZED v5 — RELATIONSHIP FOCUSED).

Target: 14 slots/week (down from 21) = ~33% LLM cost reduction
Distribution: 0 Quotes / 8 Carousels / 6 Reels

RELATIONSHIP CONTENT:  4 slots (2 Reels + 2 Carousels) — PRIMARY GROWTH PILLAR

Removed for cost optimization (rotate back in 2-3 weeks):
- All Quotes (low atom utilization)
- Philosophy (lower engagement)
- Self-Care (can merge with Healing)
"""

from typing import Dict, List, Any

from pydantic import BaseModel, ConfigDict

from app.db.enums import ContentPillar, Format


class SlotTemplate(BaseModel):
    """Immutable definition of a single posting slot."""

    model_config = ConfigDict(frozen=True)

    slot_number: int  # 1-14
    day_of_week: str
    time: str
    pillar: ContentPillar
    format: Format
    priority: int = 2
    notes: str = ""


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
# THE MASTER TEMPLATE: 14 Slots Per Week (RELATIONSHIP-FOCUSED v5)
# ════════════════════════════════════════════════════════════════════════════════

WEEKLY_SLOTS_TEMPLATE: tuple[SlotTemplate, ...] = (
    # ═══════════════════════════════════════════════════════════════════════════
    # MONDAY — Week opener (2 slots)
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=1,
        day_of_week="monday",
        time="08:00",
        pillar=ContentPillar.PRODUCTIVITY,
        format=Format.CAROUSEL,
        priority=1,
        notes="Week opener.  Tactical productivity framework. High save.",
    ),
    SlotTemplate(
        slot_number=2,
        day_of_week="monday",
        time="18:00",
        pillar=ContentPillar.SELF_WORTH,
        format=Format.REEL,
        priority=1,
        notes="Evening identity content. High emotional engagement + shares.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # TUESDAY — Relationships + Dark Psychology (2 slots)
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=3,
        day_of_week="tuesday",
        time="12:00",
        pillar=ContentPillar.DARK_PSYCHOLOGY,
        format=Format.CAROUSEL,
        priority=1,
        notes="Dark psychology deep-dive. Highest save rate pillar.",
    ),
    SlotTemplate(
        slot_number=4,
        day_of_week="tuesday",
        time="18:00",
        pillar=ContentPillar.RELATIONSHIPS,  # ← RELATIONSHIP REEL #1
        format=Format.REEL,
        priority=1,
        notes="🔥 RELATIONSHIP REEL #1. Tuesday evening emotional scroll.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # WEDNESDAY — Mid-week Reset (2 slots)
    # ══════════════════════════════════════════════════════════��════════════════
    SlotTemplate(
        slot_number=5,
        day_of_week="wednesday",
        time="08:00",
        pillar=ContentPillar.DARK_PSYCHOLOGY,
        format=Format.REEL,
        priority=1,
        notes="Morning pattern interrupt. Wake them up with edge.",
    ),
    SlotTemplate(
        slot_number=6,
        day_of_week="wednesday",
        time="18:00",
        pillar=ContentPillar.RELATIONSHIPS,  # ← RELATIONSHIP CAROUSEL #1
        format=Format.CAROUSEL,
        priority=1,
        notes="📚 RELATIONSHIP CAROUSEL #1. Mid-week relationship deep-dive.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # THURSDAY — Peak Engagement Day (2 slots)
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=7,
        day_of_week="thursday",
        time="12:00",
        pillar=ContentPillar.NEUROSCIENCE,
        format=Format.CAROUSEL,
        priority=1,
        notes="Neuroscience deep-dive. Thursday lunch = peak attention.",
    ),
    SlotTemplate(
        slot_number=8,
        day_of_week="thursday",
        time="18:00",
        pillar=ContentPillar.RELATIONSHIPS,  # ← RELATIONSHIP REEL #2
        format=Format.REEL,
        priority=1,
        notes="🔥 RELATIONSHIP REEL #2. Thursday evening = viral potential.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # FRIDAY — Reflection + Growth (2 slots)
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=9,
        day_of_week="friday",
        time="12:00",
        pillar=ContentPillar.HEALING_GROWTH,
        format=Format.CAROUSEL,
        priority=2,
        notes="End-of-week healing reflection. High save + emotional resonance.",
    ),
    SlotTemplate(
        slot_number=10,
        day_of_week="friday",
        time="18:00",
        pillar=ContentPillar.SELF_WORTH,
        format=Format.CAROUSEL,
        priority=1,
        notes="Friday evening identity validation. High save + share.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # SATURDAY — Weekend Scroll (2 slots)
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=11,
        day_of_week="saturday",
        time="14:00",
        pillar=ContentPillar.DARK_PSYCHOLOGY,
        format=Format.REEL,
        priority=1,
        notes="Dark psychology reel. Weekend 'guilty pleasure' content.",
    ),
    SlotTemplate(
        slot_number=12,
        day_of_week="saturday",
        time="20:00",
        pillar=ContentPillar.NEUROSCIENCE,
        format=Format.REEL,
        priority=2,
        notes="Saturday night neuroscience. 'Mind-blown' share content.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # SUNDAY — Relationship Deep-Dive + Prep (2 slots)
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=13,
        day_of_week="sunday",
        time="14:00",
        pillar=ContentPillar.RELATIONSHIPS,  # ← RELATIONSHIP CAROUSEL #2
        format=Format.CAROUSEL,
        priority=1,
        notes="📚 RELATIONSHIP CAROUSEL #2. Sunday relationship reflection = high saves.",
    ),
    SlotTemplate(
        slot_number=14,
        day_of_week="sunday",
        time="19:00",
        pillar=ContentPillar.PRODUCTIVITY,
        format=Format.REEL,
        priority=1,
        notes="Sunday prep reel. 'Tomorrow you will.. .' momentum.",
    ),
)


# ════════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS (Updated for 14 slots)
# ════════════════════════════════════════════════════════════════════════════════


def get_slot_by_number(slot_number: int) -> SlotTemplate:
    """Get a specific slot template by its number (1-14)."""
    for slot in WEEKLY_SLOTS_TEMPLATE:
        if slot.slot_number == slot_number:
            return slot
    raise ValueError(f"Invalid slot number: {slot_number}. Must be 1-14.")


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


def get_relationship_content() -> Dict[str, List[SlotTemplate]]:
    """Get all Relationship content slots grouped by format."""
    relationship_slots = get_slots_by_pillar(ContentPillar.RELATIONSHIPS)
    return {
        "reels": [s for s in relationship_slots if s.format == Format.REEL],
        "carousels": [s for s in relationship_slots if s.format == Format.CAROUSEL],
    }


def get_content_atom_utilization() -> Dict[str, Any]:
    """Calculate content atom utilization efficiency by format."""
    format_counts = {}
    for slot in WEEKLY_SLOTS_TEMPLATE:
        fmt = slot.format.value
        format_counts[fmt] = format_counts.get(fmt, 0) + 1

    utilization_rates = {
        "quote": 0.02,
        "carousel": 0.85,
        "reel": 0.70,
    }

    total_atoms = len(WEEKLY_SLOTS_TEMPLATE)
    weighted_utilization = (
        sum(format_counts.get(fmt, 0) * rate for fmt, rate in utilization_rates.items())
        / total_atoms
    )

    return {
        "by_format": {fmt: format_counts.get(fmt, 0) for fmt in utilization_rates},
        "average_utilization": round(weighted_utilization * 100, 1),
    }


# ══════════��═════════════════════════════════════════════════════════════════════
# VALIDATION (Updated for 14 slots — Relationship Focused)
# ════════════════════════════════════════════════════════════════════════════════


class ValidationResult(BaseModel):
    """Result of template validation."""

    total_slots: int
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    distribution: Dict[str, Dict[str, int]]
    atom_utilization: Dict[str, Any]
    cost_savings_estimate: str
    relationship_focus: Dict[str, int]


def validate_template() -> ValidationResult:
    """
    Validate the 14-slot template for consistency.

    Requirements for relationship-focused version:
    - Exactly 14 slots
    - Relationship content:  >= 2 Reels, >= 2 Carousels (4 total)
    - No quotes (100% atom utilization)
    """
    errors: List[str] = []
    warnings: List[str] = []
    distribution: Dict[str, Dict[str, int]] = {
        "by_pillar": {},
        "by_format": {},
        "by_day": {},
        "by_pillar_format": {},
    }

    # Check slot count
    if len(WEEKLY_SLOTS_TEMPLATE) != 14:
        errors.append(f"Expected 14 slots, found {len(WEEKLY_SLOTS_TEMPLATE)}")

    # Check for duplicate slot numbers
    slot_numbers = [s.slot_number for s in WEEKLY_SLOTS_TEMPLATE]
    if len(slot_numbers) != len(set(slot_numbers)):
        errors.append("Duplicate slot numbers found")

    # Check slot numbers are 1-14
    expected_slots = set(range(1, 15))
    actual_slots = set(slot_numbers)
    if expected_slots != actual_slots:
        missing = expected_slots - actual_slots
        extra = actual_slots - expected_slots
        if missing:
            errors.append(f"Missing slot numbers: {missing}")
        if extra:
            errors.append(f"Invalid slot numbers: {extra}")

    # Distribution analysis
    relationship_reel_count = 0
    relationship_carousel_count = 0
    quote_count = 0

    for slot in WEEKLY_SLOTS_TEMPLATE:
        pillar_name = slot.pillar.value
        distribution["by_pillar"][pillar_name] = (
            distribution["by_pillar"].get(pillar_name, 0) + 1
        )

        format_name = slot.format.value
        distribution["by_format"][format_name] = (
            distribution["by_format"].get(format_name, 0) + 1
        )

        distribution["by_day"][slot.day_of_week] = (
            distribution["by_day"].get(slot.day_of_week, 0) + 1
        )

        combo_key = f"{pillar_name}_{format_name}"
        distribution["by_pillar_format"][combo_key] = (
            distribution["by_pillar_format"].get(combo_key, 0) + 1
        )

        if slot.format == Format.QUOTE:
            quote_count += 1
        if slot.pillar == ContentPillar.RELATIONSHIPS:
            if slot.format == Format.REEL:
                relationship_reel_count += 1
            elif slot.format == Format.CAROUSEL:
                relationship_carousel_count += 1

    # Validate relationship content (STRICT for relationship-focused version)
    if relationship_reel_count < 2:
        errors.append(
            f"Required at least 2 Relationship Reels, found {relationship_reel_count}"
        )
    if relationship_carousel_count < 2:
        errors.append(
            f"Required at least 2 Relationship Carousels, found {relationship_carousel_count}"
        )

    # Warn if quotes exist (should be 0 in cost-optimized version)
    if quote_count > 0:
        warnings.append(
            f"Quote count ({quote_count}) > 0. Cost-optimized version should have no quotes."
        )

    atom_utilization = get_content_atom_utilization()

    # Estimate cost savings
    cost_savings = f"~{round((1 - 14/21) * 100)}% reduction (14 vs 21 slots)"

    # Relationship focus summary
    relationship_focus = {
        "total_slots": relationship_reel_count + relationship_carousel_count,
        "reels": relationship_reel_count,
        "carousels": relationship_carousel_count,
        "percentage_of_schedule": round(
            (relationship_reel_count + relationship_carousel_count) / 14 * 100, 1
        ),
    }

    return ValidationResult(
        total_slots=len(WEEKLY_SLOTS_TEMPLATE),
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        distribution=distribution,
        atom_utilization=atom_utilization,
        cost_savings_estimate=cost_savings,
        relationship_focus=relationship_focus,
    )


if __name__ == "__main__":
    import json

    result = validate_template()
    print(json.dumps(result.model_dump(), indent=2))

    print("\n💕 RELATIONSHIP CONTENT (Primary Growth Pillar):")
    rel_content = get_relationship_content()
    for fmt, slots in rel_content.items():
        print(f"  {fmt.upper()}: {len(slots)}")
        for slot in slots:
            print(
                f"    - Slot {slot.slot_number}:  {slot.day_of_week. capitalize()} {slot.time}"
            )

    print(
        f"\n📊 Relationship Focus:  {result.relationship_focus['percentage_of_schedule']}% of schedule"
    )

    print("\n⚡ Content Atom Utilization:")
    util = get_content_atom_utilization()
    print(f"  Average: {util['average_utilization']}%")
    print(f"  By format: {util['by_format']}")

    print(f"\n💰 Cost Savings: {result. cost_savings_estimate}")
