"""
Weekly Schedule Template for Prismatic Engine (OPTIMIZED v4).

Key insight: Quotes waste content atoms. A 700-word atom reduced to 15 words = 98% waste.

Distribution: 2 Quotes / 10 Carousels / 9 Reels
- Quotes ONLY for: Monday AM opener, Saturday AM softness
- Everything else maximizes atom utilization

Relationship content: 3 Reels + 2 Carousels = 5 slots
"""

from typing import Dict, List, Any

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
# THE MASTER TEMPLATE: 21 Slots Per Week (OPTIMIZED v4 — MINIMAL QUOTES)
# ════════════════════════════════════════════════════════════════════════════════

WEEKLY_SLOTS_TEMPLATE: tuple[SlotTemplate, ...] = (
    # ═══════════════════════════════════════════════════════════════════════════
    # MONDAY — Week opener
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=1,
        day_of_week="monday",
        time="08:00",
        pillar=ContentPillar.PRODUCTIVITY,
        format=Format.QUOTE,  # ← QUOTE #1: Week opener, quick hit
        priority=1,
        notes="✨ QUOTE #1. Monday motivation. Only quote justified—quick dopamine.",
    ),
    SlotTemplate(
        slot_number=2,
        day_of_week="monday",
        time="12:00",
        pillar=ContentPillar.NEUROSCIENCE,
        format=Format.CAROUSEL,
        priority=2,
        notes="Science deep-dive. Lunch break learning.",
    ),
    SlotTemplate(
        slot_number=3,
        day_of_week="monday",
        time="18:00",
        pillar=ContentPillar.SELF_WORTH,
        format=Format.REEL,
        priority=1,
        notes="Evening identity content. High emotional engagement.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # TUESDAY — Relationships + Dark Psychology
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=4,
        day_of_week="tuesday",
        time="08:00",
        pillar=ContentPillar.HEALING_GROWTH,
        format=Format.CAROUSEL,  # ← Upgraded from Quote
        priority=2,
        notes="Morning healing carousel. Full depth, high save.",
    ),
    SlotTemplate(
        slot_number=5,
        day_of_week="tuesday",
        time="12:00",
        pillar=ContentPillar.DARK_PSYCHOLOGY,
        format=Format.CAROUSEL,
        priority=1,
        notes="Dark psychology deep-dive. High save rate.",
    ),
    SlotTemplate(
        slot_number=6,
        day_of_week="tuesday",
        time="18:00",
        pillar=ContentPillar.RELATIONSHIPS,  # ← RELATIONSHIP REEL #1
        format=Format.REEL,
        priority=1,
        notes="🔥 RELATIONSHIP REEL #1. Evening emotional scroll.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # WEDNESDAY — Mid-week Reset
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=7,
        day_of_week="wednesday",
        time="08:00",
        pillar=ContentPillar.DARK_PSYCHOLOGY,
        format=Format.REEL,  # ← Changed: Morning reel for pattern interrupt
        priority=2,
        notes="Morning dark psychology reel. Wake them up.",
    ),
    SlotTemplate(
        slot_number=8,
        day_of_week="wednesday",
        time="12:00",
        pillar=ContentPillar.PRODUCTIVITY,
        format=Format.CAROUSEL,
        priority=2,
        notes="Tactical productivity frameworks.",
    ),
    SlotTemplate(
        slot_number=9,
        day_of_week="wednesday",
        time="18:00",
        pillar=ContentPillar.SELF_CARE,
        format=Format.CAROUSEL,
        priority=2,
        notes="Mid-week self-care permission. Full depth.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # THURSDAY — RELATIONSHIPS HEAVY (Peak Engagement Day)
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=10,
        day_of_week="thursday",
        time="08:00",
        pillar=ContentPillar.RELATIONSHIPS,  # ← RELATIONSHIP CAROUSEL #1
        format=Format.CAROUSEL,
        priority=1,
        notes="📚 RELATIONSHIP CAROUSEL #1. Morning relationship dynamics.",
    ),
    SlotTemplate(
        slot_number=11,
        day_of_week="thursday",
        time="12:00",
        pillar=ContentPillar.NEUROSCIENCE,
        format=Format.CAROUSEL,
        priority=1,
        notes="Neuroscience deep-dive. Thursday lunch = high attention.",
    ),
    SlotTemplate(
        slot_number=12,
        day_of_week="thursday",
        time="18:00",
        pillar=ContentPillar.RELATIONSHIPS,  # ← RELATIONSHIP REEL #2
        format=Format.REEL,
        priority=1,
        notes="🔥 RELATIONSHIP REEL #2. Thursday evening viral slot.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # FRIDAY — Reflection + Philosophy
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=13,
        day_of_week="friday",
        time="08:00",
        pillar=ContentPillar.SELF_WORTH,
        format=Format.CAROUSEL,  # ← Upgraded from Quote
        priority=2,
        notes="Friday self-worth deep-dive. End-of-week validation.",
    ),
    SlotTemplate(
        slot_number=14,
        day_of_week="friday",
        time="12:00",
        pillar=ContentPillar.HEALING_GROWTH,
        format=Format.CAROUSEL,
        priority=2,
        notes="Growth reflection carousel.",
    ),
    SlotTemplate(
        slot_number=15,
        day_of_week="friday",
        time="18:00",
        pillar=ContentPillar.PHILOSOPHY,
        format=Format.REEL,
        priority=2,
        notes="Philosophical reel. End-of-week existential content.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # SATURDAY — Weekend Mode
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=16,
        day_of_week="saturday",
        time="10:00",
        pillar=ContentPillar.SELF_CARE,
        format=Format.QUOTE,  # ← QUOTE #2: Weekend softness, permission energy
        priority=2,
        notes="✨ QUOTE #2. Weekend self-care. Only other justified quote—gentle AM.",
    ),
    SlotTemplate(
        slot_number=17,
        day_of_week="saturday",
        time="14:00",
        pillar=ContentPillar.DARK_PSYCHOLOGY,
        format=Format.REEL,
        priority=1,
        notes="Dark psychology reel. Weekend 'guilty pleasure' scroll.",
    ),
    SlotTemplate(
        slot_number=18,
        day_of_week="saturday",
        time="20:00",
        pillar=ContentPillar.RELATIONSHIPS,  # ← RELATIONSHIP REEL #3
        format=Format.REEL,
        priority=1,
        notes="🔥 RELATIONSHIP REEL #3. Saturday night emotional content.",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # SUNDAY — Reflection + Prep
    # ═══════════════════════════════════════════════════════════════════════════
    SlotTemplate(
        slot_number=19,
        day_of_week="sunday",
        time="10:00",
        pillar=ContentPillar.PHILOSOPHY,
        format=Format.CAROUSEL,  # ← Added Philosophy carousel
        priority=2,
        notes="Sunday philosophy deep-dive. Reflective scrollers.",
    ),
    SlotTemplate(
        slot_number=20,
        day_of_week="sunday",
        time="14:00",
        pillar=ContentPillar.RELATIONSHIPS,  # ← RELATIONSHIP CAROUSEL #2
        format=Format.CAROUSEL,
        priority=1,
        notes="📚 RELATIONSHIP CAROUSEL #2. Sunday relationship reflection.",
    ),
    SlotTemplate(
        slot_number=21,
        day_of_week="sunday",
        time="19:00",
        pillar=ContentPillar.PRODUCTIVITY,
        format=Format.REEL,
        priority=1,
        notes="Sunday evening prep reel. 'Tomorrow you will...' energy.",
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


def get_relationship_content() -> Dict[str, List[SlotTemplate]]:
    """Get all Relationship content slots grouped by format."""
    relationship_slots = get_slots_by_pillar(ContentPillar.RELATIONSHIPS)
    return {
        "reels": [s for s in relationship_slots if s.format == Format.REEL],
        "carousels": [s for s in relationship_slots if s.format == Format.CAROUSEL],
        "quotes": [s for s in relationship_slots if s.format == Format.QUOTE],
    }


def get_content_atom_utilization() -> Dict[str, float]:
    """Calculate content atom utilization efficiency by format."""
    format_counts = {}
    for slot in WEEKLY_SLOTS_TEMPLATE:
        fmt = slot.format.value
        format_counts[fmt] = format_counts.get(fmt, 0) + 1

    # Utilization estimates (% of 700-word atom used)
    utilization_rates = {
        "quote": 0.02,  # ~15 words / 700 = 2%
        "carousel": 0.85,  # ~600 words across slides = 85%
        "reel": 0.70,  # ~500 words in script = 70%
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
    atom_utilization: Dict[str, Any]  # fix: Any (typing) not any (built-in)


def validate_template() -> ValidationResult:
    """
    Validate the template for consistency.

    Checks:
    - Exactly 21 slots
    - No duplicate slot numbers
    - Slot numbers are 1-21
    - Relationship content requirements (>= 3 Reels, >= 1 Carousel)
    - Quote count <= 3 (minimal quotes policy)
    - Content atom utilization
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
    relationship_reel_count = 0
    relationship_carousel_count = 0
    quote_count = 0

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

        # Cross-reference pillar-format
        combo_key = f"{pillar_name}_{format_name}"
        distribution["by_pillar_format"][combo_key] = (
            distribution["by_pillar_format"].get(combo_key, 0) + 1
        )

        # Count specifics
        if slot.format == Format.QUOTE:
            quote_count += 1
        if slot.pillar == ContentPillar.RELATIONSHIPS:
            if slot.format == Format.REEL:
                relationship_reel_count += 1
            elif slot.format == Format.CAROUSEL:
                relationship_carousel_count += 1

    # Validate relationship content requirements
    if relationship_reel_count < 3:
        errors.append(
            f"Required at least 3 Relationship Reels, found {relationship_reel_count}"
        )
    if relationship_carousel_count < 1:
        errors.append(
            f"Required at least 1 Relationship Carousel, found {relationship_carousel_count}"
        )

    # Validate minimal quotes policy
    if quote_count > 3:
        warnings.append(
            f"Quote count ({quote_count}) exceeds minimal quotes policy (max 3)"
        )

    # Calculate atom utilization
    atom_utilization = get_content_atom_utilization()

    return ValidationResult(
        total_slots=len(WEEKLY_SLOTS_TEMPLATE),
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        distribution=distribution,
        atom_utilization=atom_utilization,
    )


if __name__ == "__main__":
    import json

    result = validate_template()
    print(json.dumps(result.model_dump(), indent=2))

    # Print relationship content breakdown
    print("\n📊 Relationship Content:")
    rel_content = get_relationship_content()
    for fmt, slots in rel_content.items():
        print(f"  {fmt.upper()}: {len(slots)}")
        for slot in slots:
            print(f"    - Slot {slot.slot_number}: {slot.day_of_week} {slot.time}")

    # Print atom utilization
    print("\n⚡ Content Atom Utilization:")
    util = get_content_atom_utilization()
    print(f"  Average: {util['average_utilization']}%")
    print(f"  By format: {util['by_format']}")
