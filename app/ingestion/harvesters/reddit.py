"""
Reddit Harvester.

Fetches top posts from configured subreddits, filters and validates them,
and returns structured data for storage.

This harvester:
- Fetches data from Reddit
- Parses posts into Python dicts
- Performs NO database writes
- Performs NO ingestion status transitions
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator

from app.db.enums import ContentPillar, PILLAR_SUBREDDITS
from app.infra.http.generic import GenericHTTPClient

logger = logging.getLogger(__name__)


# ============================================================================
# Harvester Schemas (internal to harvester)
# ============================================================================


class RedditMetadata(BaseModel):
    """Nested model for raw_metadata JSONB storage."""

    title: str
    author: Optional[str] = None
    subreddit: str
    score: int
    upvote_ratio: float
    num_comments: int
    created_utc: float
    permalink: str
    post_type: str = Field(description="'self' for text posts, 'link' for links")
    domain: Optional[str] = None
    url: Optional[str] = None
    is_video: bool = False


class RawRedditPost(BaseModel):
    """Pydantic model for parsed and validated Reddit post data."""

    source_id: str = Field(description="Format: {subreddit}:{post_fullname}")
    title: str
    selftext: Optional[str] = None
    score: int = Field(ge=0)
    upvote_ratio: float = Field(ge=0.0, le=1.0)
    num_comments: int = Field(ge=0)
    created_utc: float
    permalink: str
    subreddit: str
    pillar: ContentPillar
    metadata: RedditMetadata

    @field_validator("source_id")
    @classmethod
    def validate_source_id_format(cls, v: str) -> str:
        """Ensure source_id follows {subreddit}:{post_fullname} format."""
        if ":" not in v:
            raise ValueError("source_id must be in format {subreddit}:{post_fullname}")
        return v

    @property
    def raw_content(self) -> str:
        """Combined content for storage."""
        if self.selftext:
            return f"{self.title}\n\n{self.selftext}"
        return self.title

    @property
    def source_url(self) -> str:
        """Full Reddit URL for the post."""
        return f"https://reddit.com{self.permalink}"


class HarvesterConfig(BaseModel):
    """Configuration for the Reddit harvester."""

    posts_per_subreddit: int = 2
    lookback_days: int = 1
    request_delay_seconds: float = 2.0
    min_score: int = 10
    min_content_length: int = 300
    timeout_seconds: float = 30.0
    retry_delay_seconds: float = 60.0
    user_agent: str = "PrismaticEngine/1.0 (content research)"

    class Config:
        frozen = True


class SubredditFetchResult(BaseModel):
    """Result from fetching a single subreddit."""

    subreddit: str
    pillar: ContentPillar
    raw_posts: List[dict] = Field(default_factory=list)
    parsed_posts: List[RawRedditPost] = Field(default_factory=list)
    posts_fetched: int = 0
    posts_parsed: int = 0
    posts_skipped: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0


class HarvestFetchResult(BaseModel):
    """Result from the fetch phase of harvesting (no DB operations)."""

    batch_id: uuid.UUID
    subreddit_results: List[SubredditFetchResult] = Field(default_factory=list)
    total_fetched: int = 0
    total_parsed: int = 0
    total_skipped: int = 0
    errors: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


# ============================================================================
# Reddit Harvester
# ============================================================================


class RedditHarvester:
    """
    Fetch and parse top posts from Reddit.

    This harvester ONLY:
    - Calls Reddit API
    - Parses responses
    - Returns structured Python data

    This harvester does NOT:
    - Write to database
    - Manage ingestion status
    - Perform business logic beyond parsing
    """

    BASE_URL = "https://www.reddit.com"

    def __init__(
        self,
        http_client: GenericHTTPClient,
        config: Optional[HarvesterConfig] = None,
        batch_id: Optional[uuid.UUID] = None,
    ):
        self.http_client = http_client
        self.config = config or HarvesterConfig()
        self.batch_id = batch_id or uuid.uuid4()

    async def fetch_all(self) -> HarvestFetchResult:
        """
        Fetch and parse posts from all configured subreddits.

        Returns:
            HarvestFetchResult with all parsed posts and statistics
        """
        start = time.time()
        result = HarvestFetchResult(batch_id=self.batch_id)

        total_pillars = len(PILLAR_SUBREDDITS)
        total_subreddits = sum(len(subs) for subs in PILLAR_SUBREDDITS.values())

        logger.info(
            "[HARVEST] fetch_start batch_id=%s pillars=%s subreddits=%s",
            self.batch_id,
            total_pillars,
            total_subreddits,
        )

        for pillar, subreddits in PILLAR_SUBREDDITS.items():
            for subreddit in subreddits:
                try:
                    sr_result = await self._fetch_subreddit(subreddit, pillar)
                    result.subreddit_results.append(sr_result)
                    result.total_fetched += sr_result.posts_fetched
                    result.total_parsed += sr_result.posts_parsed
                    result.total_skipped += sr_result.posts_skipped
                    if sr_result.error:
                        result.errors.append(sr_result.error)
                except Exception as e:
                    msg = f"r/{subreddit} failed: {type(e).__name__}: {e}"
                    logger.exception("[HARVEST] subreddit_error %s", msg)
                    result.errors.append(msg)

                await self._apply_rate_limit()

        result.duration_seconds = time.time() - start
        logger.info(
            "[HARVEST] fetch_done batch_id=%s duration=%.2fs fetched=%s parsed=%s skipped=%s errors=%s",
            self.batch_id,
            result.duration_seconds,
            result.total_fetched,
            result.total_parsed,
            result.total_skipped,
            len(result.errors),
        )
        return result

    async def fetch_pillar(self, pillar: ContentPillar) -> HarvestFetchResult:
        """
        Fetch and parse posts from subreddits in a specific pillar.

        Args:
            pillar: The content pillar to fetch

        Returns:
            HarvestFetchResult with parsed posts from the pillar
        """
        start = time.time()
        result = HarvestFetchResult(batch_id=self.batch_id)

        subreddits = PILLAR_SUBREDDITS.get(pillar, [])
        logger.info(
            "[HARVEST] pillar_fetch_start batch_id=%s pillar=%s subreddits=%s",
            self.batch_id,
            pillar.value,
            subreddits,
        )

        for subreddit in subreddits:
            try:
                sr_result = await self._fetch_subreddit(subreddit, pillar)
                result.subreddit_results.append(sr_result)
                result.total_fetched += sr_result.posts_fetched
                result.total_parsed += sr_result.posts_parsed
                result.total_skipped += sr_result.posts_skipped
                if sr_result.error:
                    result.errors.append(sr_result.error)
            except Exception as e:
                msg = f"r/{subreddit} failed: {type(e).__name__}: {e}"
                logger.exception("[HARVEST] pillar_subreddit_error %s", msg)
                result.errors.append(msg)

            await self._apply_rate_limit()

        result.duration_seconds = time.time() - start
        logger.info(
            "[HARVEST] pillar_fetch_done batch_id=%s pillar=%s duration=%.2fs fetched=%s parsed=%s skipped=%s errors=%s",
            self.batch_id,
            pillar.value,
            result.duration_seconds,
            result.total_fetched,
            result.total_parsed,
            result.total_skipped,
            len(result.errors),
        )
        return result

    async def _fetch_subreddit(
        self,
        subreddit: str,
        pillar: ContentPillar,
    ) -> SubredditFetchResult:
        """Fetch and parse posts from a single subreddit."""
        start = time.time()
        result = SubredditFetchResult(subreddit=subreddit, pillar=pillar)

        logger.info("[SUBREDDIT] fetch_start r/%s pillar=%s", subreddit, pillar.value)

        raw_posts = await self._fetch_reddit_api(subreddit)
        result.raw_posts = raw_posts
        result.posts_fetched = len(raw_posts)

        if not raw_posts:
            logger.info("[SUBREDDIT] empty r/%s", subreddit)
            result.duration_seconds = time.time() - start
            return result

        for raw in raw_posts:
            parsed = self._parse_post(raw, pillar)
            if parsed is None:
                result.posts_skipped += 1
                continue
            result.parsed_posts.append(parsed)
            result.posts_parsed += 1

        logger.info(
            "[SUBREDDIT] fetch_done r/%s duration=%.2fs fetched=%s parsed=%s skipped=%s",
            subreddit,
            time.time() - start,
            result.posts_fetched,
            result.posts_parsed,
            result.posts_skipped,
        )

        result.duration_seconds = time.time() - start
        return result

    async def _fetch_reddit_api(self, name: str, retry: bool = True) -> List[dict]:
        """Fetch posts from Reddit API."""
        url = f"{self.BASE_URL}/r/{name}/top.json"
        params = {"t": "day", "limit": self.config.posts_per_subreddit}

        logger.info("[FETCH] r/%s", name)
        resp = await self.http_client.get(url, params=params)

        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", {}).get("children", [])

        if resp.status_code == 429 and retry:
            retry_after = resp.headers.get("Retry-After")
            wait = (
                int(retry_after)
                if retry_after and str(retry_after).isdigit()
                else int(self.config.retry_delay_seconds)
            )
            logger.warning("[FETCH] rate_limited r/%s wait=%ss", name, wait)
            await asyncio.sleep(wait)
            return await self._fetch_reddit_api(name, retry=False)

        logger.warning("[FETCH] non_200 r/%s status=%s", name, resp.status_code)
        return []

    def _parse_post(self, raw: dict, pillar: ContentPillar) -> Optional[RawRedditPost]:
        """Parse a single raw post into structured format."""
        data = raw.get("data") or {}

        # Filters (quietly skip)
        if not data:
            return None
        if not data.get("is_self", False):
            return None

        selftext = data.get("selftext") or ""
        if selftext in ("[removed]", "[deleted]"):
            return None

        score = int(data.get("score") or 0)
        if score < self.config.min_score:
            return None

        created_utc = float(data.get("created_utc") or 0)
        if not self._is_within_lookback(created_utc):
            return None

        if len(selftext) < self.config.min_content_length:
            return None

        fullname = data.get("name")
        subreddit = data.get("subreddit")
        if not fullname or not subreddit:
            return None

        try:
            metadata = RedditMetadata(
                title=data.get("title", ""),
                author=data.get("author"),
                subreddit=subreddit,
                score=score,
                upvote_ratio=float(data.get("upvote_ratio") or 0.0),
                num_comments=int(data.get("num_comments") or 0),
                created_utc=created_utc,
                permalink=data.get("permalink", ""),
                post_type="self",
                domain=data.get("domain"),
                url=data.get("url"),
                is_video=bool(data.get("is_video") or False),
            )

            return RawRedditPost(
                source_id=self._build_source_id(subreddit, fullname),
                title=data.get("title", ""),
                selftext=selftext or None,
                score=score,
                upvote_ratio=metadata.upvote_ratio,
                num_comments=metadata.num_comments,
                created_utc=created_utc,
                permalink=metadata.permalink,
                subreddit=subreddit,
                pillar=pillar,
                metadata=metadata,
            )
        except Exception as e:
            post_id = data.get("name", "unknown")
            logger.debug(
                "[PARSE] skip post_id=%s reason=%s: %s",
                post_id,
                type(e).__name__,
                e,
            )
            return None

    def _is_within_lookback(self, created_utc: float) -> bool:
        """Check if post is within the lookback window."""
        if not created_utc:
            return False
        post_time = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.config.lookback_days)
        return post_time >= cutoff

    def _build_source_id(self, subreddit: str, post_id: str) -> str:
        """Build unique source identifier."""
        return f"{subreddit}:{post_id}"

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        await asyncio.sleep(self.config.request_delay_seconds)

    def get_all_parsed_posts(
        self,
        fetch_result: HarvestFetchResult,
    ) -> List[RawRedditPost]:
        """
        Extract all parsed posts from a fetch result.

        Args:
            fetch_result: The result from fetch_all or fetch_pillar

        Returns:
            Flat list of all parsed posts
        """
        posts = []
        for sr_result in fetch_result.subreddit_results:
            posts.extend(sr_result.parsed_posts)
        return posts
