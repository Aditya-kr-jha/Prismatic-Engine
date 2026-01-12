# app/api/delivery_routes.py

"""
Delivery API Routes.

REST endpoints for Phase 5 delivery pipeline.

Routes must remain thin:
- No business logic
- No direct DB access
- No parsing
- Just orchestration
"""

import logging
import uuid
from typing import List, cast

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select, func

from app.db.db_models.strategy import ContentSchedule
from app.db.db_session import get_session
from app.db.enums import ScheduleStatus
from app.delivery.service import DeliveryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/delivery", tags=["Delivery"])


def _generate_request_id() -> str:
    """Generate a short request ID for tracing."""
    return str(uuid.uuid4())[:8]


class DeliveryRunRequest(BaseModel):
    """Request to run delivery for a week."""

    week_year: int = Field(..., ge=2020, le=2100, description="Year (e.g., 2026)")
    week_number: int = Field(..., ge=1, le=53, description="ISO week number")
    enable_telegram: bool = Field(default=True, description="Send via Telegram")
    enable_files: bool = Field(default=True, description="Export Markdown files")
    update_status: bool = Field(
        default=True, description="Update DB status to DELIVERED"
    )


class DeliveryRunResponse(BaseModel):
    """Response from delivery run."""

    request_id: str
    week_year: int
    week_number: int

    total_processed: int
    successful: int
    failed: int

    output_directory: str
    files_created: List[str]

    telegram_enabled: bool
    telegram_messages_sent: int
    telegram_errors: List[str]

    duration_seconds: float


class DeliveryStatusResponse(BaseModel):
    """Response for delivery status check."""

    request_id: str
    week_year: int
    week_number: int

    total_scheduled: int
    draft_count: int
    delivered_count: int
    pending_delivery: int


@router.post("/run", response_model=DeliveryRunResponse)
async def run_delivery(request: DeliveryRunRequest) -> DeliveryRunResponse:
    """
    Run delivery pipeline for a specific week.

    Transforms approved GeneratedContent into human-readable briefs
    and delivers via Markdown files and/or Telegram.
    """
    request_id = _generate_request_id()

    logger.info(
        "[API] delivery_run_start request_id=%s week=%d-W%d telegram=%s files=%s",
        request_id,
        request.week_year,
        request.week_number,
        request.enable_telegram,
        request.enable_files,
    )

    try:
        service = DeliveryService(
            enable_telegram=request.enable_telegram,
            enable_file_export=request.enable_files,
            update_status=request.update_status,
        )

        result = await service.deliver_week(
            week_year=request.week_year,
            week_number=request.week_number,
        )

        logger.info(
            "[API] delivery_run_done request_id=%s processed=%d files=%d telegram=%d duration=%.2fs",
            request_id,
            result.total_processed,
            len(result.files_created),
            result.telegram_messages_sent,
            result.duration_seconds,
        )

        return DeliveryRunResponse(
            request_id=request_id,
            week_year=result.week_year,
            week_number=result.week_number,
            total_processed=result.total_processed,
            successful=result.successful,
            failed=result.failed,
            output_directory=result.output_directory,
            files_created=result.files_created,
            telegram_enabled=result.telegram_enabled,
            telegram_messages_sent=result.telegram_messages_sent,
            telegram_errors=result.telegram_errors,
            duration_seconds=round(result.duration_seconds, 2),
        )

    except Exception as e:
        logger.exception("[API] delivery_run_error request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "delivery_failed",
                "message": str(e),
                "request_id": request_id,
            },
        )


@router.get("/status/{week_year}/{week_number}", response_model=DeliveryStatusResponse)
async def get_delivery_status(
    week_year: int,
    week_number: int = Path(..., ge=1, le=53, description="ISO week number (1-53)"),
) -> DeliveryStatusResponse:
    """
    Get delivery status for a specific week.

    Returns count of DELIVERED vs pending items.
    """
    request_id = _generate_request_id()

    logger.info(
        "[API] delivery_status_start request_id=%s week=%d-W%d",
        request_id,
        week_year,
        week_number,
    )

    try:
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            statement = (
                select(ContentSchedule.status, func.count(ContentSchedule.id))
                .where(ContentSchedule.week_year == week_year)
                .where(ContentSchedule.week_number == week_number)
                .group_by(ContentSchedule.status)
            )

            results = session.exec(statement).all()

            status_counts = {status_value: count for status_value, count in results}

            total_scheduled = sum(status_counts.values())
            draft_count = status_counts.get(ScheduleStatus.DRAFT, 0)
            delivered_count = status_counts.get(ScheduleStatus.DELIVERED, 0)
            pending_delivery = draft_count

        finally:
            next(session_gen, None)

        logger.info(
            "[API] delivery_status_done request_id=%s total=%d delivered=%d pending=%d",
            request_id,
            total_scheduled,
            delivered_count,
            pending_delivery,
        )

        return DeliveryStatusResponse(
            request_id=request_id,
            week_year=week_year,
            week_number=week_number,
            total_scheduled=total_scheduled,
            draft_count=draft_count,
            delivered_count=delivered_count,
            pending_delivery=pending_delivery,
        )

    except Exception as e:
        logger.exception("[API] delivery_status_error request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "status_check_failed",
                "message": str(e),
                "request_id": request_id,
            },
        )
