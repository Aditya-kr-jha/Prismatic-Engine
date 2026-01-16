"""
Classification API Routes.

REST endpoints for testing and triggering content classification operations.

Routes must remain thin:
- No business logic
- No direct DB access
- No parsing
- Just orchestration
"""

import logging
import time
import uuid
from typing import Any, Optional, cast

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session

from app.classification import db_services
from app.classification.services import ClassificationService
from app.db.db_session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/classification", tags=["Classification"])


# ============================================================================
# Response Schemas
# ============================================================================


class ContentAtomItem(BaseModel):
    """Response schema for a single ContentAtom."""

    id: uuid.UUID
    trace_id: uuid.UUID
    raw_ingest_id: Optional[uuid.UUID]
    primary_pillar: str
    secondary_pillars: list[str]
    format_fit: list[str]
    complexity_score: Optional[int]
    virality_score: float
    confidence_score: Optional[float]
    atomic_components: dict[str, Any]
    classification: dict[str, Any]

    class Config:
        from_attributes = True


class ClassifyBatchResponse(BaseModel):
    """Response schema for classification batch operation."""

    request_id: str
    batch_id: str
    processed: int
    atoms_created: int
    errors: list[str]
    duration_seconds: float
    atoms: list[ContentAtomItem]


class PendingCountResponse(BaseModel):
    """Response schema for pending count check."""

    request_id: str
    pending_count: int


# ============================================================================
# Helper Functions
# ============================================================================


def _generate_request_id() -> str:
    """Generate a short request ID for tracing."""
    return str(uuid.uuid4())[:8]


# ============================================================================
# Routes
# ============================================================================


@router.post("/classify", response_model=ClassifyBatchResponse)
async def classify_batch(
    limit: int = Query(
        default=30, ge=1, le=100, description="Number of rows to process (max 10)"
    ),
) -> ClassifyBatchResponse:
    """
    Classify pending raw_ingest records and create content atoms.

    Processes up to `limit` pending records through the LLM classifier
    and saves results to content_atoms table.

    Args:
        limit: Number of rows to process (1-100, default 30)
    """
    request_id = _generate_request_id()
    start_time = time.time()

    logger.info(
        "[API] classify_batch_start request_id=%s limit=%d",
        request_id,
        limit,
    )

    try:
        # Run classification service
        service = ClassificationService()
        result = await service.classify_batch(limit=limit)

        # Fetch created atoms for response
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            atoms = db_services.get_content_atoms_by_batch(session, result.batch_id)
            atom_items = [
                ContentAtomItem(
                    id=atom.id,
                    trace_id=atom.trace_id,
                    raw_ingest_id=atom.raw_ingest_id,
                    primary_pillar=atom.primary_pillar.value,
                    secondary_pillars=atom.secondary_pillars,
                    format_fit=atom.format_fit,
                    complexity_score=atom.complexity_score,
                    virality_score=atom.virality_score,
                    confidence_score=atom.confidence_score,
                    atomic_components=atom.atomic_components,
                    classification=atom.classification,
                )
                for atom in atoms
            ]
        finally:
            next(session_gen, None)

        duration = time.time() - start_time

        logger.info(
            "[API] classify_batch_done request_id=%s batch_id=%s duration=%.2fs "
            "processed=%d atoms=%d errors=%d",
            request_id,
            result.batch_id,
            duration,
            result.processed,
            result.atoms_created,
            len(result.errors),
        )

        return ClassifyBatchResponse(
            request_id=request_id,
            batch_id=str(result.batch_id),
            processed=result.processed,
            atoms_created=result.atoms_created,
            errors=result.errors,
            duration_seconds=round(duration, 2),
            atoms=atom_items,
        )

    except Exception as e:
        logger.exception(
            "[API] classify_batch_failed request_id=%s error_type=%s error=%s",
            request_id,
            type(e).__name__,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "classification_failed",
                "message": str(e),
                "request_id": request_id,
            },
        )


@router.get("/pending-count", response_model=PendingCountResponse)
async def get_pending_count() -> PendingCountResponse:
    """
    Get count of pending raw_ingest records awaiting classification.
    """
    request_id = _generate_request_id()

    logger.info("[API] pending_count_start request_id=%s", request_id)

    try:
        service = ClassificationService()
        count = service.get_pending_count()

        logger.info(
            "[API] pending_count_done request_id=%s count=%d",
            request_id,
            count,
        )

        return PendingCountResponse(
            request_id=request_id,
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
