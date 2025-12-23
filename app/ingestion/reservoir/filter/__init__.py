"""Filter subpackage exports."""

from app.ingestion.reservoir.filter.hard_filter import HardFilter
from app.ingestion.reservoir.filter.signal_phrases import (
    ACADEMIC_SIGNALS,
    CONTRARIAN_SIGNALS,
    MEANING_SIGNALS,
    IMPLICIT_INSIGHT_MARKERS,
    ALL_SIGNAL_PATTERNS,
    META_STRUCTURAL_PATTERNS,
)

__all__ = [
    "HardFilter",
    "ACADEMIC_SIGNALS",
    "CONTRARIAN_SIGNALS",
    "MEANING_SIGNALS",
    "IMPLICIT_INSIGHT_MARKERS",
    "ALL_SIGNAL_PATTERNS",
    "META_STRUCTURAL_PATTERNS",
]
