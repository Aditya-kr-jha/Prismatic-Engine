"""
Classification DB Services.

Phase-scoped database operations for Phase 3 classification.
This module contains ALL database READ/WRITE logic for classification tables.

Tables managed:
- ContentAtom (write)
- RawIngest (read + status update)

This service contains NO business logic — only database operations.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, select

from app.db.db_models.classification import ContentAtom
from app.db.db_models.ingestion import RawIngest
from app.db.enums import IngestStatus, LifecycleState, VerificationStatus

logger = logging.getLogger(__name__)


def get_pending_raw_ingest(
    session: Session,
    limit: int = 100,
) -> List[RawIngest]:
    """
    Fetch pending raw_ingest records for classification.

    Args:
        session: SQLModel session
        limit: Maximum records to return

    Returns:
        List of RawIngest records with PENDING status
    """
    statement = (
        select(RawIngest)
        .where(RawIngest.status == IngestStatus.PENDING)
        .order_by(RawIngest.ingested_at.asc())
        .limit(limit)
    )
    return list(session.exec(statement).all())


def insert_content_atom(
    session: Session,
    raw_ingest: RawIngest,
    classification_result: Dict[str, Any],
    batch_id: uuid.UUID,
) -> uuid.UUID:
    """
    Insert a content atom from classification result.

    Args:
        session: SQLModel session
        raw_ingest: Source RawIngest record
        classification_result: Parsed LLM output
        batch_id: Batch identifier

    Returns:
        UUID of created ContentAtom
    """
    atoms = classification_result["atomic_components"]
    dims = classification_result["classification"]

    atom = ContentAtom(
        trace_id=raw_ingest.trace_id,
        raw_ingest_id=raw_ingest.id,
        raw_content=raw_ingest.raw_content,
        source_url=raw_ingest.source_url,
        source_type=raw_ingest.source_type,
        source_metadata={
            "raw_title": raw_ingest.raw_title,
            "raw_metadata": raw_ingest.raw_metadata,
            "batch_id": str(batch_id),
        },
        # Classification
        primary_pillar=dims["primary_pillar"],
        secondary_pillars=[p.value if hasattr(p, "value") else p for p in dims["secondary_pillars"]],
        format_fit=[f.value if hasattr(f, "value") else f for f in dims["format_fit"]],
        complexity_score=dims["complexity_score"],
        classification={
            "emotional_triggers": [t.value if hasattr(t, "value") else t for t in dims["emotional_triggers"]],
            "proof_type": dims["proof_type"].value if hasattr(dims["proof_type"], "value") else dims["proof_type"],
            "hook_mechanism": dims["hook_mechanism"].value if hasattr(dims["hook_mechanism"], "value") else dims["hook_mechanism"],
        },
        # Atomic components
        atomic_components={
            "core_concept": atoms["core_concept"],
            "emotional_hook": atoms["emotional_hook"],
            "supporting_evidence": atoms["supporting_evidence"],
            "actionable_insight": atoms["actionable_insight"],
            "quotable_snippet": atoms["quotable_snippet"],
        },
        # Performance
        virality_score=classification_result["virality_estimate"],
        confidence_score=classification_result["confidence"],
        # Lifecycle
        lifecycle_state=LifecycleState.ACTIVE,
        verification_status=VerificationStatus.UNVERIFIED,
        extracted_at=datetime.now(timezone.utc),
    )

    session.add(atom)
    session.flush()

    logger.debug(
        "Inserted ContentAtom id=%s trace_id=%s pillar=%s",
        atom.id,
        atom.trace_id,
        atom.primary_pillar.value,
    )

    return atom.id


def mark_raw_ingest_processed(
    session: Session,
    ingest_id: uuid.UUID,
    status: IngestStatus,
) -> bool:
    """
    Update raw_ingest status after classification.

    Args:
        session: SQLModel session
        ingest_id: ID of the ingest record
        status: New status (PASSED or ERROR)

    Returns:
        True if update succeeded, False if record not found
    """
    record = session.get(RawIngest, ingest_id)
    if not record:
        return False

    record.status = status
    record.processed_at = datetime.now(timezone.utc)
    session.add(record)

    return True


def count_pending_raw_ingest(session: Session) -> int:
    """
    Count pending raw_ingest records.

    Args:
        session: SQLModel session

    Returns:
        Count of PENDING records
    """
    statement = select(RawIngest).where(RawIngest.status == IngestStatus.PENDING)
    return len(session.exec(statement).all())


def get_content_atoms_by_batch(
    session: Session,
    batch_id: uuid.UUID,
) -> List[ContentAtom]:
    """
    Get content atoms created in a specific batch.

    Args:
        session: SQLModel session
        batch_id: Batch identifier

    Returns:
        List of ContentAtom records from the batch
    """
    statement = select(ContentAtom).where(
        ContentAtom.source_metadata["batch_id"].astext == str(batch_id)
    )
    return list(session.exec(statement).all())
