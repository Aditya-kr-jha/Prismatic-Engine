import logging

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas.harvestors import HarvestResponse
from app.db.enums import ContentPillar
from app.services.clients import HTTPClientManager
from app.services.reddit_harvester import RedditHarvester

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.post("/reddit/harvest", response_model=HarvestResponse)
async def harvest_reddit(request: Request) -> HarvestResponse:
    """
    Trigger a full Reddit harvest across all content pillars.

    Fetches top weekly posts from 16 subreddits across 8 pillars,
    filters for quality, and stores to the raw_ingest table.

    This is a long-running operation (typically 1-3 minutes due to rate limiting).
    """
    clients: HTTPClientManager = request.app.state.clients

    if not clients or not clients.generic:
        raise HTTPException(
            status_code=503,
            detail="HTTP clients not initialized. Server may still be starting.",
        )

    logger.info("🔄 Starting full Reddit harvest via API...")
    harvester = RedditHarvester(http_client=clients.generic)
    result = await harvester.harvest_all()

    logger.info(f"✅ Reddit harvest complete: {result}")
    return HarvestResponse.from_result(result, str(harvester.batch_id))


@router.post("/reddit/harvest/{pillar}", response_model=HarvestResponse)
async def harvest_reddit_pillar(
    request: Request, pillar: ContentPillar
) -> HarvestResponse:
    """
    Trigger a Reddit harvest for a specific content pillar.

    Each pillar maps to 2 subreddits. This is useful for testing
    or targeted content refreshes.

    Args:
        pillar: Content pillar to harvest (e.g., 'productivity', 'philosophy')
    """
    clients: HTTPClientManager = request.app.state.clients

    if not clients or not clients.generic:
        raise HTTPException(
            status_code=503,
            detail="HTTP clients not initialized. Server may still be starting.",
        )

    logger.info(f"🔄 Starting Reddit harvest for pillar '{pillar.value}' via API...")
    harvester = RedditHarvester(http_client=clients.generic)
    result = await harvester.harvest_pillar(pillar)

    logger.info(f"✅ Pillar harvest complete: {result}")
    return HarvestResponse.from_result(result, str(harvester.batch_id))
