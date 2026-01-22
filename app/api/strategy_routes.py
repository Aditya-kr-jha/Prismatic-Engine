"""
Strategy API Routes.

REST endpoints for Phase 4 schedule generation and retrieval.

Routes must remain thin:
- No business logic
- No direct DB access
- No parsing
- Just orchestration
"""

import logging
import uuid
from datetime import date
from typing import cast

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel
from sqlmodel import Session

from app.api.schemas.strategy import (
    ContentScheduleItem,
    DeleteScheduleResponse,
    GenerateScheduleRequest,
    ResetScheduleResponse,
    ScheduleExistsResponse,
    ScheduleGenerationResponse,
    SlotFillResultItem,
    WeekScheduleResponse,
)
from app.db.db_session import get_session
from app.strategy import db_services
from app.strategy.services import ScheduleGeneratorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategy", tags=["Strategy"])


# ============================================================================
# Helper Functions
# ============================================================================


def _generate_request_id() -> str:
    """Generate a short request ID for tracing."""
    return str(uuid.uuid4())[:8]


# ============================================================================
# Routes
# ============================================================================


@router.post("/generate", response_model=ScheduleGenerationResponse)
async def generate_weekly_schedule(
    request: GenerateScheduleRequest,
) -> ScheduleGenerationResponse:
    """
    Generate a weekly content schedule for the given week.

    Creates 21 content_schedule rows, filling each slot with the
    best atom + angle combination based on anti-repetition rules.

    Args:
        request: Contains start_date (Monday) and force flag
    """
    request_id = _generate_request_id()

    logger.info(
        "[API] generate_schedule_start request_id=%s start_date=%s force=%s",
        request_id,
        request.start_date,
        request.force,
    )

    try:
        service = ScheduleGeneratorService()
        result = service.generate_weekly_schedule(
            start_date=request.start_date,
            force=request.force,
        )

        logger.info(
            "[API] generate_schedule_done request_id=%s trace_id=%s "
            "filled=%d/%d diversity=%.2f",
            request_id,
            result.trace_id,
            result.filled_slots,
            result.total_slots,
            result.diversity_score,
        )

        return ScheduleGenerationResponse(
            request_id=request_id,
            trace_id=result.trace_id,
            week_year=result.week_year,
            week_number=result.week_number,
            start_date=result.start_date,
            total_slots=result.total_slots,
            filled_slots=result.filled_slots,
            failed_slots=result.failed_slots,
            fallback_slots=result.fallback_slots,
            diversity_score=result.diversity_score,
            slot_results=[
                SlotFillResultItem(
                    slot_number=sr.slot_number,
                    success=sr.success,
                    atom_id=sr.atom_id,
                    angle_id=sr.angle_id,
                    score=sr.score,
                    fallback_used=sr.fallback_used,
                    error_message=sr.error_message,
                )
                for sr in result.slot_results
            ],
        )

    except ValueError as e:
        # Schedule already exists
        logger.warning(
            "[API] generate_schedule_conflict request_id=%s error=%s",
            request_id,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "schedule_exists",
                "message": str(e),
                "request_id": request_id,
            },
        )

    except Exception as e:
        logger.exception(
            "[API] generate_schedule_failed request_id=%s error_type=%s error=%s",
            request_id,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "generation_failed",
                "message": str(e),
                "request_id": request_id,
            },
        )


@router.get("/week/{week_year}/{week_number}", response_model=WeekScheduleResponse)
async def get_week_schedule(
    week_year: int,
    week_number: int = Path(..., ge=1, le=53, description="ISO week number (1-53)"),
) -> WeekScheduleResponse:
    """
    Get the content schedule for a specific week.

    Returns all 21 slots with their assignments (if any).

    Args:
        week_year: Year (e.g., 2026)
        week_number: ISO week number (1-53)
    """
    request_id = _generate_request_id()

    logger.info(
        "[API] get_week_schedule_start request_id=%s week=%d-%d",
        request_id,
        week_year,
        week_number,
    )

    try:
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            schedules = db_services.get_schedule_by_week(
                session=session,
                week_year=week_year,
                week_number=week_number,
            )

            schedule_items = [
                ContentScheduleItem(
                    id=s.id,
                    trace_id=s.trace_id,
                    week_year=s.week_year,
                    week_number=s.week_number,
                    slot_number=s.slot_number,
                    scheduled_date=s.scheduled_date,
                    scheduled_time=s.scheduled_time,
                    day_of_week=s.day_of_week,
                    required_pillar=s.required_pillar.value if hasattr(s.required_pillar, 'value') else s.required_pillar,
                    required_format=s.required_format.value if hasattr(s.required_format, 'value') else s.required_format,
                    atom_id=s.atom_id,
                    angle_id=s.angle_id,
                    status=s.status.value if hasattr(s.status, 'value') else s.status,
                    brief=s.brief or {},
                )
                for s in schedules
            ]

            filled = sum(1 for s in schedules if s.atom_id is not None)

        finally:
            next(session_gen, None)

        logger.info(
            "[API] get_week_schedule_done request_id=%s slots=%d filled=%d",
            request_id,
            len(schedule_items),
            filled,
        )

        return WeekScheduleResponse(
            request_id=request_id,
            week_year=week_year,
            week_number=week_number,
            total_slots=len(schedule_items),
            filled_slots=filled,
            schedules=schedule_items,
        )

    except Exception as e:
        logger.exception(
            "[API] get_week_schedule_failed request_id=%s error_type=%s error=%s",
            request_id,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "Error fetching schedule.",
                "request_id": request_id,
            },
        )


@router.get("/week/{week_year}/{week_number}/exists", response_model=ScheduleExistsResponse)
async def check_schedule_exists(
    week_year: int,
    week_number: int = Path(..., ge=1, le=53, description="ISO week number (1-53)"),
) -> ScheduleExistsResponse:
    """
    Check if a schedule exists for a specific week.

    Args:
        week_year: Year (e.g., 2026)
        week_number: ISO week number (1-53)
    """
    request_id = _generate_request_id()

    logger.info(
        "[API] check_schedule_exists_start request_id=%s week=%d-%d",
        request_id,
        week_year,
        week_number,
    )

    try:
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            exists = db_services.schedule_exists_for_week(
                session=session,
                week_year=week_year,
                week_number=week_number,
            )

            slot_count = 0
            if exists:
                schedules = db_services.get_schedule_by_week(
                    session=session,
                    week_year=week_year,
                    week_number=week_number,
                )
                slot_count = len(schedules)

        finally:
            next(session_gen, None)

        logger.info(
            "[API] check_schedule_exists_done request_id=%s exists=%s slots=%d",
            request_id,
            exists,
            slot_count,
        )

        return ScheduleExistsResponse(
            request_id=request_id,
            week_year=week_year,
            week_number=week_number,
            exists=exists,
            slot_count=slot_count,
        )

    except Exception as e:
        logger.exception(
            "[API] check_schedule_exists_failed request_id=%s error_type=%s error=%s",
            request_id,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "Error checking schedule existence.",
                "request_id": request_id,
            },
        )


@router.delete("/week/{week_year}/{week_number}", response_model=DeleteScheduleResponse)
async def delete_week_schedule(
    week_year: int,
    week_number: int = Path(..., ge=1, le=53, description="ISO week number (1-53)"),
) -> DeleteScheduleResponse:
    """
    Delete an entire weekly schedule.

    Removes all ContentSchedule rows for the week. GeneratedContent is
    cascade-deleted. UsageHistory.schedule_id is SET NULL (history preserved).

    Args:
        week_year: Year (e.g., 2026)
        week_number: ISO week number (1-53)
    """
    request_id = _generate_request_id()

    logger.info(
        "[API] delete_week_schedule_start request_id=%s week=%d-%d",
        request_id,
        week_year,
        week_number,
    )

    try:
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            deleted_count = db_services.delete_week_schedule(
                session=session,
                week_year=week_year,
                week_number=week_number,
            )
            session.commit()
        finally:
            next(session_gen, None)

        message = (
            f"Deleted {deleted_count} schedule(s) for week {week_year}-{week_number}"
            if deleted_count > 0
            else f"No schedules found for week {week_year}-{week_number}"
        )

        logger.info(
            "[API] delete_week_schedule_done request_id=%s deleted=%d",
            request_id,
            deleted_count,
        )

        return DeleteScheduleResponse(
            request_id=request_id,
            week_year=week_year,
            week_number=week_number,
            deleted_count=deleted_count,
            message=message,
        )

    except Exception as e:
        logger.exception(
            "[API] delete_week_schedule_failed request_id=%s error_type=%s error=%s",
            request_id,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "Error deleting schedule.",
                "request_id": request_id,
            },
        )


@router.post("/week/{week_year}/{week_number}/reset", response_model=ResetScheduleResponse)
async def reset_week_schedule(
    week_year: int,
    week_number: int = Path(..., ge=1, le=53, description="ISO week number (1-53)"),
) -> ResetScheduleResponse:
    """
    Reset a weekly schedule to SCHEDULED status for re-processing.

    Resets all ContentSchedule rows back to SCHEDULED status and deletes
    associated GeneratedContent so the creation pipeline can be re-run.

    NOTE: ContentAtom usage (times_used, last_used_at) is NOT reverted.

    Args:
        week_year: Year (e.g., 2026)
        week_number: ISO week number (1-53)
    """
    request_id = _generate_request_id()

    logger.info(
        "[API] reset_week_schedule_start request_id=%s week=%d-%d",
        request_id,
        week_year,
        week_number,
    )

    try:
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            reset_count, deleted_content_count = db_services.reset_week_schedule(
                session=session,
                week_year=week_year,
                week_number=week_number,
            )
            session.commit()
        finally:
            next(session_gen, None)

        message = (
            f"Reset {reset_count} schedule(s), deleted {deleted_content_count} generated content"
            if reset_count > 0 or deleted_content_count > 0
            else f"No schedules needed resetting for week {week_year}-{week_number}"
        )

        logger.info(
            "[API] reset_week_schedule_done request_id=%s reset=%d deleted_content=%d",
            request_id,
            reset_count,
            deleted_content_count,
        )

        return ResetScheduleResponse(
            request_id=request_id,
            week_year=week_year,
            week_number=week_number,
            reset_count=reset_count,
            deleted_generated_content_count=deleted_content_count,
            message=message,
        )

    except Exception as e:
        logger.exception(
            "[API] reset_week_schedule_failed request_id=%s error_type=%s error=%s",
            request_id,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "Error resetting schedule.",
                "request_id": request_id,
            },
        )
