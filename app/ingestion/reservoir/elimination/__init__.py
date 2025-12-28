"""
Elimination Gate for Book Source Pipeline.

4-stage elite filter to reduce LLM-validated chunks to Instagram-viral content:
  Stage A: Hard Signal Detection (binary elimination)
  Stage B: Multi-Axis Scoring (PUNCH/IDENTITY/TENSION/QUOTABILITY/NOVELTY)
  Stage C: Competitive Ranking (top chunks per axis)
  Stage D: Quota Enforcement (20-30 elite chunks)
"""

from app.ingestion.reservoir.elimination.signals import (
    has_viral_surface,
    EMOTIONAL_WORDS,
    EXPLAINER_STARTERS,
    ANTI_PATTERNS,
)
from app.ingestion.reservoir.elimination.scoring import (
    score_punch,
    score_identity,
    score_tension,
    score_quotability,
    AxisScorer,
)
from app.ingestion.reservoir.elimination.embeddings import NoveltyScorer
from app.ingestion.reservoir.elimination.ranking import EliteFilter

__all__ = [
    # Stage A
    "has_viral_surface",
    "EMOTIONAL_WORDS",
    "EXPLAINER_STARTERS",
    "ANTI_PATTERNS",
    # Stage B
    "score_punch",
    "score_identity",
    "score_tension",
    "score_quotability",
    "AxisScorer",
    # Novelty
    "NoveltyScorer",
    # Stage C+D
    "EliteFilter",
]
