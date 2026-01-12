"""
Database services for delivery phase.
"""

import logging
import uuid
from datetime import date
from typing import List, Optional, Tuple

from sqlmodel import Session, select, and_

from app.db.db_models.creation import GeneratedContent
from app.db.db_models.strategy import ContentSchedule
from app.db.enums import GeneratedContentStatus, ScheduleStatus

logger = logging.getLogger(__name__)


def get_approved_content_for_week(
    session: Session,
    week_year: int,
    week_number: int,
) -> List[Tuple[GeneratedContent, ContentSchedule]]:
    """
    Fetch all approved GeneratedContent for a week with their schedules.

    Args:
        session: SQLModel session
        week_year: Year (e.g., 2026)
        week_number: ISO week number (1-53)

    Returns:
        List of (GeneratedContent, ContentSchedule) tuples
    """
    statement = (
        select(GeneratedContent, ContentSchedule)
        .join(ContentSchedule, GeneratedContent.schedule_id == ContentSchedule.id)
        .where(
            and_(
                ContentSchedule.week_year == week_year,
                ContentSchedule.week_number == week_number,
                GeneratedContent.status == GeneratedContentStatus.APPROVED,
            )
        )
        .order_by(ContentSchedule.slot_number)
    )

    results = session.exec(statement).all()

    logger.debug(
        f"[DELIVERY] Fetched {len(results)} approved items for week {week_year}-W{week_number}"
    )

    return list(results)


def update_schedule_to_delivered(
    session: Session,
    schedule_id: uuid.UUID,
) -> bool:
    """
    Update ContentSchedule status to DELIVERED.

    Args:
        session: SQLModel session
        schedule_id: Schedule ID to update

    Returns:
        True if updated, False if not found
    """
    schedule = session.get(ContentSchedule, schedule_id)
    if not schedule:
        logger.warning(f"[DELIVERY] Schedule not found: {schedule_id}")
        return False

    # Update to DELIVERED (from any status except already DELIVERED)
    if schedule.status != ScheduleStatus.DELIVERED:
        old_status = schedule.status
        schedule.status = ScheduleStatus.DELIVERED
        session.add(schedule)
        logger.debug(f"[DELIVERY] Updated schedule {schedule_id}: {old_status} -> DELIVERED")
        return True
    else:
        logger.debug(
            f"[DELIVERY] Schedule {schedule_id} already DELIVERED, skipping"
        )
        return False


def update_generated_content_delivered(
    session: Session,
    content_id: uuid.UUID,
) -> bool:
    """
    Mark GeneratedContent as delivered (keeps APPROVED status but logs delivery).
    
    Note: GeneratedContent status enum only has APPROVED, FLAGGED_FOR_REVIEW, REJECTED.
    Delivery tracking is done via ContentSchedule.status = DELIVERED.
    """
    content = session.get(GeneratedContent, content_id)
    if not content:
        logger.warning(f"[DELIVERY] GeneratedContent not found: {content_id}")
        return False
    
    # GeneratedContent.status remains APPROVED - delivery is tracked via ContentSchedule
    logger.debug(f"[DELIVERY] GeneratedContent {content_id} marked as delivered")
    return True


def batch_update_to_delivered(
    session: Session,
    schedule_ids: List[uuid.UUID],
) -> int:
    """
    Batch update multiple schedules to DELIVERED.

    Args:
        session: SQLModel session
        schedule_ids: List of schedule IDs

    Returns:
        Number of schedules updated
    """
    updated = 0
    for schedule_id in schedule_ids:
        if update_schedule_to_delivered(session, schedule_id):
            updated += 1

    session.commit()
    logger.info(
        f"[DELIVERY] Batch updated {updated}/{len(schedule_ids)} schedules to DELIVERED"
    )

    return updated


def get_week_date_range(
    session: Session,
    week_year: int,
    week_number: int,
) -> Tuple[Optional[date], Optional[date]]:
    """
    Get the date range for a week from existing schedules.

    Returns:
        Tuple of (start_date, end_date) or (None, None) if no schedules
    """
    statement = (
        select(ContentSchedule.scheduled_date)
        .where(
            and_(
                ContentSchedule.week_year == week_year,
                ContentSchedule.week_number == week_number,
            )
        )
        .order_by(ContentSchedule.scheduled_date)
    )

    dates = session.exec(statement).all()

    if not dates:
        return None, None

    return min(dates), max(dates)
