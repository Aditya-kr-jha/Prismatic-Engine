"""
Classification Service (Orchestrator).

The ONLY entry point for Phase 3 classification logic.

This service:
- Fetches pending raw_ingest records
- Runs LLM classification with async concurrency (10 parallel)
- Inserts content atoms
- Updates raw_ingest status

Execution model:
- Batch frequency: Once per week
- Rows per run: All (~100 rows)
- Concurrency: 10 parallel (asyncio + semaphore)
- Expected runtime: 30s - 2min
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, cast

from sqlmodel import Session

from app.classification import db_services
from app.classification.classifier import ContentClassifier
from app.classification.schemas import ClassificationOutput
from app.db.db_models.ingestion import RawIngest
from app.db.db_session import get_session
from app.db.enums import IngestStatus

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result from a classification batch operation."""

    batch_id: uuid.UUID
    processed: int = 0
    atoms_created: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def __str__(self) -> str:
        return (
            f"ClassificationResult(batch_id={self.batch_id}, "
            f"processed={self.processed}, atoms_created={self.atoms_created}, "
            f"errors={len(self.errors)}, duration={self.duration_seconds:.2f}s)"
        )


class ClassificationService:
    """
    Orchestrates Phase 3 classification operations.

    This is the ONLY entry point for classification logic. It coordinates:
    - ContentClassifier (LLM execution)
    - DB Services (data access)

    Usage:
        service = ClassificationService()
        result = await service.classify_batch()
    """

    MAX_CONCURRENCY = 10

    def __init__(
        self,
        batch_id: Optional[uuid.UUID] = None,
        classifier: Optional[ContentClassifier] = None,
    ):
        """
        Initialize the classification service.

        Args:
            batch_id: Optional batch identifier (auto-generated if not provided)
            classifier: Optional classifier instance (created if not provided)
        """
        self.batch_id = batch_id or uuid.uuid4()
        self.classifier = classifier or ContentClassifier()

    async def classify_batch(
        self,
        limit: int = 100,
    ) -> ClassificationResult:
        """
        Classify all pending raw_ingest records.

        Processes up to `limit` records with 10 concurrent LLM calls.

        Args:
            limit: Maximum rows to process

        Returns:
            ClassificationResult with statistics
        """
        start = time.time()
        result = ClassificationResult(batch_id=self.batch_id)

        logger.info(
            "[CLASSIFY] batch_start batch_id=%s limit=%d",
            self.batch_id,
            limit,
        )

        # Get session
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            # Step 1: Fetch pending records
            pending_rows = db_services.get_pending_raw_ingest(session, limit=limit)

            if not pending_rows:
                logger.info("[CLASSIFY] no_pending_rows batch_id=%s", self.batch_id)
                result.duration_seconds = time.time() - start
                return result

            logger.info(
                "[CLASSIFY] fetched_rows batch_id=%s count=%d",
                self.batch_id,
                len(pending_rows),
            )

            # Step 2: Process with concurrency control
            semaphore = asyncio.Semaphore(self.MAX_CONCURRENCY)
            tasks = [
                self._classify_one(session, row, semaphore, result)
                for row in pending_rows
            ]
            await asyncio.gather(*tasks)

            # Step 3: Commit transaction
            next(session_gen, None)

            result.duration_seconds = time.time() - start
            logger.info(
                "[CLASSIFY] batch_done batch_id=%s duration=%.2fs processed=%d atoms=%d errors=%d",
                self.batch_id,
                result.duration_seconds,
                result.processed,
                result.atoms_created,
                len(result.errors),
            )

        except Exception as e:
            logger.exception("[CLASSIFY] batch_failed batch_id=%s", self.batch_id)
            result.errors.append(f"Batch failed: {str(e)}")
            raise

        finally:
            try:
                next(session_gen, None)
            except Exception:
                pass

        return result

    async def _classify_one(
        self,
        session: Session,
        row: RawIngest,
        semaphore: asyncio.Semaphore,
        result: ClassificationResult,
    ) -> None:
        """
        Classify a single raw_ingest row.

        Args:
            session: SQLModel session
            row: RawIngest record to classify
            semaphore: Concurrency limiter
            result: Result object to update
        """
        async with semaphore:
            try:
                # Run LLM classification
                classification = await self.classifier.classify(
                    content=row.raw_content,
                    source_type=row.source_type.value if row.source_type else "UNKNOWN",
                    title=row.raw_title,
                    source_url=row.source_url,
                )

                # Convert Pydantic model to dict for DB insertion
                classification_dict = classification.model_dump()

                # Insert content atom
                db_services.insert_content_atom(
                    session=session,
                    raw_ingest=row,
                    classification_result=classification_dict,
                    batch_id=self.batch_id,
                )

                # Mark raw_ingest as processed
                db_services.mark_raw_ingest_processed(
                    session=session,
                    ingest_id=row.id,
                    status=IngestStatus.PASSED,
                )

                result.processed += 1
                result.atoms_created += 1

                logger.debug(
                    "[CLASSIFY] row_done trace_id=%s pillar=%s virality=%.1f",
                    row.trace_id,
                    classification.classification.primary_pillar.value,
                    classification.virality_estimate,
                )

            except Exception as e:
                logger.warning(
                    "[CLASSIFY] row_failed trace_id=%s error=%s",
                    row.trace_id,
                    str(e),
                )

                # Mark as error
                db_services.mark_raw_ingest_processed(
                    session=session,
                    ingest_id=row.id,
                    status=IngestStatus.ERROR,
                )

                result.processed += 1
                result.errors.append(f"trace_id={row.trace_id}: {str(e)}")

    def get_pending_count(self) -> int:
        """
        Get count of pending raw_ingest records.

        Returns:
            Number of PENDING records
        """
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            count = db_services.count_pending_raw_ingest(session)
        finally:
            try:
                next(session_gen, None)
            except Exception:
                pass

        return count
