"""
Phase 5 Creation DB Services.

Phase-scoped database operations for the creation pipeline.
This module contains ALL database READ/WRITE logic for Phase 5.

Tables accessed:
- ContentSchedule (read + status update)
"""

import logging
import uuid
from typing import List, Optional

from sqlmodel import Session, select

from app.db.db_models.strategy import ContentSchedule
from app.db.enums import ScheduleStatus

logger = logging.getLogger(__name__)


# ============================================================================
# READ OPERATIONS
# ============================================================================


def get_pending_scheduled_content(
    session: Session,
    week_year: int,
    week_number: int,
    limit: int = 21,
) -> List[ContentSchedule]:
    """
    Fetch ContentSchedule rows ready for creation (status=SCHEDULED).

    Args:
        session: SQLModel session
        week_year: Target year (e.g., 2026)
        week_number: Target week number (1-53)
        limit: Maximum records to return (default 21 = full week)

    Returns:
        List of ContentSchedule records with SCHEDULED status
    """
    statement = (
        select(ContentSchedule)
        .where(ContentSchedule.week_year == week_year)
        .where(ContentSchedule.week_number == week_number)
        .where(ContentSchedule.status == ScheduleStatus.SCHEDULED)
        .order_by(ContentSchedule.slot_number)
        .limit(limit)
    )

    results = session.exec(statement).all()

    logger.debug(
        "[CREATION] Fetched %d scheduled rows: week=%d-%d",
        len(results),
        week_year,
        week_number,
    )

    return list(results)


def get_schedule_by_id(
    session: Session,
    schedule_id: uuid.UUID,
) -> Optional[ContentSchedule]:
    """
    Fetch a specific ContentSchedule by ID.

    Args:
        session: SQLModel session
        schedule_id: UUID of the schedule row

    Returns:
        ContentSchedule if found, None otherwise
    """
    return session.get(ContentSchedule, schedule_id)


def count_scheduled_for_week(
    session: Session,
    week_year: int,
    week_number: int,
) -> int:
    """
    Count scheduled content for a given week.

    Args:
        session: SQLModel session
        week_year: Target year
        week_number: Target week number

    Returns:
        Count of SCHEDULED rows
    """
    statement = (
        select(ContentSchedule)
        .where(ContentSchedule.week_year == week_year)
        .where(ContentSchedule.week_number == week_number)
        .where(ContentSchedule.status == ScheduleStatus.SCHEDULED)
    )

    return len(session.exec(statement).all())


# ============================================================================
# WRITE OPERATIONS
# ============================================================================


def update_schedule_status(
    session: Session,
    schedule_id: uuid.UUID,
    status: ScheduleStatus,
) -> bool:
    """
    Update ContentSchedule status.

    Args:
        session: SQLModel session
        schedule_id: ID of the schedule record
        status: New status (e.g., CREATING, DRAFT, SKIPPED)

    Returns:
        True if update succeeded, False if record not found
    """
    schedule = session.get(ContentSchedule, schedule_id)
    if not schedule:
        logger.warning(
            "[CREATION] Schedule not found for status update: %s", schedule_id
        )
        return False

    old_status = schedule.status
    schedule.status = status
    session.add(schedule)

    logger.debug(
        "[CREATION] Status updated: schedule_id=%s, %s -> %s",
        schedule_id,
        old_status.value if old_status else "None",
        status.value,
    )

    return True


def flag_for_human_review(
    session: Session,
    schedule_id: uuid.UUID,
    reason: str,
) -> bool:
    """
    Flag a schedule row for human review when content is UNSUITABLE.

    Updates status to SKIPPED and stores the reason in the brief JSONB.

    Args:
        session: SQLModel session
        schedule_id: ID of the schedule record
        reason: Why this content was flagged as unsuitable

    Returns:
        True if flagged successfully, False if record not found
    """
    schedule = session.get(ContentSchedule, schedule_id)
    if not schedule:
        logger.warning("[CREATION] Schedule not found for flagging: %s", schedule_id)
        return False

    # Store the review reason in the brief
    if schedule.brief is None:
        schedule.brief = {}

    schedule.brief["_review_flag"] = {
        "status": "NEEDS_HUMAN_REVIEW",
        "reason": reason,
        "phase": "CREATION_STAGE_1",
    }

    # schedule.status = ScheduleStatus.SKIPPED
    session.add(schedule)

    logger.info(
        "[CREATION] Flagged for review: schedule_id=%s, reason=%s",
        schedule_id,
        reason[:50] if reason else "None",
    )

    return True


def store_stage1_analysis(
    session: Session,
    schedule_id: uuid.UUID,
    analysis_dict: dict,
) -> bool:
    """
    Store Stage 1 analysis result in the ContentSchedule brief.

    The analysis is stored under the "_stage1_analysis" key in the brief JSONB.

    Args:
        session: SQLModel session
        schedule_id: ID of the schedule record
        analysis_dict: Stage1Analysis as a dictionary

    Returns:
        True if stored successfully, False if record not found
    """
    schedule = session.get(ContentSchedule, schedule_id)
    if not schedule:
        logger.warning(
            "[CREATION] Schedule not found for storing analysis: %s", schedule_id
        )
        return False

    # Store the analysis in the brief
    if schedule.brief is None:
        schedule.brief = {}

    schedule.brief["_stage1_analysis"] = analysis_dict
    session.add(schedule)

    logger.debug(
        "[CREATION] Stored Stage1 analysis: schedule_id=%s, readiness=%s",
        schedule_id,
        analysis_dict.get("instagram_readiness", "UNKNOWN"),
    )

    return True


def store_generated_content(
    session: Session,
    schedule_id: uuid.UUID,
    trace_id: uuid.UUID,
    format_type: str,
    content_json: dict,
    generation_context: dict,
    resolved_mode: str,
    emotional_journey: dict,
    emotional_arc: dict,
    mode_sequence: dict,
    critique_scores: dict,
    generation_attempts: int,
    flag_reasons: list = None,
    is_flagged: bool = False,
) -> uuid.UUID:
    """
    Store generated content in the GeneratedContent table.

    Args:
        session: SQLModel session
        schedule_id: ID of the ContentSchedule record
        trace_id: Trace ID for lineage
        format_type: REEL, CAROUSEL, or QUOTE
        content_json: The full content as a dictionary
        generation_context: Full GenerationContext for debugging
        resolved_mode: Mode used for generation
        emotional_journey: Three-state emotional journey (DEPRECATED)
        emotional_arc: 5-stage continuous emotional arc
        mode_sequence: Three-part mode journey (opener, bridge, closer)
        critique_scores: CritiqueScores from Stage 4
        generation_attempts: Number of attempts used
        flag_reasons: List of hard filter failures (if any)
        is_flagged: True if content should be flagged for review

    Returns:
        UUID of the created GeneratedContent record
    """
    from app.db.db_models.creation import GeneratedContent
    from app.db.enums import Format, GeneratedContentStatus

    # Determine status
    status = (
        GeneratedContentStatus.FLAGGED_FOR_REVIEW
        if is_flagged
        else GeneratedContentStatus.APPROVED
    )

    # Create the record
    generated = GeneratedContent(
        schedule_id=schedule_id,
        trace_id=trace_id,
        format_type=Format(format_type),
        content_json=content_json,
        generation_context=generation_context,
        resolved_mode=resolved_mode,
        emotional_journey=emotional_journey,
        emotional_arc=emotional_arc,
        mode_sequence=mode_sequence,
        critique_scores=critique_scores,
        generation_attempts=generation_attempts,
        status=status,
        flag_reasons=flag_reasons or [],
    )

    session.add(generated)
    session.flush()  # Get the ID without committing

    logger.info(
        "[CREATION:S5] stored content: id=%s, schedule_id=%s, status=%s",
        generated.id,
        schedule_id,
        status.value,
    )

    return generated.id


def delete_generated_content(
    session: Session,
    content_id: uuid.UUID,
) -> bool:
    """
    Delete a GeneratedContent record by ID.

    Args:
        session: SQLModel session
        content_id: UUID of the GeneratedContent record

    Returns:
        True if deleted, False if not found
    """
    from app.db.db_models.creation import GeneratedContent

    content = session.get(GeneratedContent, content_id)
    if not content:
        logger.warning(
            "[CREATION] GeneratedContent not found for deletion: %s", content_id
        )
        return False

    session.delete(content)
    session.flush()

    logger.info("[CREATION] Deleted GeneratedContent: id=%s", content_id)

    return True

