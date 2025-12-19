"""
Ingestion DB Services.

Phase-scoped database operations for Phase 1 ingestion.
This module contains ALL database READ/WRITE logic for ingestion tables.

Tables managed:
- RawIngest
- RejectedContent

This service contains NO business logic - only database operations.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, cast

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, select

from app.db.db_models.ingestion import RawIngest, RejectedContent
from app.db.db_session import get_session
from app.db.enums import IngestStatus, RejectionPhase, SourceType

logger = logging.getLogger(__name__)


def get_pending_ingest_records(
    session: Session,
    limit: Optional[int] = None,
) -> List[RawIngest]:
    """
    Fetch all pending or processing ingest records.

    Args:
        session: SQLModel session
        limit: Optional limit on records returned

    Returns:
        List of RawIngest records with PENDING or PROCESSING status
    """
    statement = (
        select(RawIngest)
        .where(RawIngest.status.in_([IngestStatus.PENDING, IngestStatus.PROCESSING]))
        .order_by(RawIngest.ingested_at.desc())
    )

    if limit:
        statement = statement.limit(limit)

    return list(session.exec(statement).all())


def bulk_insert_raw_ingest(
    session: Session,
    records: List[dict],
    batch_id: uuid.UUID,
) -> tuple[int, int]:
    """
    Bulk insert RawIngest records with conflict handling.

    Uses INSERT ... ON CONFLICT DO NOTHING for deduplication.

    Args:
        session: SQLModel session
        records: List of dicts with RawIngest field data
        batch_id: Batch identifier for this ingestion run

    Returns:
        Tuple of (stored_count, skipped_count)
    """
    stored = 0
    skipped = 0

    for record in records:
        # Ensure batch_id is set
        record["batch_id"] = batch_id

        # Set default status if not provided
        if "status" not in record:
            record["status"] = IngestStatus.PENDING

        # Set ingested_at if not provided
        if "ingested_at" not in record:
            record["ingested_at"] = datetime.now(timezone.utc)

        stmt = insert(RawIngest).values(**record).on_conflict_do_nothing()
        result = session.exec(stmt)

        if result.rowcount and result.rowcount > 0:
            stored += 1
        else:
            skipped += 1

    return stored, skipped


def insert_raw_ingest(
    session: Session,
    source_type: SourceType,
    source_identifier: str,
    raw_content: str,
    batch_id: uuid.UUID,
    source_url: Optional[str] = None,
    raw_title: Optional[str] = None,
    raw_metadata: Optional[dict] = None,
) -> Optional[uuid.UUID]:
    """
    Insert a single RawIngest record with conflict handling.

    Args:
        session: SQLModel session
        source_type: Type of content source
        source_identifier: Unique identifier from source
        raw_content: Raw content text
        batch_id: Batch identifier
        source_url: Optional URL
        raw_title: Optional title
        raw_metadata: Optional metadata dict

    Returns:
        UUID of inserted record, or None if skipped (duplicate)
    """
    record = RawIngest(
        source_type=source_type,
        source_identifier=source_identifier,
        source_url=source_url,
        raw_title=raw_title,
        raw_content=raw_content,
        raw_metadata=raw_metadata or {},
        status=IngestStatus.PENDING,
        batch_id=batch_id,
        ingested_at=datetime.now(timezone.utc),
    )

    stmt = (
        insert(RawIngest)
        .values(**record.model_dump(exclude={"content_hash"}))
        .on_conflict_do_nothing()
    )
    result = session.exec(stmt)

    if result.rowcount and result.rowcount > 0:
        return record.id
    return None


def update_ingest_status(
    session: Session,
    ingest_id: uuid.UUID,
    status: IngestStatus,
    processed_at: Optional[datetime] = None,
) -> bool:
    """
    Update the status of an ingest record.

    Args:
        session: SQLModel session
        ingest_id: ID of the ingest record
        status: New status
        processed_at: Optional processed timestamp

    Returns:
        True if update succeeded, False if record not found
    """
    record = session.get(RawIngest, ingest_id)
    if not record:
        return False

    record.status = status
    if processed_at:
        record.processed_at = processed_at

    session.add(record)
    return True


def create_rejection_record(
    session: Session,
    trace_id: uuid.UUID,
    rejection_phase: RejectionPhase,
    rejection_reasons: dict,
    content_snapshot: dict,
    raw_ingest_id: Optional[uuid.UUID] = None,
    rejected_by: str = "system",
) -> uuid.UUID:
    """
    Create a rejection record.

    Args:
        session: SQLModel session
        trace_id: Trace ID for the rejected content
        rejection_phase: Phase where rejection occurred
        rejection_reasons: Structured rejection reasons
        content_snapshot: Snapshot of content at rejection time
        raw_ingest_id: Optional link to RawIngest record
        rejected_by: Who/what caused the rejection

    Returns:
        UUID of created rejection record
    """
    rejection = RejectedContent(
        trace_id=trace_id,
        raw_ingest_id=raw_ingest_id,
        rejection_phase=rejection_phase,
        rejection_reasons=rejection_reasons,
        content_snapshot=content_snapshot,
        rejected_at=datetime.now(timezone.utc),
        rejected_by=rejected_by,
    )

    session.add(rejection)
    return rejection.id


def get_ingest_by_batch(
    session: Session,
    batch_id: uuid.UUID,
) -> List[RawIngest]:
    """
    Fetch all ingest records for a specific batch.

    Args:
        session: SQLModel session
        batch_id: Batch identifier

    Returns:
        List of RawIngest records in the batch
    """
    statement = (
        select(RawIngest)
        .where(RawIngest.batch_id == batch_id)
        .order_by(RawIngest.ingested_at.desc())
    )
    return list(session.exec(statement).all())


def count_ingest_by_status(
    session: Session,
    status: IngestStatus,
) -> int:
    """
    Count ingest records by status.

    Args:
        session: SQLModel session
        status: Status to count

    Returns:
        Count of records with the given status
    """
    statement = select(RawIngest).where(RawIngest.status == status)
    return len(session.exec(statement).all())
