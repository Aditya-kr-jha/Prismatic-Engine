"""
Reservoir Harvester Configuration.

Pydantic configuration for harvesting content from ContentReservoir
to RawIngest with configurable quotas.
"""

from typing import Dict

from pydantic import BaseModel

from app.db.enums import ContentPillar, EvergreenSourceType


class ReservoirHarvesterConfig(BaseModel):
    """
    Configuration for reservoir content harvesting.

    Attributes:
        pillar_quotas: Minimum items to harvest per content pillar
        source_type_quotas: Distribution percentages by source type
    """

    pillar_quotas: Dict[ContentPillar, int] = {
        ContentPillar.PRODUCTIVITY: 3,
        ContentPillar.DARK_PSYCHOLOGY: 3,
        ContentPillar.RELATIONSHIPS: 5,
        ContentPillar.NEUROSCIENCE: 3,
        ContentPillar.PHILOSOPHY: 3,
        ContentPillar.HEALING_GROWTH: 3,
        ContentPillar.SELF_CARE: 3,
        ContentPillar.SELF_WORTH: 3,
    }

    source_type_quotas: Dict[EvergreenSourceType, float] = {
        EvergreenSourceType.YOUTUBE: 0.3,
        EvergreenSourceType.BLOG: 0.4,
        EvergreenSourceType.BOOK: 0.3,
    }

    @property
    def total_content(self) -> int:
        """Total content to harvest, computed from pillar quotas."""
        return sum(self.pillar_quotas.values())

    class Config:
        frozen = True
