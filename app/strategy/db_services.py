"""
Strategy DB Services.

Phase-scoped database operations for Phase 4 strategy.
This module contains ALL database READ/WRITE logic for strategy tables.

Tables managed:
- ContentSchedule (write)
- UsageHistory (write)
- AngleMatrix (read)
- ContentAtom (read)

This service contains NO business logic — only database operations.
"""

import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import func
from sqlmodel import Session, and_, or_, select

from app.db.db_models.classification import ContentAtom
from app.db.db_models.strategy import AngleMatrix, ContentSchedule, UsageHistory
from app.db.enums import ContentPillar, Format, LifecycleState, ScheduleStatus, PostingStatus

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════════
# CONTENT SCHEDULE OPERATIONS
# ════════════════════════════════════════════════════════════════════════════════


def insert_content_schedule(
    session: Session,
    week_year: int,
    week_number: int,
    slot_number: int,
    scheduled_date: date,
    day_of_week: str,
    required_pillar: ContentPillar,
    required_format: Format,
    scheduled_time: Optional[time] = None,
    trace_id: Optional[uuid.UUID] = None,
) -> ContentSchedule:
    """
    Insert an empty content schedule slot.

    Args:
        session: SQLModel session
        week_year: Year of the week (e.g., 2026)
        week_number: ISO week number (1-53)
        slot_number: Slot in the week (1-21)
        scheduled_date: Date for this slot
        day_of_week: Day name (e.g., "monday")
        required_pillar: Content pillar for this slot
        required_format: Content format for this slot
        scheduled_time: Optional posting time
        trace_id: Optional trace ID

    Returns:
        Created ContentSchedule record
    """
    schedule = ContentSchedule(
        trace_id=trace_id or uuid.uuid4(),
        week_year=week_year,
        week_number=week_number,
        slot_number=slot_number,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        day_of_week=day_of_week,
        required_pillar=required_pillar,
        required_format=required_format,
        status=ScheduleStatus.SCHEDULED,
        brief={},
    )

    session.add(schedule)
    session.flush()

    logger.debug(
        "Inserted ContentSchedule id=%s week=%d-%d slot=%d date=%s",
        schedule.id,
        week_year,
        week_number,
        slot_number,
        scheduled_date,
    )

    return schedule


def update_schedule_assignment(
    session: Session,
    schedule_id: uuid.UUID,
    atom_id: uuid.UUID,
    angle_id: str,
    brief: Dict[str, Any],
) -> bool:
    """
    Update a content schedule with atom and angle assignment.

    Args:
        session: SQLModel session
        schedule_id: ID of the schedule to update
        atom_id: Selected atom ID
        angle_id: Selected angle ID
        brief: Generated content brief

    Returns:
        True if update succeeded, False if schedule not found
    """
    schedule = session.get(ContentSchedule, schedule_id)
    if not schedule:
        return False

    schedule.atom_id = atom_id
    schedule.angle_id = angle_id
    schedule.brief = brief
    schedule.updated_at = datetime.now(timezone.utc)

    session.add(schedule)
    return True


def get_schedule_by_week(
    session: Session,
    week_year: int,
    week_number: int,
) -> List[ContentSchedule]:
    """
    Get all schedules for a specific week.

    Args:
        session: SQLModel session
        week_year: Year of the week
        week_number: ISO week number

    Returns:
        List of ContentSchedule records for the week
    """
    statement = (
        select(ContentSchedule)
        .where(
            and_(
                ContentSchedule.week_year == week_year,
                ContentSchedule.week_number == week_number,
            )
        )
        .order_by(ContentSchedule.slot_number)
    )

    return list(session.exec(statement).all())


def get_unfilled_schedules(
    session: Session,
    week_year: int,
    week_number: int,
) -> List[ContentSchedule]:
    """
    Get schedules without atom assignment for a week.

    Args:
        session: SQLModel session
        week_year: Year of the week
        week_number: ISO week number

    Returns:
        List of unfilled ContentSchedule records
    """
    statement = (
        select(ContentSchedule)
        .where(
            and_(
                ContentSchedule.week_year == week_year,
                ContentSchedule.week_number == week_number,
                ContentSchedule.atom_id.is_(None),
            )
        )
        .order_by(ContentSchedule.slot_number)
    )

    return list(session.exec(statement).all())


def schedule_exists_for_week(
    session: Session,
    week_year: int,
    week_number: int,
) -> bool:
    """
    Check if any schedules exist for a week.

    Args:
        session: SQLModel session
        week_year: Year of the week
        week_number: ISO week number

    Returns:
        True if schedules exist, False otherwise
    """
    statement = (
        select(func.count(ContentSchedule.id))
        .where(
            and_(
                ContentSchedule.week_year == week_year,
                ContentSchedule.week_number == week_number,
            )
        )
    )

    count = session.exec(statement).one()
    return count > 0


def delete_week_schedule(
    session: Session,
    week_year: int,
    week_number: int,
) -> int:
    """
    Delete all ContentSchedule rows for a specific week.

    GeneratedContent is explicitly deleted first (ORM doesn't cascade properly).
    UsageHistory.schedule_id is SET NULL (history preserved).

    Args:
        session: SQLModel session
        week_year: Year of the week
        week_number: ISO week number

    Returns:
        Number of deleted rows
    """
    statement = (
        select(ContentSchedule)
        .where(
            and_(
                ContentSchedule.week_year == week_year,
                ContentSchedule.week_number == week_number,
            )
        )
    )

    schedules = session.exec(statement).all()
    count = len(schedules)

    for schedule in schedules:
        # Explicitly delete GeneratedContent first to avoid NOT NULL violation
        # on schedule_id when SQLAlchemy tries to nullify FK before delete
        if schedule.generated_content is not None:
            session.delete(schedule.generated_content)
        session.delete(schedule)

    session.flush()

    logger.info(
        "Deleted %d ContentSchedule rows for week=%d-%d",
        count,
        week_year,
        week_number,
    )

    return count


def reset_week_schedule(
    session: Session,
    week_year: int,
    week_number: int,
) -> tuple[int, int]:
    """
    Reset all ContentSchedule rows for a week back to SCHEDULED status.

    Also deletes associated GeneratedContent so the pipeline can be re-run.
    ContentAtom usage is NOT reverted (times_used, last_used_at unchanged).

    Args:
        session: SQLModel session
        week_year: Year of the week
        week_number: ISO week number

    Returns:
        Tuple of (reset_count, deleted_generated_content_count)
    """
    from app.db.db_models.creation import GeneratedContent

    # Get all schedules for the week
    statement = (
        select(ContentSchedule)
        .where(
            and_(
                ContentSchedule.week_year == week_year,
                ContentSchedule.week_number == week_number,
            )
        )
    )

    schedules = session.exec(statement).all()
    reset_count = 0
    deleted_content_count = 0

    for schedule in schedules:
        # Delete associated GeneratedContent first
        if schedule.generated_content is not None:
            session.delete(schedule.generated_content)
            deleted_content_count += 1

        # Reset status to SCHEDULED
        if schedule.status != ScheduleStatus.SCHEDULED:
            schedule.status = ScheduleStatus.SCHEDULED
            session.add(schedule)
            reset_count += 1

    session.flush()

    logger.info(
        "Reset %d ContentSchedule rows, deleted %d GeneratedContent for week=%d-%d",
        reset_count,
        deleted_content_count,
        week_year,
        week_number,
    )

    return reset_count, deleted_content_count


# ════════════════════════════════════════════════════════════════════════════════
# USAGE HISTORY OPERATIONS
# ════════════════════════════════════════════════════════════════════════════════


def insert_usage_history(
    session: Session,
    schedule: ContentSchedule,
    atom: ContentAtom,
    angle_id: str,
) -> UsageHistory:
    """
    Insert a usage history record after scheduling.

    Args:
        session: SQLModel session
        schedule: ContentSchedule being used
        atom: ContentAtom being used
        angle_id: Angle ID being applied

    Returns:
        Created UsageHistory record
    """
    usage = UsageHistory(
        trace_id=schedule.trace_id,
        schedule_id=schedule.id,
        atom_id=atom.id,
        angle_id=angle_id,
        # Denormalized fields from atom
        pillar=atom.primary_pillar.value if hasattr(atom.primary_pillar, 'value') else atom.primary_pillar,
        format=schedule.required_format.value if hasattr(schedule.required_format, 'value') else schedule.required_format,
        # Denormalized fields from schedule
        scheduled_date=schedule.scheduled_date,
        scheduled_time=schedule.scheduled_time,
        day_of_week=schedule.day_of_week,
        week_year=schedule.week_year,
        week_number=schedule.week_number,
        # Initial status
        posting_status=PostingStatus.GENERATED,
    )

    session.add(usage)
    session.flush()

    logger.debug(
        "Inserted UsageHistory id=%s schedule=%s atom=%s angle=%s",
        usage.id,
        schedule.id,
        atom.id,
        angle_id,
    )

    return usage


def get_recently_used_atom_ids(
    session: Session,
    weeks: int = 6,
    as_of_date: Optional[date] = None,
) -> Set[uuid.UUID]:
    """
    Get IDs of atoms used within the last N weeks.

    Args:
        session: Database session
        weeks: Lookback period in weeks
        as_of_date: Reference date (defaults to today)

    Returns:
        Set of atom UUIDs that should be excluded
    """
    if as_of_date is None:
        as_of_date = date.today()

    cutoff_date = as_of_date - timedelta(weeks=weeks)

    statement = (
        select(UsageHistory.atom_id)
        .where(
            and_(
                UsageHistory.atom_id.is_not(None),
                UsageHistory.scheduled_date >= cutoff_date,
                UsageHistory.scheduled_date <= as_of_date,
            )
        )
        .distinct()
    )

    results = session.exec(statement).all()
    return {atom_id for atom_id in results if atom_id is not None}


def get_recently_used_atom_angle_pairs(
    session: Session,
    weeks: int = 12,
    as_of_date: Optional[date] = None,
) -> Set[Tuple[uuid.UUID, str]]:
    """
    Get (atom_id, angle_id) pairs used within the last N weeks.

    Args:
        session: Database session
        weeks: Lookback period in weeks
        as_of_date: Reference date (defaults to today)

    Returns:
        Set of (atom_id, angle_id) tuples that should be excluded
    """
    if as_of_date is None:
        as_of_date = date.today()

    cutoff_date = as_of_date - timedelta(weeks=weeks)

    statement = (
        select(UsageHistory.atom_id, UsageHistory.angle_id)
        .where(
            and_(
                UsageHistory.atom_id.is_not(None),
                UsageHistory.angle_id.is_not(None),
                UsageHistory.scheduled_date >= cutoff_date,
                UsageHistory.scheduled_date <= as_of_date,
            )
        )
        .distinct()
    )

    results = session.exec(statement).all()
    return {(row[0], row[1]) for row in results}


def get_pillar_usage_counts(
    session: Session,
    weeks: int = 4,
    as_of_date: Optional[date] = None,
) -> Dict[str, int]:
    """
    Get count of posts per pillar in the lookback period.

    Args:
        session: Database session
        weeks: Lookback period in weeks
        as_of_date: Reference date (defaults to today)

    Returns:
        Dict mapping pillar name to usage count
    """
    if as_of_date is None:
        as_of_date = date.today()

    cutoff_date = as_of_date - timedelta(weeks=weeks)

    statement = (
        select(UsageHistory.pillar, func.count(UsageHistory.id))
        .where(
            and_(
                UsageHistory.scheduled_date >= cutoff_date,
                UsageHistory.scheduled_date <= as_of_date,
            )
        )
        .group_by(UsageHistory.pillar)
    )

    results = session.exec(statement).all()
    return {row[0]: row[1] for row in results}


# ════════════════════════════════════════════════════════════════════════════════
# CONTENT ATOM QUERIES (Read-only)
# ════════════════════════════════════════════════════════════════════════════════


def get_eligible_atoms(
    session: Session,
    pillar: ContentPillar,
    format: Format,
    excluded_atom_ids: Set[uuid.UUID],
    limit: int = 100,
) -> List[ContentAtom]:
    """
    Get active atoms matching pillar/format, excluding recently used.

    Args:
        session: SQLModel session
        pillar: Required content pillar
        format: Required content format
        excluded_atom_ids: Set of atom IDs to exclude
        limit: Maximum results

    Returns:
        List of eligible ContentAtom objects ordered by virality_score
    """
    pillar_value = pillar.value if hasattr(pillar, 'value') else pillar
    format_value = format.value if hasattr(format, 'value') else format

    statement = (
        select(ContentAtom)
        .where(
            and_(
                ContentAtom.primary_pillar == pillar_value,
                ContentAtom.format_fit.contains([format_value]),
                ContentAtom.lifecycle_state == LifecycleState.ACTIVE.value,
                ContentAtom.deleted_at.is_(None),
            )
        )
    )

    if excluded_atom_ids:
        statement = statement.where(ContentAtom.id.not_in(excluded_atom_ids))

    statement = (
        statement
        .order_by(ContentAtom.virality_score.desc())
        .limit(limit)
    )

    return list(session.exec(statement).all())


def get_eligible_atoms_by_secondary_pillar(
    session: Session,
    pillar: ContentPillar,
    format: Format,
    excluded_atom_ids: Set[uuid.UUID],
    limit: int = 50,
) -> List[ContentAtom]:
    """
    Fallback: Get atoms where pillar is in secondary_pillars.

    Args:
        session: SQLModel session
        pillar: Required pillar (checked in secondary_pillars)
        format: Required content format
        excluded_atom_ids: Set of atom IDs to exclude
        limit: Maximum results

    Returns:
        List of eligible ContentAtom objects
    """
    pillar_value = pillar.value if hasattr(pillar, 'value') else pillar
    format_value = format.value if hasattr(format, 'value') else format

    statement = (
        select(ContentAtom)
        .where(
            and_(
                ContentAtom.secondary_pillars.contains([pillar_value]),
                ContentAtom.format_fit.contains([format_value]),
                ContentAtom.lifecycle_state == LifecycleState.ACTIVE.value,
                ContentAtom.deleted_at.is_(None),
            )
        )
    )

    if excluded_atom_ids:
        statement = statement.where(ContentAtom.id.not_in(excluded_atom_ids))

    statement = (
        statement
        .order_by(ContentAtom.virality_score.desc())
        .limit(limit)
    )

    return list(session.exec(statement).all())


def update_atom_usage(
    session: Session,
    atom_id: uuid.UUID,
) -> bool:
    """
    Update atom's usage tracking after scheduling.

    Args:
        session: SQLModel session
        atom_id: ID of the atom

    Returns:
        True if update succeeded, False if atom not found
    """
    atom = session.get(ContentAtom, atom_id)
    if not atom:
        return False

    atom.times_used = (atom.times_used or 0) + 1
    atom.last_used_at = datetime.now(timezone.utc)
    session.add(atom)

    return True


# ════════════════════════════════════════════════════════════════════════════════
# ANGLE MATRIX QUERIES (Read-only)
# ════════════════════════════════════════════════════════════════════════════════


def get_active_angles(session: Session) -> List[AngleMatrix]:
    """
    Get all active angles.

    Args:
        session: SQLModel session

    Returns:
        List of active AngleMatrix records
    """
    statement = (
        select(AngleMatrix)
        .where(AngleMatrix.is_active == True)
        .order_by(AngleMatrix.virality_multiplier.desc())
    )

    return list(session.exec(statement).all())


def get_angles_for_format(
    session: Session,
    format: Format,
) -> List[AngleMatrix]:
    """
    Get active angles compatible with a format.

    Args:
        session: SQLModel session
        format: Required content format

    Returns:
        List of compatible AngleMatrix records
    """
    format_value = format.value if hasattr(format, 'value') else format

    statement = (
        select(AngleMatrix)
        .where(
            and_(
                AngleMatrix.is_active == True,
                AngleMatrix.best_for_formats.contains([format_value]),
            )
        )
        .order_by(AngleMatrix.virality_multiplier.desc())
    )

    return list(session.exec(statement).all())


def get_angle_by_id(
    session: Session,
    angle_id: str,
) -> Optional[AngleMatrix]:
    """
    Get angle by ID.

    Args:
        session: SQLModel session
        angle_id: Angle identifier

    Returns:
        AngleMatrix or None
    """
    return session.get(AngleMatrix, angle_id)
