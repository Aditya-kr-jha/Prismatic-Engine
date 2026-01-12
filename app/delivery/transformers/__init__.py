"""
Transformer factory for delivery briefs.
"""

from typing import Dict, Type

from app.delivery.transformers.base import BaseBriefTransformer
from app.delivery.transformers.reel_transformer import ReelTransformer
from app.delivery.transformers.carousel_transformer import CarouselTransformer
from app.delivery.transformers.quote_transformer import QuoteTransformer


TRANSFORMER_MAP: Dict[str, Type[BaseBriefTransformer]] = {
    "REEL": ReelTransformer,
    "CAROUSEL": CarouselTransformer,
    "QUOTE": QuoteTransformer,
}


def get_transformer(format_type: str) -> BaseBriefTransformer:
    """
    Get the appropriate transformer for a format type.

    Args:
        format_type: REEL, CAROUSEL, or QUOTE

    Returns:
        Instantiated transformer

    Raises:
        ValueError: If format_type is unknown
    """
    transformer_class = TRANSFORMER_MAP.get(format_type.upper())
    if not transformer_class:
        raise ValueError(f"Unknown format type: {format_type}")
    return transformer_class()


__all__ = [
    "BaseBriefTransformer",
    "ReelTransformer",
    "CarouselTransformer",
    "QuoteTransformer",
    "get_transformer",
]
