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
from typing import Optional, List, Dict, cast

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

    # ========================================================================
    # Reservoir Harvesting Methods
    # ========================================================================

    def harvest_from_reservoir(
        self,
        total_content: Optional[int] = None,
        dry_run: bool = False,
    ) -> "ReservoirHarvestResult":
        """
        Harvest content from ContentReservoir to RawIngest.
        
        Orchestrates the full flow:
        1. Fetch available content based on quotas
        2. Mark as QUEUED (if not dry_run)
        3. Transfer to RawIngest (if not dry_run)
        
        Args:
            total_content: Override total items to harvest (uses config default)
            dry_run: If True, preview changes without DB modifications
            
        Returns:
            ReservoirHarvestResult with statistics
        """
        from app.ingestion.harvesters.reservoir import ReservoirHarvester
        from app.ingestion.harvesters.reservoir_config import ReservoirHarvesterConfig
        
        start = time.time()
        result = ReservoirHarvestResult(batch_id=self.batch_id, dry_run=dry_run)
        
        logger.info(
            "[RESERVOIR_HARVEST] start batch_id=%s trace_id=%s dry_run=%s",
            self.batch_id,
            self.trace_id,
            dry_run,
        )
        
        # Build config with optional override
        config = ReservoirHarvesterConfig()
        if total_content:
            # Create custom pillar quotas scaled to total_content
            scale = total_content / config.total_content
            config = ReservoirHarvesterConfig(
                pillar_quotas={
                    pillar: max(1, int(quota * scale))
                    for pillar, quota in config.pillar_quotas.items()
                }
            )
        
        # Get session
        session_gen = get_session()
        session = cast(Session, next(session_gen))
        
        try:
            # Step 1: Fetch using harvester
            harvester = ReservoirHarvester(
                session=session,
                config=config,
                batch_id=self.batch_id,
            )
            fetch_result = harvester.fetch_by_config(dry_run=dry_run)
            
            result.items_fetched = fetch_result.total_fetched
            result.by_source_type = fetch_result.by_source_type
            
            if dry_run:
                logger.info(
                    "[RESERVOIR_HARVEST] dry_run complete, would fetch %s items",
                    result.items_fetched,
                )
                result.duration_seconds = time.time() - start
                return result
            
            if not fetch_result.items:
                logger.info("[RESERVOIR_HARVEST] no items to transfer")
                result.duration_seconds = time.time() - start
                return result
            
            # Step 2: Mark as QUEUED
            content_ids = [item.id for item in fetch_result.items]
            queued = db_services.mark_reservoir_content_as_queued(session, content_ids)
            result.items_queued = queued
            
            # Step 3: Transfer to RawIngest
            inserted, skipped = db_services.transfer_reservoir_to_raw_ingest(
                session=session,
                content_ids=content_ids,
                batch_id=self.batch_id,
            )
            result.items_transferred = inserted
            result.items_skipped = skipped
            
            # Commit transaction
            next(session_gen, None)
            
            result.duration_seconds = time.time() - start
            logger.info(
                "[RESERVOIR_HARVEST] done batch_id=%s duration=%.2fs fetched=%s queued=%s transferred=%s skipped=%s",
                self.batch_id,
                result.duration_seconds,
                result.items_fetched,
                result.items_queued,
                result.items_transferred,
                result.items_skipped,
            )
            
        except Exception as e:
            logger.exception("[RESERVOIR_HARVEST] failed batch_id=%s", self.batch_id)
            result.error = str(e)
            raise
            
        finally:
            try:
                next(session_gen, None)
            except Exception:
                pass
        
        return result

    def get_reservoir_statistics(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics about available reservoir content.
        
        Returns:
            Dict with 'by_source_type' and 'by_status' counts
        """
        from app.ingestion.harvesters.reservoir import ReservoirHarvester
        
        session_gen = get_session()
        session = cast(Session, next(session_gen))
        
        try:
            harvester = ReservoirHarvester(session=session)
            stats = harvester.get_statistics()
        finally:
            try:
                next(session_gen, None)
            except Exception:
                pass
        
        return stats


@dataclass
class ReservoirHarvestResult:
    """Result from a reservoir harvest operation."""
    
    batch_id: uuid.UUID
    items_fetched: int = 0
    items_queued: int = 0
    items_transferred: int = 0
    items_skipped: int = 0
    by_source_type: Dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0.0
    dry_run: bool = False
    error: Optional[str] = None
    
    def __str__(self) -> str:
        return (
            f"ReservoirHarvestResult(batch_id={self.batch_id}, "
            f"fetched={self.items_fetched}, queued={self.items_queued}, "
            f"transferred={self.items_transferred}, skipped={self.items_skipped}, "
            f"dry_run={self.dry_run}, duration={self.duration_seconds:.2f}s)"
        )
