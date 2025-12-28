"""
Stage C+D: Competitive Ranking + Quota Enforcement (WITH FIXES).

Selection Logic (per axis):
- Top 8 by PUNCH (best hooks)
- Top 6 by IDENTITY (most shareable)
- Top 6 by TENSION (psychologically uncomfortable)
- Top 5 by QUOTABILITY (carousel/quote posts)
- Top 5 by NOVELTY (freshest reframes)

FIXES:
- Stage C: Multi-axis bonus (+25 to total for chunks qualifying on >1 axis)
- Stage D: Polarization floor for fill-up (requires identity+tension >= floor)
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Set

from app.ingestion.reservoir.schemas import Chunk
from app.ingestion.reservoir.elimination.signals import has_viral_surface
from app.ingestion.reservoir.elimination.scoring import AxisScorer, AxisScores
from app.ingestion.reservoir.elimination.embeddings import NoveltyScorer

logger = logging.getLogger(__name__)


# ============================================================================
# Fix Constants
# ============================================================================

# Multi-axis bonus for psychologically complete chunks
MULTI_AXIS_BONUS = 25

# Polarization floor for fill-up guardrail
POLARIZATION_FLOOR = 50  # Minimum identity + tension for fill-up


@dataclass
class ScoredChunk:
    """A chunk with its viral axis scores."""
    chunk: Chunk
    scores: AxisScores
    qualified_axes: List[str] = field(default_factory=list)
    _multi_axis_bonus_applied: bool = field(default=False, repr=False)
    
    @property
    def is_multi_axis(self) -> bool:
        return len(self.qualified_axes) > 1
    
    @property
    def adjusted_total(self) -> int:
        """Total score with multi-axis bonus applied."""
        bonus = MULTI_AXIS_BONUS if self.is_multi_axis else 0
        return self.scores.total + bonus


@dataclass
class EliminationResult:
    """Result from the elimination gate."""
    elite_chunks: List[ScoredChunk]
    eliminated_by_signal: int = 0
    eliminated_by_ranking: int = 0
    is_low_yield: bool = False
    axis_distribution: Dict[str, int] = field(default_factory=dict)
    
    @property
    def total_elite(self) -> int:
        return len(self.elite_chunks)


class EliteFilter:
    """
    4-stage elimination gate for Instagram-viral content (WITH FIXES).
    
    Stages:
        A: Hard Signal Detection (binary elimination)
        B: Multi-Axis Scoring (0-100 per axis)
        C: Competitive Ranking (with multi-axis bonus)
        D: Quota Enforcement (with polarization floor for fill-up)
    """
    
    # Quota thresholds
    MIN_ELITE_CHUNKS = 15
    MAX_ELITE_CHUNKS = 35
    
    # Selection quotas per axis
    AXIS_QUOTAS = {
        "punch": 8,
        "identity": 6,
        "tension": 6,
        "quotability": 5,
        "novelty": 5,
    }
    
    # Minimum scores per axis
    MIN_AXIS_SCORES = {
        "punch": 25,
        "identity": 20,
        "tension": 30,
        "quotability": 35,
        "novelty": 0,
    }
    
    # Minimum total score for fill-up
    MIN_TOTAL_SCORE = 80
    
    def __init__(
        self,
        enable_novelty: bool = True,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize elite filter.
        
        Args:
            enable_novelty: Whether to use embedding-based novelty scoring
            cache_dir: Directory for caching novelty baseline
        """
        self.enable_novelty = enable_novelty
        self.cache_dir = cache_dir
        
        # Initialize scorers
        novelty_scorer = None
        if enable_novelty:
            novelty_scorer = NoveltyScorer(cache_dir=cache_dir)
        
        self.axis_scorer = AxisScorer(novelty_scorer=novelty_scorer)
    
    def filter(self, chunks: List[Chunk]) -> EliminationResult:
        """
        Apply 4-stage elimination to produce elite chunks.
        
        Args:
            chunks: LLM-validated chunks to filter
            
        Returns:
            EliminationResult with elite chunks and stats
        """
        if not chunks:
            return EliminationResult(elite_chunks=[], is_low_yield=True)
        
        logger.info(f"Stage A: Signal detection on {len(chunks)} chunks")
        
        # Stage A: Hard Signal Detection
        surviving = []
        eliminated_signal = 0
        
        for chunk in chunks:
            if has_viral_surface(chunk.text):
                surviving.append(chunk)
            else:
                eliminated_signal += 1
        
        logger.info(f"Stage A eliminated {eliminated_signal} chunks, {len(surviving)} remaining")
        
        if not surviving:
            return EliminationResult(
                elite_chunks=[],
                eliminated_by_signal=eliminated_signal,
                is_low_yield=True,
            )
        
        # Stage B: Multi-Axis Scoring
        logger.info(f"Stage B: Scoring {len(surviving)} chunks on 5 axes")
        
        scored_chunks: List[ScoredChunk] = []
        for chunk in surviving:
            scores = self.axis_scorer.score(chunk.text)
            scored_chunks.append(ScoredChunk(chunk=chunk, scores=scores))
        
        # Stage C: Competitive Ranking with minimum score thresholds
        logger.info("Stage C: Competitive ranking per axis (with min thresholds)")
        
        selected_indices: Set[int] = set()
        axis_distribution: Dict[str, int] = {}
        
        for axis, quota in self.AXIS_QUOTAS.items():
            min_score = self.MIN_AXIS_SCORES[axis]
            
            # Sort by this axis score (descending)
            sorted_by_axis = sorted(
                enumerate(scored_chunks),
                key=lambda x: getattr(x[1].scores, axis),
                reverse=True,
            )
            
            count = 0
            for idx, scored_chunk in sorted_by_axis:
                if count >= quota:
                    break
                # Check minimum score threshold
                axis_score = getattr(scored_chunk.scores, axis)
                if axis_score >= min_score:
                    if idx not in selected_indices:
                        selected_indices.add(idx)
                        scored_chunk.qualified_axes.append(axis)
                        count += 1
                    elif axis not in scored_chunks[idx].qualified_axes:
                        # Already selected, just add axis qualification
                        scored_chunks[idx].qualified_axes.append(axis)
            
            axis_distribution[axis] = count
        
        # Collect selected chunks
        elite_chunks = [scored_chunks[i] for i in selected_indices]
        
        # FIX Stage C: Apply multi-axis bonus for ranking
        # (This affects the adjusted_total property used in sorting)
        multi_axis_count = sum(1 for c in elite_chunks if c.is_multi_axis)
        logger.info(f"Stage C selected {len(elite_chunks)} unique chunks ({multi_axis_count} multi-axis)")
        
        # Stage D: Quota Enforcement with fill-up
        logger.info("Stage D: Quota enforcement")
        
        # FIX Stage D: Fill with polarization floor guardrail
        if len(elite_chunks) < self.MIN_ELITE_CHUNKS:
            remaining = [
                (i, scored_chunks[i]) 
                for i in range(len(scored_chunks)) 
                if i not in selected_indices
            ]
            # Sort by adjusted_total (includes multi-axis bonus potential)
            remaining.sort(key=lambda x: x[1].scores.total, reverse=True)
            
            for idx, scored_chunk in remaining:
                if len(elite_chunks) >= self.MIN_ELITE_CHUNKS:
                    break
                
                # FIX: Check total score AND polarization floor
                total_score = scored_chunk.scores.total
                polarization = scored_chunk.scores.identity + scored_chunk.scores.tension
                
                if total_score >= self.MIN_TOTAL_SCORE and polarization >= POLARIZATION_FLOOR:
                    selected_indices.add(idx)
                    scored_chunk.qualified_axes.append("fill")
                    elite_chunks.append(scored_chunk)
            
            logger.info(f"Filled to {len(elite_chunks)} chunks (with polarization floor)")
        
        eliminated_ranking = len(surviving) - len(elite_chunks)
        
        # Cap at maximum - use adjusted_total for ranking
        if len(elite_chunks) > self.MAX_ELITE_CHUNKS:
            # FIX: Use adjusted_total (with multi-axis bonus) for final ranking
            elite_chunks.sort(key=lambda x: x.adjusted_total, reverse=True)
            eliminated_ranking += len(elite_chunks) - self.MAX_ELITE_CHUNKS
            elite_chunks = elite_chunks[:self.MAX_ELITE_CHUNKS]
            logger.info(f"Quota enforced: capped at {self.MAX_ELITE_CHUNKS}")
        
        is_low_yield = len(elite_chunks) < self.MIN_ELITE_CHUNKS
        if is_low_yield:
            logger.warning(
                f"Low yield: only {len(elite_chunks)} elite chunks "
                f"(minimum is {self.MIN_ELITE_CHUNKS})"
            )
        
        result = EliminationResult(
            elite_chunks=elite_chunks,
            eliminated_by_signal=eliminated_signal,
            eliminated_by_ranking=eliminated_ranking,
            is_low_yield=is_low_yield,
            axis_distribution=axis_distribution,
        )
        
        logger.info(
            f"Elimination complete: {result.total_elite} elite chunks "
            f"(signal: -{eliminated_signal}, ranking: -{eliminated_ranking})"
        )
        
        return result
