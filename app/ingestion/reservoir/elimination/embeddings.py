"""
Novelty Scoring via Embeddings (RELAXED VERSION).

Measures distance from "common knowledge" platitudes using sentence embeddings.
Higher distance = more novel = higher score.

RELAXED:
- More generous score mapping (scores start from 20 instead of 0)
- Fallback score of 40 when embeddings unavailable (instead of 0)
- Wider baseline for educational content

Uses sentence-transformers with all-MiniLM-L6-v2 (~80MB, runs on 8GB M1).
"""

import logging
from pathlib import Path
from typing import Optional, List

import numpy as np

logger = logging.getLogger(__name__)

# Default common knowledge platitudes for baseline
DEFAULT_COMMON_KNOWLEDGE: List[str] = [
    # Generic self-help
    "Hard work leads to success.",
    "You should focus on your goals.",
    "Time management is important.",
    "Distractions are bad for productivity.",
    "You need discipline to succeed.",
    "Consistency is key to achieving your goals.",
    "Believe in yourself and you can do anything.",
    "Success requires sacrifice.",
    "Follow your passion.",
    "Never give up on your dreams.",
    
    # Common productivity advice
    "Wake up early to be more productive.",
    "Plan your day the night before.",
    "Break big tasks into smaller ones.",
    "Eliminate distractions to focus better.",
    "Take regular breaks to stay fresh.",
    "Exercise improves mental clarity.",
    "Eat healthy to think better.",
    "Get enough sleep for peak performance.",
    
    # Generic life advice
    "Be grateful for what you have.",
    "Live in the present moment.",
    "Learn from your mistakes.",
    "Surround yourself with positive people.",
    "Set clear goals and work towards them.",
    "Communication is key in relationships.",
    "Money can't buy happiness.",
    "Health is wealth.",
    
    # Common mindset platitudes
    "Attitude is everything.",
    "You become what you think about.",
    "Positivity attracts success.",
    "Your network is your net worth.",
    "Knowledge is power.",
    "Actions speak louder than words.",
    "Practice makes perfect.",
    "Quality over quantity.",
    
    # Generic business advice
    "The customer is always right.",
    "Work smarter, not harder.",
    "Fail fast, learn faster.",
    "Innovation drives success.",
    "Leadership is about influence.",
    "Teamwork makes the dream work.",
]


class NoveltyScorer:
    """
    Scores chunk novelty via embedding distance from common knowledge.
    
    RELAXED VERSION:
    - More generous score mapping
    - Fallback score when embeddings unavailable
    
    Uses sentence-transformers to embed chunks and measure cosine distance
    from a pre-computed baseline of common platitudes.
    """
    
    # RELAXED: Fallback score when embeddings not available
    FALLBACK_SCORE = 40
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        cache_dir: Optional[Path] = None,
        common_knowledge: Optional[List[str]] = None,
    ):
        """
        Initialize novelty scorer.
        
        Args:
            model_name: Sentence transformer model name
            cache_dir: Directory to cache baseline embeddings
            common_knowledge: Custom platitude list (uses default if None)
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.common_knowledge = common_knowledge or DEFAULT_COMMON_KNOWLEDGE
        
        self._model = None
        self._baseline_center = None
        self._model_available = None  # Cache availability check
    
    def _load_model(self):
        """Lazy load the sentence transformer model."""
        if self._model is not None:
            return True
        
        if self._model_available is False:
            return False
        
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._model_available = True
            logger.info(f"Loaded sentence transformer: {self.model_name}")
            return True
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                f"Novelty scoring will return fallback score of {self.FALLBACK_SCORE}. "
                "Install with: pip install sentence-transformers"
            )
            self._model_available = False
            return False
        except Exception as e:
            logger.warning(f"Failed to load sentence transformer: {e}")
            self._model_available = False
            return False
    
    def _compute_baseline(self):
        """Compute and cache baseline center embedding."""
        if self._baseline_center is not None:
            return True
        
        # Try to load from cache
        cache_file = None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / "novelty_baseline.npy"
            if cache_file.exists():
                try:
                    self._baseline_center = np.load(cache_file)
                    logger.info(f"Loaded baseline from cache: {cache_file}")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to load cache: {e}")
        
        # Compute baseline
        if not self._load_model():
            return False
        
        logger.info(f"Computing baseline from {len(self.common_knowledge)} platitudes...")
        baseline_embeddings = self._model.encode(
            self.common_knowledge, 
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        self._baseline_center = np.mean(baseline_embeddings, axis=0)
        
        # Normalize the center
        self._baseline_center = self._baseline_center / np.linalg.norm(self._baseline_center)
        
        # Save to cache
        if cache_file:
            try:
                np.save(cache_file, self._baseline_center)
                logger.info(f"Saved baseline to cache: {cache_file}")
            except Exception as e:
                logger.warning(f"Failed to save cache: {e}")
        
        return True
    
    def score_novelty(self, chunk: str) -> int:
        """
        Score 0-100 for distance from common knowledge (RELAXED).
        
        Higher distance = more novel = higher score.
        
        RELAXED typical similarity ranges:
        - Generic platitude: 0.65 - 0.80 → score 20-40
        - Well-written but common: 0.55 - 0.65 → score 40-60
        - Fresh reframe: 0.35 - 0.55 → score 60-85
        - Sharp contrarian: < 0.35 → score 85-100
        
        Returns FALLBACK_SCORE (40) if embeddings not available.
        """
        if not self._compute_baseline():
            return self.FALLBACK_SCORE
        
        if self._model is None or self._baseline_center is None:
            return self.FALLBACK_SCORE
        
        try:
            # Encode chunk
            chunk_embedding = self._model.encode(
                [chunk], 
                normalize_embeddings=True,
                show_progress_bar=False,
            )[0]
            
            # Cosine similarity (embeddings are normalized)
            similarity = float(np.dot(chunk_embedding, self._baseline_center))
            
            # RELAXED: More generous score mapping
            # similarity 0.8 -> 20, similarity 0.2 -> 100
            # Score = 20 + (1 - similarity) * 100
            novelty = 20 + (1 - similarity) * 100
            
            return int(max(0, min(100, novelty)))
        except Exception as e:
            logger.warning(f"Error scoring novelty: {e}")
            return self.FALLBACK_SCORE
    
    def score_batch(self, chunks: List[str]) -> List[int]:
        """Score multiple chunks efficiently."""
        if not self._compute_baseline():
            return [self.FALLBACK_SCORE] * len(chunks)
        
        if self._model is None or self._baseline_center is None:
            return [self.FALLBACK_SCORE] * len(chunks)
        
        try:
            # Encode all chunks at once
            chunk_embeddings = self._model.encode(
                chunks,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            
            scores = []
            for embedding in chunk_embeddings:
                similarity = float(np.dot(embedding, self._baseline_center))
                # RELAXED: More generous score mapping
                novelty = 20 + (1 - similarity) * 100
                scores.append(int(max(0, min(100, novelty))))
            
            return scores
        except Exception as e:
            logger.warning(f"Error batch scoring novelty: {e}")
            return [self.FALLBACK_SCORE] * len(chunks)
