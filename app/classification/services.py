"""
Classification Service (Orchestrator).

The ONLY entry point for Phase 3 classification logic.

This service:
- Fetches pending raw_ingest records
- Runs LLM classification with async concurrency
- Inserts content atoms
- Updates raw_ingest status

Execution model:
- Batch frequency: Once per week
- Rows per run: All (~100 rows)
- Concurrency: 3 parallel (reduced to stay within rate limits)
- Expected runtime: 1-5 min (with rate limiting)
- Rate limit handling: Exponential backoff with retries
"""

import asyncio
import logging
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, cast

from sqlmodel import Session

from app.classification import db_services
from app.classification.classifier import ContentClassifier
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
    retries: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def __str__(self) -> str:
        return (
            f"ClassificationResult(batch_id={self.batch_id}, "
            f"processed={self.processed}, atoms_created={self.atoms_created}, "
            f"retries={self.retries}, errors={len(self.errors)}, "
            f"duration={self.duration_seconds:.2f}s)"
        )


class ClassificationService:
    """
    Orchestrates Phase 3 classification operations.

    This is the ONLY entry point for classification logic. It coordinates:
    - ContentClassifier (LLM execution)
    - DB Services (data access)

    Includes built-in rate limiting with exponential backoff to handle
    OpenAI 429 errors gracefully.

    Usage:
        service = ClassificationService()
        result = await service.classify_batch()
    """

    # Reduced from 10 to 3 to stay within OpenAI's 30k TPM limit
    MAX_CONCURRENCY = 3

    # Rate limit retry configuration
    MAX_RETRIES = 5
    BASE_DELAY_SECONDS = 2.0
    MAX_DELAY_SECONDS = 60.0

    # Default source type distribution ratios
    # This ensures balanced classification across different content sources
    DEFAULT_SOURCE_RATIOS: Dict[str, float] = {
        "REDDIT": 0.50,  # 40% Reddit posts
        "BOOK": 0.20,  # 30% Book chunks
        "BLOG": 0.30,  # 30% Blog articles
    }

    def __init__(
        self,
        batch_id: Optional[uuid.UUID] = None,
        classifier: Optional[ContentClassifier] = None,
        source_ratios: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize the classification service.

        Args:
            batch_id: Optional batch identifier (auto-generated if not provided)
            classifier: Optional classifier instance (created if not provided)
            source_ratios: Optional dict mapping SourceType values to ratios (0.0-1.0)
                           Example: {"REDDIT": 0.4, "BOOK": 0.3, "BLOG": 0.3}
                           If None, uses DEFAULT_SOURCE_RATIOS
        """
        self.batch_id = batch_id or uuid.uuid4()
        self.classifier = classifier or ContentClassifier()
        self.source_ratios = source_ratios or self.DEFAULT_SOURCE_RATIOS

    async def classify_batch(
        self,
        limit: int = 100,
        use_source_ratios: bool = True,
    ) -> ClassificationResult:
        """
        Classify all pending raw_ingest records.

        Processes up to `limit` records with concurrent LLM calls.
        Uses source type ratios to ensure balanced distribution.

        Args:
            limit: Maximum rows to process
            use_source_ratios: If True, fetch records according to source_ratios.
                               If False, fetch records in order (legacy behavior).

        Returns:
            ClassificationResult with statistics
        """
        start = time.time()
        result = ClassificationResult(batch_id=self.batch_id)

        logger.info(
            "[CLASSIFY] batch_start batch_id=%s limit=%d use_ratios=%s ratios=%s",
            self.batch_id,
            limit,
            use_source_ratios,
            self.source_ratios if use_source_ratios else "N/A",
        )

        # Get session
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            # Step 1: Fetch pending records with source type distribution
            if use_source_ratios:
                pending_rows = db_services.get_pending_raw_ingest_by_source_ratio(
                    session,
                    source_ratios=self.source_ratios,
                    limit=limit,
                )
            else:
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
        Classify a single raw_ingest row with retry logic for rate limits.

        Args:
            session: SQLModel session
            row: RawIngest record to classify
            semaphore: Concurrency limiter
            result: Result object to update
        """
        async with semaphore:
            classification = None
            last_error = None

            for attempt in range(self.MAX_RETRIES):
                try:
                    # Run LLM classification
                    classification = await self.classifier.classify(
                        content=row.raw_content,
                        source_type=(
                            row.source_type.value if row.source_type else "UNKNOWN"
                        ),
                        title=row.raw_title,
                        source_url=row.source_url,
                    )
                    break  # Success, exit retry loop

                except Exception as e:
                    last_error = e
                    error_str = str(e)

                    # Check if this is a rate limit error (429)
                    if "429" in error_str or "rate_limit" in error_str.lower():
                        # Extract suggested retry time from error message
                        wait_time = self._extract_retry_time(error_str)

                        if wait_time is None:
                            # Use exponential backoff with jitter
                            wait_time = min(
                                self.BASE_DELAY_SECONDS * (2**attempt)
                                + random.uniform(0, 1),
                                self.MAX_DELAY_SECONDS,
                            )

                        logger.info(
                            "[CLASSIFY] rate_limited trace_id=%s attempt=%d/%d wait=%.2fs",
                            row.trace_id,
                            attempt + 1,
                            self.MAX_RETRIES,
                            wait_time,
                        )

                        result.retries += 1
                        await asyncio.sleep(wait_time)
                        continue

                    # Non-rate-limit error, don't retry
                    break

            # Process result
            if classification is not None:
                try:
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
                    return

                except Exception as db_error:
                    last_error = db_error
                    logger.warning(
                        "[CLASSIFY] db_insert_failed trace_id=%s error=%s",
                        row.trace_id,
                        str(db_error),
                    )

            # Classification failed after all retries
            logger.warning(
                "[CLASSIFY] row_failed trace_id=%s error=%s",
                row.trace_id,
                str(last_error) if last_error else "Unknown error",
            )

            # Mark as error
            db_services.mark_raw_ingest_processed(
                session=session,
                ingest_id=row.id,
                status=IngestStatus.ERROR,
            )

            result.processed += 1
            result.errors.append(f"trace_id={row.trace_id}: {str(last_error)}")

    def _extract_retry_time(self, error_message: str) -> Optional[float]:
        """
        Extract suggested retry time from OpenAI rate limit error message.

        Parses messages like 'Please try again in 2.5s' or 'try again in 500ms'.

        Args:
            error_message: The error message string

        Returns:
            Retry time in seconds, or None if not found
        """
        # Match patterns like "try again in 2.5s" or "try again in 500ms"
        patterns = [
            r"try again in (\d+\.?\d*)s",  # seconds
            r"try again in (\d+)ms",  # milliseconds
        ]

        for i, pattern in enumerate(patterns):
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if i == 1:  # milliseconds pattern
                    value = value / 1000.0
                # Add a small buffer to be safe
                return value + 0.5

        return None

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
