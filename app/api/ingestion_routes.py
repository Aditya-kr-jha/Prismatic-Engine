"""
Ingestion API Routes.

REST endpoints for triggering content harvesting operations
from various sources (Reddit, etc.).

Routes must remain thin:
- No business logic
- No direct DB access
- No parsing
- Just orchestration
"""

import logging
import time
import uuid
from typing import Optional, cast

from fastapi import APIRouter, HTTPException, Request, status
from sqlmodel import Session

from app.api.schemas.ingestion import (
    HarvestResponse,
    PendingIngestResponse,
    RawIngestItem,
)
from app.db.db_session import get_session
from app.db.enums import ContentPillar
from app.infra.http import HTTPClientManager
from app.ingestion import db_services
from app.ingestion.service import IngestionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


def _generate_request_id() -> str:
    """Generate a short request ID for tracing."""
    return str(uuid.uuid4())[:8]


def _get_http_clients(request: Request, request_id: str) -> HTTPClientManager:
    """Get HTTP client manager from app state."""
    clients: Optional[HTTPClientManager] = getattr(request.app.state, "clients", None)

    if not clients or not clients.generic:
        logger.error("[API] http_clients_unavailable request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "service_unavailable",
                "message": "HTTP clients not initialized.",
                "request_id": request_id,
            },
        )

    return clients


@router.post("/reddit/harvest", response_model=HarvestResponse)
async def harvest_reddit(request: Request) -> HarvestResponse:
    """
    Harvest content from all configured Reddit subreddits.

    Triggers ingestion of top posts from all pillars.
    """
    request_id = _generate_request_id()
    start_time = time.time()

    logger.info("[API] harvest_all_start request_id=%s", request_id)
    clients = _get_http_clients(request, request_id)

    try:
        # Use the ingestion service for orchestration
        service = IngestionService(http_client=clients.generic)
        result = await service.ingest_reddit_all()

        duration = time.time() - start_time
        batch_id = str(service.batch_id)

        logger.info(
            "[API] harvest_all_done request_id=%s batch_id=%s duration=%.2fs fetched=%s stored=%s skipped=%s errors=%s",
            request_id,
            batch_id,
            duration,
            result.posts_fetched,
            result.posts_stored,
            result.posts_skipped,
            len(result.errors),
        )

        return HarvestResponse.from_result(
            posts_fetched=result.posts_fetched,
            posts_stored=result.posts_stored,
            posts_skipped=result.posts_skipped,
            errors=result.errors,
            duration_seconds=result.duration_seconds,
            batch_id=batch_id,
        )

    except Exception as e:
        logger.exception(
            "[API] harvest_all_failed request_id=%s error_type=%s error=%s",
            request_id,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Harvest failed.",
                "request_id": request_id,
            },
        )


@router.post("/reddit/harvest/{pillar}", response_model=HarvestResponse)
async def harvest_reddit_pillar(
    request: Request, pillar: ContentPillar
) -> HarvestResponse:
    """
    Harvest content from a specific Reddit content pillar.

    Args:
        pillar: The content pillar to harvest (e.g., PRODUCTIVITY, PHILOSOPHY)
    """
    request_id = _generate_request_id()
    start_time = time.time()

    logger.info(
        "[API] harvest_pillar_start request_id=%s pillar=%s", request_id, pillar.value
    )
    clients = _get_http_clients(request, request_id)

    try:
        # Use the ingestion service for orchestration
        service = IngestionService(http_client=clients.generic)
        result = await service.ingest_reddit_pillar(pillar)

        duration = time.time() - start_time
        batch_id = str(service.batch_id)

        logger.info(
            "[API] harvest_pillar_done request_id=%s batch_id=%s pillar=%s duration=%.2fs fetched=%s stored=%s skipped=%s errors=%s",
            request_id,
            batch_id,
            pillar.value,
            duration,
            result.posts_fetched,
            result.posts_stored,
            result.posts_skipped,
            len(result.errors),
        )

        return HarvestResponse.from_result(
            posts_fetched=result.posts_fetched,
            posts_stored=result.posts_stored,
            posts_skipped=result.posts_skipped,
            errors=result.errors,
            duration_seconds=result.duration_seconds,
            batch_id=batch_id,
        )

    except Exception as e:
        logger.exception(
            "[API] harvest_pillar_failed request_id=%s pillar=%s error_type=%s error=%s",
            request_id,
            pillar.value,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Pillar harvest failed.",
                "request_id": request_id,
                "pillar": pillar.value,
            },
        )


@router.get("/raw-ingest/pending", response_model=PendingIngestResponse)
async def get_pending_ingest_records() -> PendingIngestResponse:
    """
    Get all pending or processing ingest records.

    Returns records that are awaiting or currently undergoing processing.
    """
    request_id = _generate_request_id()
    start_time = time.time()

    logger.info("[API] pending_ingest_start request_id=%s", request_id)

    try:
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        # Use db_services for database access
        results = db_services.get_pending_ingest_records(session)
        records = [RawIngestItem.model_validate(r) for r in results]

        # Consume generator to trigger commit/close
        next(session_gen, None)

        duration = time.time() - start_time
        logger.info(
            "[API] pending_ingest_done request_id=%s duration=%.2fs record_count=%s",
            request_id,
            duration,
            len(records),
        )

        return PendingIngestResponse(
            request_id=request_id,
            total_count=len(records),
            records=records,
        )

    except Exception as e:
        logger.exception(
            "[API] pending_ingest_failed request_id=%s error_type=%s error=%s",
            request_id,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "database_error",
                "message": "Error fetching pending ingest records.",
                "request_id": request_id,
            },
        )
