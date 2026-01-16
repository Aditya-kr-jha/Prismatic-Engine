"""
Phase 4: Schedule Generator Service for Prismatic Engine.

This is the "Remix Engine" that:
1. Creates 21 content_schedule rows for a given week
2. Fills each slot with the best atom + angle combination
3. Generates content briefs for Phase 5
4. Records usage in usage_history for anti-repetition

Run this every Sunday evening to generate the upcoming week's schedule.
"""

import logging
import uuid
from datetime import date, time as dt_time, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, cast

from pydantic import BaseModel
from sqlmodel import Session, and_, select

from app.db.db_models.classification import ContentAtom
from app.db.db_models.strategy import AngleMatrix, ContentSchedule, UsageHistory
from app.db.db_session import get_session
from app.db.enums import ContentPillar, Format
from app.strategy import db_services
from app.strategy.anti_repetition import (
    DEFAULT_CONFIG,
    AntiRepetitionConfig,
    get_candidate_atoms,
    get_excluded_atom_angle_pairs,
    get_underused_pillars,
    calculate_diversity_score,
)
from app.strategy.lifecycle_manager import (
    LifecycleConfig,
    update_atom_after_scheduling,
    process_cooling_atoms,
)
from app.strategy.weekly_slots import (
    DAY_OFFSETS,
    WEEKLY_SLOTS_TEMPLATE,
    SlotTemplate,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════════
# RESULT MODELS
# ════════════════════════════════════════════════════════════════════════════════


class SlotFillResult(BaseModel):
    """Result of attempting to fill a single slot."""

    slot_number: int
    success: bool = False
    atom_id: Optional[uuid.UUID] = None
    angle_id: Optional[str] = None
    score: float = 0.0
    fallback_used: bool = False
    error_message: Optional[str] = None


class ScheduleGenerationResult(BaseModel):
    """Result of generating a full week's schedule."""

    week_year: int
    week_number: int
    start_date: date
    total_slots: int
    filled_slots: int
    failed_slots: int
    fallback_slots: int
    diversity_score: float
    slot_results: List[SlotFillResult]
    trace_id: uuid.UUID


# ════════════════════════════════════════════════════════════════════════════════
# ANGLE SELECTION
# ════════════════════════════════════════════════════════════════════════════════


def get_compatible_angles(
    session: Session,
    pillar: ContentPillar,
    format: Format,
    complexity_score: int = 3,
) -> List[AngleMatrix]:
    """
    Get angles compatible with a given pillar/format/complexity.

    Args:
        session: Database session
        pillar: Content pillar
        format: Content format
        complexity_score: Atom's complexity (1-5)

    Returns:
        List of compatible AngleMatrix objects, ordered by virality_multiplier
    """
    pillar_value = pillar.value if hasattr(pillar, "value") else pillar
    format_value = format.value if hasattr(format, "value") else format

    statement = (
        select(AngleMatrix)
        .where(
            and_(
                AngleMatrix.is_active == True,
                # Pillar in best_for_pillars
                AngleMatrix.best_for_pillars.contains([pillar_value]),
                # Format in best_for_formats
                AngleMatrix.best_for_formats.contains([format_value]),
            )
        )
        .order_by(AngleMatrix.virality_multiplier.desc())
    )

    angles = list(session.exec(statement).all())

    # Filter by complexity range (stored in constraints JSONB)
    compatible = []
    for angle in angles:
        constraints = angle.constraints or {}
        complexity_range = constraints.get("complexity_range", [1, 5])
        if len(complexity_range) >= 2:
            min_complexity, max_complexity = complexity_range[0], complexity_range[1]
            if min_complexity <= complexity_score <= max_complexity:
                compatible.append(angle)
        else:
            compatible.append(angle)  # No constraint, include it

    return compatible


def get_fallback_angles(
    session: Session,
    format: Format,
) -> List[AngleMatrix]:
    """
    Get any active angle that works with the format (fallback when no ideal match).

    Args:
        session: Database session
        format: Content format

    Returns:
        List of AngleMatrix objects
    """
    format_value = format.value if hasattr(format, "value") else format

    statement = (
        select(AngleMatrix)
        .where(
            and_(
                AngleMatrix.is_active == True,
                AngleMatrix.best_for_formats.contains([format_value]),
            )
        )
        .order_by(AngleMatrix.virality_multiplier.desc())
        .limit(5)
    )

    return list(session.exec(statement).all())


# ════════════════════════════════════════════════════════════════════════════════
# SCORING
# ════════════════════════════════════════════════════════════════════════════════


def calculate_candidate_score(
    atom: ContentAtom,
    angle: AngleMatrix,
    pillar: ContentPillar,
    underused_pillars: List[ContentPillar],
    slot_priority: int = 2,
) -> float:
    """
    Calculate a combined score for an atom + angle combination.

    Score = atom_virality × angle_multiplier × boosts

    Args:
        atom: The content atom
        angle: The angle to apply
        pillar: The target pillar
        underused_pillars: List of pillars that need more content
        slot_priority: Slot priority (1=high, 2=normal, 3=experimental)

    Returns:
        Combined score (higher is better)
    """
    # Base scores
    atom_score = atom.virality_score or 5.0
    angle_multiplier = angle.virality_multiplier or 1.0

    # Start with base calculation
    score = atom_score * angle_multiplier

    # Boost for high-priority slots (want best content)
    if slot_priority == 1:
        score *= 1.2

    # Boost for atoms whose secondary pillars touch underused topics
    # This helps balance diversity even when slot pillar is fixed by template
    atom_secondary_pillars = []
    for p in (atom.secondary_pillars or []):
        try:
            atom_secondary_pillars.append(ContentPillar(p) if isinstance(p, str) else p)
        except ValueError:
            continue  # Skip invalid pillar values
    
    if any(sp in underused_pillars for sp in atom_secondary_pillars):
        score *= 1.15  # Boost atoms that touch underused topics via secondary pillars

    # Penalty for low-credibility with scientific angles
    constraints = angle.constraints or {}
    if constraints.get("requires_proof"):
        # Check source metadata for credibility if available
        source_meta = atom.source_metadata or {}
        credibility = source_meta.get("credibility", "MEDIUM")
        if credibility == "LOW":
            score *= 0.5  # Heavy penalty

    return score


# ════════════════════════════════════════════════════════════════════════════════
# BRIEF BUILDER
# ════════════════════════════════════════════════════════════════════════════════


# Pillar to target emotions mapping
PILLAR_EMOTIONS: Dict[str, List[str]] = {
    "PRODUCTIVITY": ["EMPOWERMENT", "CURIOSITY"],
    "DARK_PSYCHOLOGY": ["CURIOSITY", "FEAR"],
    "RELATIONSHIPS": ["VALIDATION", "HOPE"],
    "NEUROSCIENCE": ["CURIOSITY", "IDENTITY"],
    "PHILOSOPHY": ["CURIOSITY", "IDENTITY"],
    "HEALING_GROWTH": ["HOPE", "EMPOWERMENT"],
    "SELF_CARE": ["VALIDATION", "HOPE"],
    "SELF_WORTH": ["EMPOWERMENT", "VALIDATION"],
}


def build_content_brief(
    atom: ContentAtom,
    angle: AngleMatrix,
    slot: SlotTemplate,
) -> Dict[str, Any]:
    """
    Build the content brief JSON that Phase 5 will use.

    The brief should be SELF-CONTAINED — Phase 5 should not need
    to query other tables.

    Args:
        atom: The selected content atom
        angle: The selected angle
        slot: The slot template

    Returns:
        Complete brief dictionary
    """
    # Extract constraints from angle
    constraints = angle.constraints or {}
    tone = constraints.get("tone", "Neutral")

    # Get target emotions for this pillar
    pillar_value = slot.pillar.value if hasattr(slot.pillar, "value") else slot.pillar
    target_emotions = PILLAR_EMOTIONS.get(pillar_value, ["CURIOSITY"])

    # Build the brief
    brief = {
        # === IDENTIFIERS ===
        "atom_id": str(atom.id),
        "angle_id": angle.id,
        # === CREATIVE DIRECTION ===
        "angle_template": angle.template,
        "angle_name": angle.name,
        "pillar": pillar_value,
        "format": slot.format.value if hasattr(slot.format, "value") else slot.format,
        "target_emotions": target_emotions,
        "tone": tone,
        "complexity": atom.complexity_score or 3,
        # === SOURCE CONTENT (THE KEY PART) ===
        "raw_content": atom.raw_content,
        "atomic_components": atom.atomic_components or {},
        # === CONTENT SIGNALS ===
        "classification": atom.classification or {},
        # === METADATA ===
        "slot_number": slot.slot_number,
        "slot_priority": slot.priority,
        "slot_notes": slot.notes,
        # === ANGLE CONSTRAINTS ===
        "angle_constraints": constraints,
        # === EXAMPLE (for LLM guidance) ===
        "angle_example": angle.example_content,
    }

    return brief


# ════════════════════════════════════════════════════════════════════════════════
# SLOT FILLER
# ════════════════════════════════════════════════════════════════════════════════


def fill_single_slot(
    session: Session,
    slot: SlotTemplate,
    week_start_date: date,
    week_year: int,
    week_number: int,
    trace_id: uuid.UUID,
    config: AntiRepetitionConfig = DEFAULT_CONFIG,
    lifecycle_config: LifecycleConfig = LifecycleConfig(),
    underused_pillars: Optional[List[ContentPillar]] = None,
    atoms_used_this_week: Optional[Set[uuid.UUID]] = None,
) -> Tuple[ContentSchedule, Optional[UsageHistory], SlotFillResult]:
    """
    Fill a single slot with the best atom + angle combination.

    Args:
        session: Database session
        slot: The slot template to fill
        week_start_date: Monday of the target week
        week_year: Year (e.g., 2026)
        week_number: ISO week number (1-53)
        trace_id: Trace ID for this generation run
        config: Anti-repetition configuration
        lifecycle_config: Lifecycle management configuration
        underused_pillars: Pillars that need diversity boost
        atoms_used_this_week: Set of atom IDs already used in this week's generation

    Returns:
        Tuple of (ContentSchedule, UsageHistory or None, SlotFillResult)
    """
    if underused_pillars is None:
        underused_pillars = []
    if atoms_used_this_week is None:
        atoms_used_this_week = set()

    # Calculate scheduled date
    day_offset = DAY_OFFSETS[slot.day_of_week]
    scheduled_date = week_start_date + timedelta(days=day_offset)
    scheduled_time = dt_time.fromisoformat(slot.time)

    result = SlotFillResult(slot_number=slot.slot_number, success=False)

    # Step 1: Get eligible atoms (respects anti-repetition)
    eligible_atoms = get_candidate_atoms(
        session=session,
        pillar=slot.pillar,
        format=slot.format,
        config=config,
        as_of_date=scheduled_date,
    )

    # Step 1b: Exclude atoms already used in this week's generation run
    # This prevents the same atom from being used for multiple slots (e.g., PRODUCTIVITY-REEL and PRODUCTIVITY-QUOTE)
    if atoms_used_this_week:
        eligible_atoms = [a for a in eligible_atoms if a.id not in atoms_used_this_week]

    # Step 2: If no atoms found, return empty schedule
    if not eligible_atoms:
        logger.warning(f"Slot {slot.slot_number}: No eligible atoms found")
        result.error_message = "No eligible atoms found"

        schedule = db_services.insert_content_schedule(
            session=session,
            week_year=week_year,
            week_number=week_number,
            slot_number=slot.slot_number,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            day_of_week=slot.day_of_week,
            required_pillar=slot.pillar,
            required_format=slot.format,
            trace_id=trace_id,
        )

        return schedule, None, result

    # Step 3: Get recently used atom+angle pairs for filtering
    used_pairs = get_excluded_atom_angle_pairs(
        session=session,
        config=config,
        as_of_date=scheduled_date,
    )

    # Step 4: Score all atom + angle combinations
    best_score = -1.0
    best_atom: Optional[ContentAtom] = None
    best_angle: Optional[AngleMatrix] = None

    for atom in eligible_atoms:
        # Get compatible angles for this atom
        compatible_angles = get_compatible_angles(
            session=session,
            pillar=slot.pillar,
            format=slot.format,
            complexity_score=atom.complexity_score or 3,
        )

        # Fallback if no compatible angles
        if not compatible_angles:
            compatible_angles = get_fallback_angles(session, format=slot.format)
            if compatible_angles:
                result.fallback_used = True

        for angle in compatible_angles:
            # Skip recently used combinations
            if (atom.id, angle.id) in used_pairs:
                continue

            # Calculate score
            score = calculate_candidate_score(
                atom=atom,
                angle=angle,
                pillar=slot.pillar,
                underused_pillars=underused_pillars,
                slot_priority=slot.priority,
            )

            if score > best_score:
                best_score = score
                best_atom = atom
                best_angle = angle

    # Step 5: Handle no valid combination found
    if best_atom is None or best_angle is None:
        logger.warning(f"Slot {slot.slot_number}: No valid atom+angle combination")
        result.error_message = "No valid atom+angle combination"

        schedule = db_services.insert_content_schedule(
            session=session,
            week_year=week_year,
            week_number=week_number,
            slot_number=slot.slot_number,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            day_of_week=slot.day_of_week,
            required_pillar=slot.pillar,
            required_format=slot.format,
            trace_id=trace_id,
        )

        return schedule, None, result

    # Step 6: Build the brief
    brief = build_content_brief(
        atom=best_atom,
        angle=best_angle,
        slot=slot,
    )

    # Step 7: Create ContentSchedule entry
    schedule = db_services.insert_content_schedule(
        session=session,
        week_year=week_year,
        week_number=week_number,
        slot_number=slot.slot_number,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        day_of_week=slot.day_of_week,
        required_pillar=slot.pillar,
        required_format=slot.format,
        trace_id=trace_id,
    )

    # Update with atom and angle assignment
    db_services.update_schedule_assignment(
        session=session,
        schedule_id=schedule.id,
        atom_id=best_atom.id,
        angle_id=best_angle.id,
        brief=brief,
    )

    # Step 8: Create UsageHistory entry
    usage = db_services.insert_usage_history(
        session=session,
        schedule=schedule,
        atom=best_atom,
        angle_id=best_angle.id,
    )

    # Step 9: Update atom lifecycle and usage tracking
    update_atom_after_scheduling(session, best_atom, lifecycle_config)

    # Step 10: Update result
    result.success = True
    result.atom_id = best_atom.id
    result.angle_id = best_angle.id
    result.score = best_score

    logger.info(
        f"Slot {slot.slot_number}: Filled with atom={best_atom.id}, "
        f"angle={best_angle.id}, score={best_score:.2f}"
    )

    return schedule, usage, result


# ════════════════════════════════════════════════════════════════════════════════
# MAIN GENERATOR
# ════════════════════════════════════════════════════════════════════════════════


class ScheduleGeneratorService:
    """
    Orchestrates Phase 4 schedule generation.

    This is the MAIN ENTRY POINT for Phase 4. Run this every Sunday evening
    to generate the upcoming week's schedule.

    Usage:
        service = ScheduleGeneratorService()
        result = service.generate_weekly_schedule(start_date=date(2026, 1, 6))
    """

    def __init__(
        self,
        config: AntiRepetitionConfig = DEFAULT_CONFIG,
        lifecycle_config: LifecycleConfig = LifecycleConfig(),
    ):
        """
        Initialize the schedule generator service.

        Args:
            config: Anti-repetition configuration
            lifecycle_config: Lifecycle management configuration
        """
        self.config = config
        self.lifecycle_config = lifecycle_config

    def generate_weekly_schedule(
        self,
        start_date: date,
        force: bool = False,
    ) -> ScheduleGenerationResult:
        """
        Generate a complete weekly schedule (21 slots).

        Args:
            start_date: Monday of the target week
            force: If True, delete existing schedule for this week and regenerate

        Returns:
            ScheduleGenerationResult with details of the generation

        Raises:
            ValueError: If schedule already exists and force=False
        """
        # Calculate week identifiers
        iso_calendar = start_date.isocalendar()
        week_year = iso_calendar[0]
        week_number = iso_calendar[1]

        # Generate trace ID for this run
        trace_id = uuid.uuid4()

        logger.info(
            f"Starting schedule generation for Week {week_number}, {week_year} "
            f"(trace_id={trace_id})"
        )

        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            # Check for existing schedule
            existing = db_services.schedule_exists_for_week(
                session=session,
                week_year=week_year,
                week_number=week_number,
            )

            if existing and not force:
                raise ValueError(
                    f"Schedule already exists for Week {week_number}, {week_year}. "
                    f"Use force=True to regenerate."
                )

            if existing and force:
                logger.warning(f"Force regenerating schedule for Week {week_number}")
                # Delete existing schedule entries
                existing_schedules = db_services.get_schedule_by_week(
                    session=session,
                    week_year=week_year,
                    week_number=week_number,
                )
                for sched in existing_schedules:
                    session.delete(sched)
                session.commit()

            # Reactivate atoms whose cooling period has ended (COOLING → ACTIVE)
            # This must happen BEFORE we query for eligible atoms
            reactivated_count = process_cooling_atoms(
                session, self.lifecycle_config, commit=False
            )
            if reactivated_count > 0:
                logger.info(
                    f"Reactivated {reactivated_count} atoms from COOLING to ACTIVE"
                )

            # Get underused pillars for diversity boosting
            underused_pillars = get_underused_pillars(
                session=session,
                weeks=self.config.lookback_weeks,
                as_of_date=start_date,
            )

            if underused_pillars:
                logger.info(
                    f"Underused pillars (will boost): {[p.value for p in underused_pillars]}"
                )

            # Fill all 21 slots
            schedules: List[ContentSchedule] = []
            usages: List[UsageHistory] = []
            slot_results: List[SlotFillResult] = []
            
            # Track atoms used in THIS generation run to prevent same atom in multiple slots
            atoms_used_this_week: Set[uuid.UUID] = set()

            for slot in WEEKLY_SLOTS_TEMPLATE:
                schedule, usage, result = fill_single_slot(
                    session=session,
                    slot=slot,
                    week_start_date=start_date,
                    week_year=week_year,
                    week_number=week_number,
                    trace_id=trace_id,
                    config=self.config,
                    lifecycle_config=self.lifecycle_config,
                    underused_pillars=underused_pillars,
                    atoms_used_this_week=atoms_used_this_week,
                )

                # Track atom to prevent reuse in subsequent slots
                if result.atom_id:
                    atoms_used_this_week.add(result.atom_id)

                schedules.append(schedule)
                slot_results.append(result)

                if usage:
                    usages.append(usage)

            # Commit all changes
            next(session_gen, None)

            # Calculate final diversity score
            session_gen2 = get_session()
            session2 = cast(Session, next(session_gen2))
            try:
                diversity_score = calculate_diversity_score(
                    session=session2,
                    weeks=self.config.lookback_weeks,
                    as_of_date=start_date,
                )
            finally:
                try:
                    next(session_gen2, None)
                except Exception:
                    pass

            # Build result
            filled = sum(1 for r in slot_results if r.success)
            failed = sum(1 for r in slot_results if not r.success)
            fallback = sum(1 for r in slot_results if r.fallback_used)

            result = ScheduleGenerationResult(
                week_year=week_year,
                week_number=week_number,
                start_date=start_date,
                total_slots=len(WEEKLY_SLOTS_TEMPLATE),
                filled_slots=filled,
                failed_slots=failed,
                fallback_slots=fallback,
                diversity_score=diversity_score,
                slot_results=slot_results,
                trace_id=trace_id,
            )

            logger.info(
                f"Schedule generation complete: {filled}/{result.total_slots} filled, "
                f"{failed} failed, {fallback} used fallback, "
                f"diversity={diversity_score:.2f}"
            )

            return result

        except Exception as e:
            logger.exception("Schedule generation failed")
            raise

        finally:
            try:
                next(session_gen, None)
            except Exception:
                pass

    def get_week_schedule(
        self,
        week_year: int,
        week_number: int,
    ) -> List[ContentSchedule]:
        """
        Get existing schedule for a week.

        Args:
            week_year: Year
            week_number: ISO week number

        Returns:
            List of ContentSchedule records
        """
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            return db_services.get_schedule_by_week(
                session=session,
                week_year=week_year,
                week_number=week_number,
            )
        finally:
            try:
                next(session_gen, None)
            except Exception:
                pass


# ════════════════════════════════════════════════════════════════════════════════
# TEST SCRIPT
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json
    import sys
    from datetime import date
    from pathlib import Path

    # Add project root to path for direct script execution
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # Parse flags first
    force = "--force" in sys.argv or "-f" in sys.argv
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv

    # Parse date from positional arguments (filter out flags)
    positional_args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    if positional_args:
        start_date = date.fromisoformat(positional_args[0])
    else:
        # Default to next Monday
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # Next Monday, not today
        start_date = today + timedelta(days=days_until_monday)

    print(f"\n{'='*60}")
    print(f"PRISMATIC ENGINE - PHASE 4 SCHEDULE GENERATOR")
    print(f"{'='*60}")
    print(f"Target week start date: {start_date}")
    print(f"Force regenerate: {force}")
    print(f"Dry run: {dry_run}")
    print(f"{'='*60}\n")

    if dry_run:
        print("DRY RUN MODE - No database changes will be made")
        print("\nWould generate schedule for:")
        print(f"  Week: {start_date.isocalendar()[1]}, {start_date.isocalendar()[0]}")
        print(f"  Slots: 21")
        print(f"\nTemplate validation:")

        from app.strategy.weekly_slots import validate_template

        validation = validate_template()
        print(json.dumps(validation.model_dump(), indent=2))
        sys.exit(0)

    # Run the generator
    try:
        service = ScheduleGeneratorService()
        result = service.generate_weekly_schedule(
            start_date=start_date,
            force=force,
        )

        print(f"\n{'='*60}")
        print(f"GENERATION RESULT")
        print(f"{'='*60}")
        print(f"Week: {result.week_number}, {result.week_year}")
        print(f"Trace ID: {result.trace_id}")
        print(f"Total slots: {result.total_slots}")
        print(f"Filled: {result.filled_slots}")
        print(f"Failed: {result.failed_slots}")
        print(f"Fallbacks: {result.fallback_slots}")
        print(f"Diversity score: {result.diversity_score:.2f}")

        print(f"\nSlot Details:")
        for sr in result.slot_results:
            status = "✓" if sr.success else "✗"
            fallback = " (fallback)" if sr.fallback_used else ""
            if sr.success:
                print(
                    f"  {status} Slot {sr.slot_number}: atom={sr.atom_id}, angle={sr.angle_id}, score={sr.score:.2f}{fallback}"
                )
            else:
                print(f"  {status} Slot {sr.slot_number}: {sr.error_message}")

    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        raise
