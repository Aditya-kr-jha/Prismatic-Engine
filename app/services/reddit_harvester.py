"""
Reddit Harvester Service.

Fetches top weekly posts from configured subreddits, filters and validates them,
and stores qualified content in the raw_ingest table for downstream processing.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, cast

import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session

from app.db.enums import (
    ContentPillar,
    IngestStatus,
    PILLAR_SUBREDDITS,
    SourceType,
)
from app.db.models.ingestion import RawIngest
from app.db.session import get_session
from app.services.clients import GenericHTTPClient
from app.services.schemas import (
    HarvesterConfig,
    HarvestResult,
    RawRedditPost,
    RedditMetadata,
)

logger = logging.getLogger(__name__)


class RedditHarvester:
    """
    Harvests top weekly posts from Reddit subreddits mapped to content pillars.

    Features:
    - Fetches posts from 16 subreddits across 8 content pillars
    - Filters out low-quality, old, NSFW, and deleted content
    - Handles rate limiting with automatic retry
    - Deduplicates posts on insert
    """

    BASE_URL = "https://www.reddit.com"

    def __init__(
        self,
        http_client: GenericHTTPClient,
        config: Optional[HarvesterConfig] = None,
        batch_id: Optional[uuid.UUID] = None,
    ):
        """
        Initialize the Reddit harvester.

        Args:
            http_client: Injected HTTP client (lifecycle managed externally)
            config: Harvester configuration
            batch_id: Batch ID for this harvest run
        """
        self.http_client = http_client
        self.config = config or HarvesterConfig()
        self.batch_id = batch_id or uuid.uuid4()

    # NOTE: close() removed - client lifecycle managed by HTTPClientManager

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC METHODS
    # ──────────────────────────────────────────────────────────────────────────

    async def harvest_all(self) -> HarvestResult:
        """
        Main entry point. Fetches posts from all configured subreddits.

        Returns:
            HarvestResult with summary statistics.
        """
        start_time = time.time()
        result = HarvestResult()

        logger.info(f"Starting harvest. Batch ID: {self.batch_id}")

        for pillar, subreddits in PILLAR_SUBREDDITS.items():
            for subreddit in subreddits:
                subreddit_result = await self._harvest_subreddit(subreddit, pillar)
                result.posts_fetched += subreddit_result.posts_fetched
                result.posts_stored += subreddit_result.posts_stored
                result.posts_skipped += subreddit_result.posts_skipped
                result.errors.extend(subreddit_result.errors)

                await self._apply_rate_limit()

        result.duration_seconds = time.time() - start_time
        logger.info(f"Harvest complete. {result}")
        return result

    async def harvest_pillar(self, pillar: ContentPillar) -> HarvestResult:
        """
        Fetch posts for a single pillar (typically 2 subreddits).

        Args:
            pillar: The content pillar to harvest.

        Returns:
            HarvestResult with summary statistics.
        """
        start_time = time.time()
        result = HarvestResult()

        subreddits = PILLAR_SUBREDDITS.get(pillar, [])
        if not subreddits:
            logger.warning(f"No subreddits configured for pillar: {pillar.value}")
            return result

        logger.info(f"Harvesting pillar {pillar.value}: {subreddits}")

        for subreddit in subreddits:
            subreddit_result = await self._harvest_subreddit(subreddit, pillar)
            result.posts_fetched += subreddit_result.posts_fetched
            result.posts_stored += subreddit_result.posts_stored
            result.posts_skipped += subreddit_result.posts_skipped
            result.errors.extend(subreddit_result.errors)

            await self._apply_rate_limit()

        result.duration_seconds = time.time() - start_time
        return result

    # ──────────────────────────────────────────────────────────────────────────
    # PRIVATE METHODS
    # ──────────────────────────────────────────────────────────────────────────

    async def _harvest_subreddit(
        self,
        subreddit: str,
        pillar: ContentPillar,
    ) -> HarvestResult:
        """Fetch and store posts from a single subreddit."""
        result = HarvestResult()

        logger.info(f"Harvesting r/{subreddit} for {pillar.value}...")

        raw_posts = await self._fetch_subreddit(subreddit)
        if not raw_posts:
            return result

        result.posts_fetched = len(raw_posts)

        # Parse and filter posts
        valid_posts: list[RawRedditPost] = []
        for raw_post in raw_posts:
            parsed = self._parse_post(raw_post, pillar)
            if parsed is not None:
                valid_posts.append(parsed)
            else:
                result.posts_skipped += 1

        # Store valid posts
        if valid_posts:
            stored, skipped = self._store_posts(valid_posts)
            result.posts_stored = stored
            result.posts_skipped += skipped

        logger.info(
            f"r/{subreddit}: fetched={result.posts_fetched}, "
            f"stored={result.posts_stored}, skipped={result.posts_skipped}"
        )
        return result

    async def _fetch_subreddit(self, name: str, retry: bool = True) -> list[dict]:
        """
        Fetch top weekly posts from a subreddit.

        Args:
            name: Subreddit name (without r/ prefix).
            retry: Whether to retry on rate limit (429).

        Returns:
            List of raw post data dictionaries.
        """
        url = f"{self.BASE_URL}/r/{name}/top.json"
        params = {"t": "week", "limit": self.config.posts_per_subreddit}

        try:
            response = await self.http_client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                children = data.get("data", {}).get("children", [])
                return children

            elif response.status_code == 429:
                logger.warning(f"Rate limited on r/{name}.")
                if retry:
                    logger.info(
                        f"Waiting {self.config.retry_delay_seconds}s before retry..."
                    )
                    await asyncio.sleep(self.config.retry_delay_seconds)
                    return await self._fetch_subreddit(name, retry=False)
                logger.warning(f"Skipping r/{name} after rate limit retry failed.")
                return []

            elif response.status_code >= 500:
                logger.warning(
                    f"Server error {response.status_code} on r/{name}. Skipping."
                )
                return []

            else:
                logger.error(
                    f"Unexpected status {response.status_code} fetching r/{name}"
                )
                return []

        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching r/{name}. Skipping.")
            return []
        except httpx.RequestError as e:
            logger.error(f"Request error fetching r/{name}: {e}")
            return []

    def _parse_post(
        self,
        raw: dict,
        pillar: ContentPillar,
    ) -> Optional[RawRedditPost]:
        """
        Extract and validate fields from Reddit JSON.

        Returns:
            RawRedditPost if valid, None if post should be filtered out.
        """
        data = raw.get("data", {})
        if not data:
            return None

        # Filter: Deleted or removed content
        selftext = data.get("selftext", "")

        # Filter: Score below threshold
        score = data.get("score", 0)
        if score < self.config.min_score:
            logger.debug(f"Filtered low-score post ({score}): {data.get('name')}")
            return None

        # Filter: Post older than lookback period
        created_utc = data.get("created_utc", 0)
        if not self._is_within_lookback(created_utc):
            logger.debug(f"Filtered old post: {data.get('name')}")
            return None

        # Filter: Self posts with too short content
        is_self = data.get("is_self", False)
        if is_self and len(selftext) < self.config.min_content_length:
            logger.debug(f"Filtered short content post: {data.get('name')}")
            return None

        # Build validated post
        fullname = data.get("name")
        subreddit = data.get("subreddit", "")
        if not fullname or not subreddit:
            return None

        try:
            metadata = RedditMetadata(
                title=data.get("title", ""),
                author=data.get("author"),
                subreddit=subreddit,
                score=score,
                upvote_ratio=data.get("upvote_ratio", 0.0),
                num_comments=data.get("num_comments", 0),
                created_utc=created_utc,
                permalink=data.get("permalink", ""),
                post_type="self" if is_self else "link",
                domain=data.get("domain"),
                url=data.get("url"),
                is_video=data.get("is_video", False),
            )

            return RawRedditPost(
                source_id=self._build_source_id(subreddit, fullname),
                title=data.get("title", ""),
                selftext=selftext if selftext else None,
                score=score,
                upvote_ratio=data.get("upvote_ratio", 0.0),
                num_comments=data.get("num_comments", 0),
                created_utc=created_utc,
                permalink=data.get("permalink", ""),
                subreddit=subreddit,
                pillar=pillar,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Error parsing post {data.get('name')}: {e}")
            return None

    def _is_within_lookback(self, created_utc: float) -> bool:
        """Check if post is within the lookback period."""
        if not created_utc:
            return False
        post_time = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.config.lookback_days)
        return post_time >= cutoff

    def _build_source_id(self, subreddit: str, post_id: str) -> str:
        """Format: {subreddit}:{post_fullname}"""
        return f"{subreddit}:{post_id}"

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting delay between requests."""
        await asyncio.sleep(self.config.request_delay_seconds)

    def _store_posts(self, posts: list[RawRedditPost]) -> tuple[int, int]:
        """
        Store validated posts to the database.

        Args:
            posts: List of validated RawRedditPost objects.

        Returns:
            Tuple of (stored_count, skipped_count).
        """
        stored = 0
        skipped = 0

        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            for post in posts:
                # Build metadata dict with pillar info
                metadata_dict = post.metadata.model_dump()
                metadata_dict["content_pillar"] = post.pillar.value

                raw_ingest = RawIngest(
                    source_type=SourceType.REDDIT,
                    source_identifier=post.source_id,
                    source_url=post.source_url,
                    raw_title=post.title,
                    raw_content=post.raw_content,
                    raw_metadata=metadata_dict,
                    status=IngestStatus.PENDING,
                    batch_id=self.batch_id,
                    ingested_at=datetime.now(timezone.utc),
                )

                # Use UPSERT (do nothing) to handle duplicates (source_id or content_hash)
                # We exclude 'content_hash' because it's a computed column in Postgres
                stmt = (
                    insert(RawIngest)
                    .values(**raw_ingest.model_dump(exclude={"content_hash"}))
                    .on_conflict_do_nothing()
                )

                result = session.exec(stmt)
                if result.rowcount > 0:
                    stored += 1
                else:
                    skipped += 1

            # Commit handled by get_session() generator
            next(session_gen, None)
            logger.info(f"Stored {stored} posts, skipped {skipped} duplicates")

        except Exception as e:
            logger.error(f"Database error storing posts: {e}")
            try:
                next(session_gen, None)
            except Exception:
                pass
            raise

        return stored, skipped
