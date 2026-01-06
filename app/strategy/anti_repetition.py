"""
Anti-Repetition Query Helpers for Prismatic Engine Phase 4.

These functions ensure content freshness by excluding recently used atoms and angles.

Rules:
- Same atom (any angle): Cannot reuse within 6 weeks
- Same atom + same angle: Cannot reuse within 12 weeks
- Same pillar saturation: Max 40% of recent posts from one pillar
"""

import logging
import math
import uuid
from datetime import date, datetime, time as dt_time, timedelta, timezone
from typing import List, Optional, Set, Tuple

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from app.db.db_models.classification import ContentAtom
from app.db.db_models.strategy import AngleMatrix
from app.db.enums import ContentPillar, Format
from app.strategy import db_services

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════════


class AntiRepetitionConfig(BaseModel):
    """Configuration for anti-repetition rules."""

    model_config = ConfigDict(frozen=True)

    atom_cooldown_weeks: int = 6  # Same atom, any angle
    atom_angle_cooldown_weeks: int = 12  # Same atom + same angle
    pillar_saturation_limit: float = 0.4  # Max 40% from one pillar in lookback
    lookback_weeks: int = 4  # Weeks to check for saturation
    min_atoms_before_reuse: int = 50  # Minimum unique atoms before allowing reuse


DEFAULT_CONFIG = AntiRepetitionConfig()


# ════════════════════════════════════════════════════════════════════════════════
# CORE ANTI-REPETITION FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════════


def get_excluded_atom_ids(
    session: Session,
    config: AntiRepetitionConfig = DEFAULT_CONFIG,
    as_of_date: Optional[date] = None,
) -> Set[uuid.UUID]:
    """
    Get all atom IDs that should be excluded from selection.

    Uses the atom_cooldown_weeks from config.

    Args:
        session: Database session
        config: Anti-repetition configuration
        as_of_date: Reference date (defaults to today)

    Returns:
        Set of atom UUIDs to exclude
    """
    return db_services.get_recently_used_atom_ids(
        session=session,
        weeks=config.atom_cooldown_weeks,
        as_of_date=as_of_date,
    )


def get_excluded_atom_angle_pairs(
    session: Session,
    config: AntiRepetitionConfig = DEFAULT_CONFIG,
    as_of_date: Optional[date] = None,
) -> Set[Tuple[uuid.UUID, str]]:
    """
    Get all (atom_id, angle_id) pairs that should be excluded.

    Uses the atom_angle_cooldown_weeks from config.

    Args:
        session: Database session
        config: Anti-repetition configuration
        as_of_date: Reference date (defaults to today)

    Returns:
        Set of (atom_id, angle_id) tuples to exclude
    """
    return db_services.get_recently_used_atom_angle_pairs(
        session=session,
        weeks=config.atom_angle_cooldown_weeks,
        as_of_date=as_of_date,
    )


def is_pillar_oversaturated(
    session: Session,
    pillar: ContentPillar,
    config: AntiRepetitionConfig = DEFAULT_CONFIG,
    as_of_date: Optional[date] = None,
) -> bool:
    """
    Check if a pillar has been used too frequently in recent posts.

    Args:
        session: Database session
        pillar: The pillar to check
        config: Anti-repetition configuration
        as_of_date: Reference date (defaults to today)

    Returns:
        True if pillar usage exceeds saturation limit
    """
    usage_counts = db_services.get_pillar_usage_counts(
        session=session,
        weeks=config.lookback_weeks,
        as_of_date=as_of_date,
    )

    total_posts = sum(usage_counts.values())
    if total_posts == 0:
        return False

    pillar_value = pillar.value if hasattr(pillar, "value") else pillar
    pillar_count = usage_counts.get(pillar_value, 0)
    saturation = pillar_count / total_posts

    return saturation > config.pillar_saturation_limit


def is_atom_angle_combination_allowed(
    session: Session,
    atom_id: uuid.UUID,
    angle_id: str,
    config: AntiRepetitionConfig = DEFAULT_CONFIG,
    as_of_date: Optional[date] = None,
) -> bool:
    """
    Check if a specific atom + angle combination can be used.

    Args:
        session: Database session
        atom_id: The atom UUID
        angle_id: The angle ID
        config: Anti-repetition configuration
        as_of_date: Reference date (defaults to today)

    Returns:
        True if combination is allowed, False if recently used
    """
    recently_used_pairs = get_excluded_atom_angle_pairs(
        session=session,
        config=config,
        as_of_date=as_of_date,
    )

    return (atom_id, angle_id) not in recently_used_pairs


# ════════════════════════════════════════════════════════════════════════════════
# CANDIDATE SELECTION
# ════════════════════════════════════════════════════════════════════════════════


def get_candidate_atoms(
    session: Session,
    pillar: ContentPillar,
    format: Format,
    config: AntiRepetitionConfig = DEFAULT_CONFIG,
    as_of_date: Optional[date] = None,
    limit: int = 100,
) -> List[ContentAtom]:
    """
    Get eligible atoms for a slot, respecting anti-repetition rules.

    First tries primary pillar match, then falls back to secondary pillars.

    Args:
        session: Database session
        pillar: Required content pillar
        format: Required content format
        config: Anti-repetition configuration
        as_of_date: Reference date (defaults to today)
        limit: Maximum results

    Returns:
        List of eligible ContentAtom objects ordered by virality_score
    """
    excluded_ids = get_excluded_atom_ids(
        session=session,
        config=config,
        as_of_date=as_of_date,
    )

    # Try primary pillar first
    candidates = db_services.get_eligible_atoms(
        session=session,
        pillar=pillar,
        format=format,
        excluded_atom_ids=excluded_ids,
        limit=limit,
    )

    # Fall back to secondary pillar if insufficient
    if len(candidates) < 5:
        logger.debug(
            "Insufficient primary pillar candidates (%d), checking secondary pillars",
            len(candidates),
        )
        secondary = db_services.get_eligible_atoms_by_secondary_pillar(
            session=session,
            pillar=pillar,
            format=format,
            excluded_atom_ids=excluded_ids,
            limit=limit - len(candidates),
        )
        candidates.extend(secondary)

    return candidates


def get_candidate_angles(
    session: Session,
    format: Format,
    atom_id: uuid.UUID,
    config: AntiRepetitionConfig = DEFAULT_CONFIG,
    as_of_date: Optional[date] = None,
) -> List[AngleMatrix]:
    """
    Get eligible angles for an atom, respecting anti-repetition rules.

    Excludes angles that have been used with this atom within cooldown period.

    Args:
        session: Database session
        format: Required content format
        atom_id: The selected atom ID
        config: Anti-repetition configuration
        as_of_date: Reference date (defaults to today)

    Returns:
        List of eligible AngleMatrix objects ordered by virality_multiplier
    """
    # Get all format-compatible angles
    all_angles = db_services.get_angles_for_format(session, format)

    if not all_angles:
        # Fallback to all active angles
        all_angles = db_services.get_active_angles(session)

    # Get excluded pairs
    excluded_pairs = get_excluded_atom_angle_pairs(
        session=session,
        config=config,
        as_of_date=as_of_date,
    )

    # Filter out excluded combinations
    excluded_angles = {pair[1] for pair in excluded_pairs if pair[0] == atom_id}

    eligible = [a for a in all_angles if a.id not in excluded_angles]

    return eligible


# ════════════════════════════════════════════════════════════════════════════════
# DIVERSITY HELPERS
# ════════════════════════════════════════════════════════════════════════════════


class DiversityMetrics(BaseModel):
    """Diversity analysis result."""

    diversity_score: float  # 0-1, higher = more diverse
    total_posts: int
    pillar_counts: dict[str, int]
    underused_pillars: List[str]


def calculate_diversity_score(
    session: Session,
    weeks: int = 4,
    as_of_date: Optional[date] = None,
) -> float:
    """
    Calculate a diversity score (0-1) for recent content.

    Higher score = more diverse content across pillars.
    Uses Shannon entropy normalized to 0-1 range.

    Args:
        session: Database session
        weeks: Lookback period
        as_of_date: Reference date (defaults to today)

    Returns:
        Diversity score between 0 (all same pillar) and 1 (perfectly balanced)
    """
    usage_counts = db_services.get_pillar_usage_counts(session, weeks, as_of_date)

    if not usage_counts:
        return 1.0  # No history = assume diverse

    total = sum(usage_counts.values())
    if total == 0:
        return 1.0

    # Calculate Shannon entropy
    entropy = 0.0
    for count in usage_counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)

    # Normalize to 0-1 (max entropy = log2(num_pillars))
    num_pillars = len(ContentPillar)
    max_entropy = math.log2(num_pillars)

    if max_entropy == 0:
        return 1.0

    return entropy / max_entropy


def get_underused_pillars(
    session: Session,
    weeks: int = 4,
    threshold: float = 0.8,
    as_of_date: Optional[date] = None,
) -> List[ContentPillar]:
    """
    Get pillars that are underrepresented in recent content.

    Useful for diversity boosting.

    Args:
        session: Database session
        weeks: Lookback period
        threshold: Ratio below which a pillar is "underused" (0.8 = 80% of expected)
        as_of_date: Reference date (defaults to today)

    Returns:
        List of underused ContentPillar values
    """
    usage_counts = db_services.get_pillar_usage_counts(session, weeks, as_of_date)
    total = sum(usage_counts.values())

    if total == 0:
        return list(ContentPillar)  # All pillars need content

    # Expected count per pillar (assuming even distribution)
    num_pillars = len(ContentPillar)
    expected_per_pillar = total / num_pillars

    underused = []
    for pillar in ContentPillar:
        actual = usage_counts.get(pillar.value, 0)
        if actual < expected_per_pillar * threshold:
            underused.append(pillar)

    return underused


def analyze_diversity(
    session: Session,
    weeks: int = 4,
    as_of_date: Optional[date] = None,
) -> DiversityMetrics:
    """
    Full diversity analysis for recent content.

    Args:
        session: Database session
        weeks: Lookback period
        as_of_date: Reference date (defaults to today)

    Returns:
        DiversityMetrics with all analysis data
    """
    usage_counts = db_services.get_pillar_usage_counts(session, weeks, as_of_date)
    underused = get_underused_pillars(session, weeks, as_of_date=as_of_date)
    score = calculate_diversity_score(session, weeks, as_of_date)

    return DiversityMetrics(
        diversity_score=score,
        total_posts=sum(usage_counts.values()),
        pillar_counts=usage_counts,
        underused_pillars=[p.value for p in underused],
    )
