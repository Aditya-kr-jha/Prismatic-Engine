"""
Creation API Routes.

REST endpoints for Phase 5 content creation pipeline.

Routes must remain thin:
- No business logic
- No direct DB access
- No parsing
- Just orchestration
"""

import logging
import uuid
from typing import cast

from fastapi import APIRouter, HTTPException, Path, status
from sqlmodel import Session, select

from app.api.schemas.creation import (
    ContentScheduleBriefResponse,
    GeneratedContentDetailResponse,
    GeneratedContentItem,
    GeneratedContentListResponse,
    PendingScheduleCountResponse,
    PipelineResultResponse,
    RunPipelineRequest,
)
from app.creation import db_services
from app.creation.service import CreationService
from app.db.db_models.creation import GeneratedContent
from app.db.db_session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/creation", tags=["Creation"])


# ============================================================================
# Helper Functions
# ============================================================================


def _generate_request_id() -> str:
    """Generate a short request ID for tracing."""
    return str(uuid.uuid4())[:8]


# ============================================================================
# Routes
# ============================================================================


@router.post("/run", response_model=PipelineResultResponse)
async def run_creation_pipeline(
    request: RunPipelineRequest,
) -> PipelineResultResponse:
    """
    Run the full content creation pipeline for a week.

    Executes all 5 stages:
    - Stage 1: Analyze content briefs
    - Stage 2: Target emotional journey
    - Stage 3: Generate format-specific content
    - Stage 4: Self-critique and rewrite loop
    - Stage 5: Hard filters and storage

    Args:
        request: Contains week_year, week_number, limit, and dry_run flag
    """
    request_id = _generate_request_id()

    logger.info(
        "[API] run_pipeline_start request_id=%s week=%d-%d limit=%d dry_run=%s",
        request_id,
        request.week_year,
        request.week_number,
        request.limit,
        request.dry_run,
    )

    try:
        service = CreationService()
        result = await service.run_pipeline(
            week_year=request.week_year,
            week_number=request.week_number,
            limit=request.limit,
            dry_run=request.dry_run,
        )

        # Fetch the generated content from database
        generated_content_items: list[GeneratedContentItem] = []
        
        if not request.dry_run and result.successful > 0:
            session_gen = get_session()
            session = cast(Session, next(session_gen))
            
            try:
                # Get content IDs from successful items
                content_ids = [
                    uuid.UUID(item.stage5_result.generated_content_id)
                    for item in result.items
                    if item.stage5_result and item.stage5_result.generated_content_id
                ]
                
                if content_ids:
                    statement = select(GeneratedContent).where(
                        GeneratedContent.id.in_(content_ids)
                    )
                    results = session.exec(statement).all()
                    
                    generated_content_items = [
                        GeneratedContentItem(
                            id=gc.id,
                            schedule_id=gc.schedule_id,
                            trace_id=gc.trace_id,
                            format_type=gc.format_type.value if hasattr(gc.format_type, 'value') else gc.format_type,
                            content_json=gc.content_json,
                            resolved_mode=gc.resolved_mode,
                            emotional_journey=gc.emotional_journey,
                            critique_scores=gc.critique_scores,
                            generation_attempts=gc.generation_attempts,
                            status=gc.status.value if hasattr(gc.status, 'value') else gc.status,
                            flag_reasons=gc.flag_reasons or [],
                            generated_at=gc.generated_at,
                        )
                        for gc in results
                    ]
            finally:
                next(session_gen, None)

        logger.info(
            "[API] run_pipeline_done request_id=%s duration=%.2fs "
            "processed=%d successful=%d errors=%d content_returned=%d",
            request_id,
            result.duration_seconds,
            result.total_processed,
            result.successful,
            result.errors,
            len(generated_content_items),
        )

        return PipelineResultResponse(
            request_id=request_id,
            week_year=result.week_year,
            week_number=result.week_number,
            total_processed=result.total_processed,
            successful=result.successful,
            unsuitable=result.unsuitable,
            errors=result.errors,
            duration_seconds=round(result.duration_seconds, 2),
            generated_content=generated_content_items,
        )

    except Exception as e:
        logger.exception(
            "[API] run_pipeline_failed request_id=%s error_type=%s error=%s",
            request_id,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "pipeline_failed",
                "message": str(e),
                "request_id": request_id,
            },
        )


@router.get(
    "/pending-count/{week_year}/{week_number}",
    response_model=PendingScheduleCountResponse,
)
async def get_pending_schedule_count(
    week_year: int,
    week_number: int = Path(..., ge=1, le=53, description="ISO week number (1-53)"),
) -> PendingScheduleCountResponse:
    """
    Get count of pending scheduled content for a week.

    Returns the number of ContentSchedule rows with SCHEDULED status
    that are ready for creation processing.

    Args:
        week_year: Year (e.g., 2026)
        week_number: ISO week number (1-53)
    """
    request_id = _generate_request_id()

    logger.info(
        "[API] pending_count_start request_id=%s week=%d-%d",
        request_id,
        week_year,
        week_number,
    )

    try:
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            count = db_services.count_scheduled_for_week(
                session=session,
                week_year=week_year,
                week_number=week_number,
            )
        finally:
            next(session_gen, None)

        logger.info(
            "[API] pending_count_done request_id=%s count=%d",
            request_id,
            count,
        )

        return PendingScheduleCountResponse(
            request_id=request_id,
            week_year=week_year,
            week_number=week_number,
            pending_count=count,
        )

    except Exception as e:
        logger.exception(
            "[API] pending_count_failed request_id=%s error_type=%s error=%s",
            request_id,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "Error fetching pending count.",
                "request_id": request_id,
            },
        )


@router.get(
    "/generated/detail/{content_id}",
    response_model=GeneratedContentDetailResponse,
)
async def get_generated_content_by_id(
    content_id: uuid.UUID = Path(..., description="UUID of the GeneratedContent record"),
) -> GeneratedContentDetailResponse:
    """
    Get a specific generated content by its ID.

    Returns the full GeneratedContent record with all details.

    Args:
        content_id: UUID of the GeneratedContent record
    """
    request_id = _generate_request_id()

    logger.info(
        "[API] get_content_detail_start request_id=%s content_id=%s",
        request_id,
        content_id,
    )

    try:
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            gc = session.get(GeneratedContent, content_id)

            if gc is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "not_found",
                        "message": f"GeneratedContent with ID {content_id} not found.",
                        "request_id": request_id,
                    },
                )

            content_item = GeneratedContentItem(
                id=gc.id,
                schedule_id=gc.schedule_id,
                trace_id=gc.trace_id,
                format_type=gc.format_type.value if hasattr(gc.format_type, 'value') else gc.format_type,
                content_json=gc.content_json,
                resolved_mode=gc.resolved_mode,
                emotional_journey=gc.emotional_journey,
                critique_scores=gc.critique_scores,
                generation_attempts=gc.generation_attempts,
                status=gc.status.value if hasattr(gc.status, 'value') else gc.status,
                flag_reasons=gc.flag_reasons or [],
                generated_at=gc.generated_at,
            )

        finally:
            next(session_gen, None)

        logger.info(
            "[API] get_content_detail_done request_id=%s format=%s",
            request_id,
            content_item.format_type,
        )

        return GeneratedContentDetailResponse(
            request_id=request_id,
            content=content_item,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "[API] get_content_detail_failed request_id=%s error_type=%s error=%s",
            request_id,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "Error fetching content detail.",
                "request_id": request_id,
            },
        )


@router.get(
    "/generated/{week_year}/{week_number}",
    response_model=GeneratedContentListResponse,
)
async def get_generated_content_for_week(
    week_year: int,
    week_number: int = Path(..., ge=1, le=53, description="ISO week number (1-53)"),
) -> GeneratedContentListResponse:
    """
    Get all generated content for a specific week.

    Returns the list of GeneratedContent records created during
    pipeline execution for the specified week.

    Args:
        week_year: Year (e.g., 2026)
        week_number: ISO week number (1-53)
    """
    request_id = _generate_request_id()

    logger.info(
        "[API] get_generated_start request_id=%s week=%d-%d",
        request_id,
        week_year,
        week_number,
    )

    try:
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            # Query GeneratedContent via ContentSchedule relationship
            from app.db.db_models.strategy import ContentSchedule

            statement = (
                select(GeneratedContent)
                .join(ContentSchedule, GeneratedContent.schedule_id == ContentSchedule.id)
                .where(ContentSchedule.week_year == week_year)
                .where(ContentSchedule.week_number == week_number)
                .order_by(GeneratedContent.generated_at.desc())
            )

            results = session.exec(statement).all()

            content_items = [
                GeneratedContentItem(
                    id=gc.id,
                    schedule_id=gc.schedule_id,
                    trace_id=gc.trace_id,
                    format_type=gc.format_type.value if hasattr(gc.format_type, 'value') else gc.format_type,
                    content_json=gc.content_json,
                    resolved_mode=gc.resolved_mode,
                    emotional_journey=gc.emotional_journey,
                    critique_scores=gc.critique_scores,
                    generation_attempts=gc.generation_attempts,
                    status=gc.status.value if hasattr(gc.status, 'value') else gc.status,
                    flag_reasons=gc.flag_reasons or [],
                    generated_at=gc.generated_at,
                )
                for gc in results
            ]

        finally:
            next(session_gen, None)

        logger.info(
            "[API] get_generated_done request_id=%s count=%d",
            request_id,
            len(content_items),
        )

        return GeneratedContentListResponse(
            request_id=request_id,
            week_year=week_year,
            week_number=week_number,
            total_count=len(content_items),
            content=content_items,
        )

    except Exception as e:
        logger.exception(
            "[API] get_generated_failed request_id=%s error_type=%s error=%s",
            request_id,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "Error fetching generated content.",
                "request_id": request_id,
            },
        )


@router.get(
    "/brief/{content_id}",
    response_model=ContentScheduleBriefResponse,
)
async def get_content_schedule_brief(
    content_id: uuid.UUID = Path(..., description="UUID of the GeneratedContent record"),
) -> ContentScheduleBriefResponse:
    """
    Get the ContentSchedule brief used to generate a specific content.

    Returns the original brief JSON from the ContentSchedule that
    was used as input for the creation pipeline.

    Args:
        content_id: UUID of the GeneratedContent record
    """
    request_id = _generate_request_id()

    logger.info(
        "[API] get_brief_start request_id=%s content_id=%s",
        request_id,
        content_id,
    )

    try:
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            from app.db.db_models.strategy import ContentSchedule

            # First get the GeneratedContent to find the schedule_id
            gc = session.get(GeneratedContent, content_id)

            if gc is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "not_found",
                        "message": f"GeneratedContent with ID {content_id} not found.",
                        "request_id": request_id,
                    },
                )

            # Get the associated ContentSchedule
            schedule = session.get(ContentSchedule, gc.schedule_id)

            if schedule is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "not_found",
                        "message": f"ContentSchedule with ID {gc.schedule_id} not found.",
                        "request_id": request_id,
                    },
                )

            # Build response while session is still active
            response = ContentScheduleBriefResponse(
                request_id=request_id,
                generated_content_id=content_id,
                schedule_id=schedule.id,
                trace_id=schedule.trace_id,
                required_pillar=schedule.required_pillar.value if hasattr(schedule.required_pillar, 'value') else schedule.required_pillar,
                required_format=schedule.required_format.value if hasattr(schedule.required_format, 'value') else schedule.required_format,
                brief=schedule.brief or {},
            )

        finally:
            next(session_gen, None)

        logger.info(
            "[API] get_brief_done request_id=%s schedule_id=%s",
            request_id,
            response.schedule_id,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "[API] get_brief_failed request_id=%s error_type=%s error=%s",
            request_id,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "Error fetching content brief.",
                "request_id": request_id,
            },
        )
