"""
Reservoir Harvester.

Fetches available content from ContentReservoir for transfer to RawIngest.

This harvester:
- Fetches content from ContentReservoir with AVAILABLE status
- Applies quota-based selection (per-pillar and source type distribution)
- Returns structured data for storage

This harvester does NOT:
- Write to database
- Manage status transitions
"""

import logging
import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from sqlmodel import Session, select, func

from app.db.db_models.pre_ingestion import ContentReservoir
from app.db.enums import ContentPillar, EvergreenSourceType, ReservoirStatus
from app.ingestion.harvesters.reservoir_config import ReservoirHarvesterConfig

logger = logging.getLogger(__name__)


# ============================================================================
# Harvester Schemas
# ============================================================================


class ReservoirItem(BaseModel):
    """Represents a single item fetched from ContentReservoir."""

    id: uuid.UUID
    raw_text: str
    raw_title: Optional[str] = None
    chunk_index: int
    source_id: uuid.UUID
    source_type: EvergreenSourceType
    source_name: Optional[str] = None
    source_author: Optional[str] = None
    pillar: Optional[ContentPillar] = None


class ReservoirFetchResult(BaseModel):
    """Result from fetching content from reservoir."""

    batch_id: uuid.UUID
    items: List[ReservoirItem] = Field(default_factory=list)
    total_fetched: int = 0
    by_source_type: Dict[str, int] = Field(default_factory=dict)
    by_pillar: Dict[str, int] = Field(default_factory=dict)
    dry_run: bool = False


# ============================================================================
# Reservoir Harvester
# ============================================================================


class ReservoirHarvester:
    """
    Fetch available content from ContentReservoir.

    This harvester ONLY:
    - Queries ContentReservoir for AVAILABLE content
    - Applies quota-based selection
    - Returns structured Python data

    This harvester does NOT:
    - Write to database
    - Manage status transitions
    """

    def __init__(
        self,
        session: Session,
        config: Optional[ReservoirHarvesterConfig] = None,
        batch_id: Optional[uuid.UUID] = None,
    ):
        self.session = session
        self.config = config or ReservoirHarvesterConfig()
        self.batch_id = batch_id or uuid.uuid4()

    def fetch_by_config(self, dry_run: bool = False) -> ReservoirFetchResult:
        """
        Fetch content based on configured quotas.

        Args:
            dry_run: If True, just preview what would be fetched

        Returns:
            ReservoirFetchResult with selected items
        """
        result = ReservoirFetchResult(batch_id=self.batch_id, dry_run=dry_run)

        logger.info(
            "[RESERVOIR] fetch_start batch_id=%s total_target=%s dry_run=%s",
            self.batch_id,
            self.config.total_content,
            dry_run,
        )

        all_items: List[ReservoirItem] = []

        # Fetch by source type quotas
        for source_type, quota_pct in self.config.source_type_quotas.items():
            target_count = int(self.config.total_content * quota_pct)

            items = self._fetch_by_source_type(source_type, target_count)
            all_items.extend(items)

            result.by_source_type[source_type.value] = len(items)

            logger.info(
                "[RESERVOIR] source_type=%s target=%s fetched=%s",
                source_type.value,
                target_count,
                len(items),
            )

        result.items = all_items
        result.total_fetched = len(all_items)

        # Count by pillar (for stats)
        for item in all_items:
            if item.pillar:
                pillar_key = item.pillar.value
                result.by_pillar[pillar_key] = result.by_pillar.get(pillar_key, 0) + 1

        logger.info(
            "[RESERVOIR] fetch_done batch_id=%s total_fetched=%s by_type=%s",
            self.batch_id,
            result.total_fetched,
            result.by_source_type,
        )

        return result

    def _fetch_by_source_type(
        self,
        source_type: EvergreenSourceType,
        limit: int,
    ) -> List[ReservoirItem]:
        """Fetch available content of a specific source type."""

        # Query ContentReservoir with random ordering
        statement = (
            select(ContentReservoir)
            .where(
                ContentReservoir.status == ReservoirStatus.AVAILABLE,
                ContentReservoir.source_type == source_type.value,
            )
            .order_by(func.random())
            .limit(limit)
        )

        results = self.session.exec(statement).all()

        items = []
        for row in results:
            try:
                item = ReservoirItem(
                    id=row.id,
                    raw_text=row.raw_text,
                    raw_title=row.raw_title,
                    chunk_index=row.chunk_index,
                    source_id=row.source_id,
                    source_type=EvergreenSourceType(row.source_type),
                    source_name=row.source_name,
                    source_author=row.source_author,
                    pillar=self._infer_pillar_from_author(row.source_author),
                )
                items.append(item)
            except Exception as e:
                logger.warning(
                    "[RESERVOIR] parse_error id=%s error=%s",
                    row.id,
                    str(e),
                )

        return items

    def _infer_pillar_from_author(
        self, author: Optional[str]
    ) -> Optional[ContentPillar]:
        """
        Infer content pillar from author name.

        This is a placeholder - in a real implementation, you might:
        - Look up author->pillar mapping from config/DB
        - Use a heuristic based on source metadata
        """
        # For now, return None - pillar tracking can be added later
        # when author->pillar mapping is established
        return None

    def get_statistics(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics about available reservoir content.

        Returns:
            Dict with 'by_source_type' and 'by_status' counts
        """
        stats: Dict[str, Dict[str, int]] = {
            "by_source_type": {},
            "by_status": {},
        }

        # Count by source type
        stmt = (
            select(ContentReservoir.source_type, func.count())
            .where(ContentReservoir.status == ReservoirStatus.AVAILABLE)
            .group_by(ContentReservoir.source_type)
        )
        for row in self.session.exec(stmt):
            stats["by_source_type"][row[0] or "UNKNOWN"] = row[1]

        # Count by status
        stmt = select(ContentReservoir.status, func.count()).group_by(
            ContentReservoir.status
        )
        for row in self.session.exec(stmt):
            stats["by_status"][row[0].value if row[0] else "UNKNOWN"] = row[1]

        return stats
