"""
Ingestion Service (Orchestrator).

The ONLY entry point for Phase 1 ingestion logic.

This service:
- Coordinates harvesters
- Calls validators
- Calls ingestion db_services
- Manages batch_id and trace_id

This service replaces any DB access previously done inside harvesters.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, cast

from sqlmodel import Session

from app.db.db_models.ingestion import RawIngest
from app.db.db_session import get_session
from app.db.enums import ContentPillar, IngestStatus, SourceType
from app.infra.http.generic import GenericHTTPClient
from app.ingestion import db_services
from app.ingestion.harvesters.reddit import (
    RedditHarvester,
    HarvestFetchResult,
    RawRedditPost,
    HarvesterConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result from an ingestion operation."""

    batch_id: uuid.UUID
    posts_fetched: int = 0
    posts_stored: int = 0
    posts_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def __str__(self) -> str:
        return (
            f"IngestionResult(batch_id={self.batch_id}, fetched={self.posts_fetched}, "
            f"stored={self.posts_stored}, skipped={self.posts_skipped}, "
            f"errors={len(self.errors)}, duration={self.duration_seconds:.2f}s)"
        )


class IngestionService:
    """
    Orchestrates Phase 1 ingestion operations.

    This is the ONLY entry point for ingestion logic. It coordinates:
    - Harvesters (fetch external data)
    - Validators (validate content)
    - DB Services (store data)

    Usage:
        service = IngestionService(http_client=clients.generic)
        result = await service.ingest_reddit_all()
    """

    def __init__(
        self,
        http_client: GenericHTTPClient,
        batch_id: Optional[uuid.UUID] = None,
        trace_id: Optional[uuid.UUID] = None,
    ):
        self.http_client = http_client
        self.batch_id = batch_id or uuid.uuid4()
        self.trace_id = trace_id or uuid.uuid4()

    async def ingest_reddit_all(
        self,
        config: Optional[HarvesterConfig] = None,
    ) -> IngestionResult:
        """
        Ingest content from all configured Reddit subreddits.

        Args:
            config: Optional harvester configuration

        Returns:
            IngestionResult with statistics
        """
        start = time.time()
        result = IngestionResult(batch_id=self.batch_id)

        logger.info(
            "[INGEST] reddit_all_start batch_id=%s trace_id=%s",
            self.batch_id,
            self.trace_id,
        )

        # Step 1: Fetch and parse from Reddit
        harvester = RedditHarvester(
            http_client=self.http_client,
            config=config,
            batch_id=self.batch_id,
        )
        fetch_result = await harvester.fetch_all()

        result.posts_fetched = fetch_result.total_fetched
        result.posts_skipped = fetch_result.total_skipped
        result.errors.extend(fetch_result.errors)

        # Step 2: Get all parsed posts
        parsed_posts = harvester.get_all_parsed_posts(fetch_result)

        if not parsed_posts:
            logger.info("[INGEST] no_posts_to_store batch_id=%s", self.batch_id)
            result.duration_seconds = time.time() - start
            return result

        # Step 3: Store posts in database
        stored, skipped = self._store_posts(parsed_posts)
        result.posts_stored = stored
        result.posts_skipped += skipped

        result.duration_seconds = time.time() - start
        logger.info(
            "[INGEST] reddit_all_done batch_id=%s duration=%.2fs fetched=%s stored=%s skipped=%s errors=%s",
            self.batch_id,
            result.duration_seconds,
            result.posts_fetched,
            result.posts_stored,
            result.posts_skipped,
            len(result.errors),
        )

        return result

    async def ingest_reddit_pillar(
        self,
        pillar: ContentPillar,
        config: Optional[HarvesterConfig] = None,
    ) -> IngestionResult:
        """
        Ingest content from a specific Reddit pillar.

        Args:
            pillar: The content pillar to ingest
            config: Optional harvester configuration

        Returns:
            IngestionResult with statistics
        """
        start = time.time()
        result = IngestionResult(batch_id=self.batch_id)

        logger.info(
            "[INGEST] reddit_pillar_start batch_id=%s trace_id=%s pillar=%s",
            self.batch_id,
            self.trace_id,
            pillar.value,
        )

        # Step 1: Fetch and parse from Reddit
        harvester = RedditHarvester(
            http_client=self.http_client,
            config=config,
            batch_id=self.batch_id,
        )
        fetch_result = await harvester.fetch_pillar(pillar)

        result.posts_fetched = fetch_result.total_fetched
        result.posts_skipped = fetch_result.total_skipped
        result.errors.extend(fetch_result.errors)

        # Step 2: Get all parsed posts
        parsed_posts = harvester.get_all_parsed_posts(fetch_result)

        if not parsed_posts:
            logger.info(
                "[INGEST] no_posts_to_store batch_id=%s pillar=%s",
                self.batch_id,
                pillar.value,
            )
            result.duration_seconds = time.time() - start
            return result

        # Step 3: Store posts in database
        stored, skipped = self._store_posts(parsed_posts)
        result.posts_stored = stored
        result.posts_skipped += skipped

        result.duration_seconds = time.time() - start
        logger.info(
            "[INGEST] reddit_pillar_done batch_id=%s pillar=%s duration=%.2fs fetched=%s stored=%s skipped=%s errors=%s",
            self.batch_id,
            pillar.value,
            result.duration_seconds,
            result.posts_fetched,
            result.posts_stored,
            result.posts_skipped,
            len(result.errors),
        )

        return result

    def _store_posts(self, posts: List[RawRedditPost]) -> tuple[int, int]:
        """
        Store parsed posts in the database.

        Args:
            posts: List of parsed Reddit posts

        Returns:
            Tuple of (stored_count, skipped_count)
        """
        stored = 0
        skipped = 0
        start = time.time()

        logger.info("[STORE] start batch_id=%s posts=%s", self.batch_id, len(posts))

        # Convert posts to record dicts
        records = []
        for post in posts:
            metadata = post.metadata.model_dump()
            metadata["content_pillar"] = post.pillar.value

            record = {
                "source_type": SourceType.REDDIT,
                "source_identifier": post.source_id,
                "source_url": post.source_url,
                "raw_title": post.title,
                "raw_content": post.raw_content,
                "raw_metadata": metadata,
                "status": IngestStatus.PENDING,
                "ingested_at": datetime.now(timezone.utc),
            }
            records.append(record)

        # Use session and db_services for storage
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            stored, skipped = db_services.bulk_insert_raw_ingest(
                session=session,
                records=records,
                batch_id=self.batch_id,
            )

            # Consume generator to trigger commit
            next(session_gen, None)

        except Exception:
            logger.exception("[STORE] failed batch_id=%s", self.batch_id)
            raise

        finally:
            # Ensure generator finalizer runs
            try:
                next(session_gen, None)
            except Exception:
                pass

        logger.info(
            "[STORE] done batch_id=%s duration=%.2fs stored=%s skipped=%s",
            self.batch_id,
            time.time() - start,
            stored,
            skipped,
        )

        return stored, skipped
