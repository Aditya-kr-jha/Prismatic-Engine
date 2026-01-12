"""
Format × Pillar Mode Resolution Matrix.

Hardcoded logic for resolving generation modes based on content format and pillar.
Each combination returns a (mode, structural_note) tuple.
"""

from typing import Dict, Tuple

# ============================================================================
# MODE MATRIX
# ============================================================================
#
# Maps (FORMAT, PILLAR) -> (resolved_mode, structural_note)
#
# Modes:
# - ROAST_MASTER: Direct call-out, behavior naming
# - MIRROR: Recognition without advice, "being seen" energy
# - ORACLE: Mechanism reveal, prophecy-like truth
# - SURGEON: Tactical precision, no emotional fluff
# - ROAST_TO_SURGEON: Roast opener, Surgeon breakdown
# - ROAST_TO_MIRROR: Expose false beliefs → recognize truth
# - ORACLE_SURGEON: Mechanism + structure hybrid
# - ORACLE_COMPRESSED: One-line mechanism
# ============================================================================

MODE_MATRIX: Dict[Tuple[str, str], Tuple[str, str]] = {
    # ══════════════════════════════════════════════════════════════════════
    # REELS
    # ══════════════════════════════════════════════════════════════════════
    ("REEL", "RELATIONSHIPS"): (
        "ROAST_MASTER",
        "Direct call-out, behavior naming",
    ),
    ("REEL", "DARK_PSYCHOLOGY"): (
        "ROAST_MASTER",
        "Oracle insight delivered as exposure",
    ),
    ("REEL", "PRODUCTIVITY"): (
        "ROAST_MASTER",
        "Naming avoidance and cope",
    ),
    ("REEL", "NEUROSCIENCE"): (
        "MIRROR",
        "Recognition of internal experience",
    ),
    ("REEL", "PHILOSOPHY"): (
        "MIRROR",
        "Truth as uncomfortable reflection",
    ),
    ("REEL", "HEALING_GROWTH"): (
        "MIRROR",
        "Seen without being fixed",
    ),
    ("REEL", "SELF_CARE"): (
        "MIRROR",
        "Permission without softness",
    ),
    ("REEL", "SELF_WORTH"): (
        "MIRROR",
        "Identity recognition",
    ),
    # ══════════════════════════════════════════════════════════════════════
    # CAROUSELS
    # ══════════════════════════════════════════════════════════════════════
    ("CAROUSEL", "RELATIONSHIPS"): (
        "ROAST_TO_SURGEON",
        "Roast opener, Surgeon breakdown",
    ),
    ("CAROUSEL", "DARK_PSYCHOLOGY"): (
        "ORACLE",
        "Mechanism reveal, slide by slide",
    ),
    ("CAROUSEL", "PRODUCTIVITY"): (
        "ROAST_TO_SURGEON",
        "Call-out opener, tactical body",
    ),
    ("CAROUSEL", "NEUROSCIENCE"): (
        "ORACLE_SURGEON",
        "Mechanism + structure hybrid",
    ),
    ("CAROUSEL", "PHILOSOPHY"): (
        "ORACLE",
        "Revelation sequence",
    ),
    ("CAROUSEL", "HEALING_GROWTH"): (
        "ORACLE",
        "Mechanism of healing, not comfort",
    ),
    ("CAROUSEL", "SELF_CARE"): (
        "SURGEON",
        "Tactical, no fluff",
    ),
    ("CAROUSEL", "SELF_WORTH"): (
        "ROAST_TO_MIRROR",
        "Expose false beliefs → recognize truth",
    ),
    # ══════════════════════════════════════════════════════════════════════
    # QUOTES
    # ══════════════════════════════════════════════════════════════════════
    ("QUOTE", "RELATIONSHIPS"): (
        "ROAST_MASTER",
        "One-line exposure",
    ),
    ("QUOTE", "DARK_PSYCHOLOGY"): (
        "ROAST_MASTER",
        "Oracle truth in Roast voice",
    ),
    ("QUOTE", "PRODUCTIVITY"): (
        "ROAST_MASTER",
        "Naming the avoidance",
    ),
    ("QUOTE", "NEUROSCIENCE"): (
        "ORACLE_COMPRESSED",
        "One-line mechanism",
    ),
    ("QUOTE", "PHILOSOPHY"): (
        "MIRROR",
        "Recognition as wisdom",
    ),
    ("QUOTE", "HEALING_GROWTH"): (
        "MIRROR",
        "Seen, not advised",
    ),
    ("QUOTE", "SELF_CARE"): (
        "MIRROR",
        "Permission statement",
    ),
    ("QUOTE", "SELF_WORTH"): (
        "MIRROR",
        "Identity affirmation, sharp not soft",
    ),
}

# Default fallback for unknown combinations
DEFAULT_MODE = ("MIRROR", "Recognition and truth-telling")


def resolve_mode(format_type: str, pillar: str) -> Tuple[str, str]:
    """
    Resolve the generation mode from Format × Pillar matrix.

    Args:
        format_type: REEL, CAROUSEL, or QUOTE
        pillar: Content pillar (e.g., RELATIONSHIPS, PRODUCTIVITY)

    Returns:
        Tuple of (resolved_mode, structural_note)
    """
    key = (format_type.upper(), pillar.upper())
    return MODE_MATRIX.get(key, DEFAULT_MODE)
