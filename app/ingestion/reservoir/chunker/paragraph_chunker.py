"""
Paragraph-based text chunker.

Splits text into chunks based on paragraph boundaries and word count rules:
- MIN = 250 words (minimum to form a chunk)
- TARGET = 350-700 words (preferred range)
- HARD MAX = 900 words (force close)
- Early close allowed if insight/resolution pattern detected
"""

import logging
import re
from typing import List, Optional

from app.ingestion.reservoir.schemas import (
    ChunkingConfig,
    Chunk,
    ChunkingResult,
)

logger = logging.getLogger(__name__)


class ParagraphChunker:
    """
    Paragraph-based text chunker.
    
    Accumulates paragraphs into chunks until word count thresholds
    are met, always closing at paragraph boundaries.
    """

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        Initialize chunker with optional configuration.
        
        Args:
            config: Chunking configuration. Uses defaults if not provided.
        """
        self.config = config or ChunkingConfig()
        
        # Compile early close patterns
        self._early_close_regex = None
        if self.config.enable_early_close and self.config.early_close_patterns:
            combined = "|".join(self.config.early_close_patterns)
            self._early_close_regex = re.compile(combined, re.IGNORECASE)

    def chunk_text(self, text: str) -> ChunkingResult:
        """
        Split text into chunks based on paragraph boundaries.
        
        Args:
            text: Cleaned text to chunk
            
        Returns:
            ChunkingResult with list of Chunk objects and statistics
        """
        cfg = self.config
        paragraphs = [
            p.strip() for p in text.split(cfg.paragraph_separator) if p.strip()
        ]

        if not paragraphs:
            return ChunkingResult()

        chunks: List[Chunk] = []
        current_paragraphs: List[str] = []
        current_word_count = 0
        start_para_idx = 0
        early_closes = 0

        for para_idx, paragraph in enumerate(paragraphs):
            para_words = self._count_words(paragraph)
            current_paragraphs.append(paragraph)
            current_word_count += para_words

            should_close, closed_early, early_reason = self._should_close_chunk(
                current_word_count, paragraph
            )

            if should_close and current_paragraphs:
                chunk = self._create_chunk(
                    paragraphs=current_paragraphs,
                    index=len(chunks),
                    start_para=start_para_idx,
                    end_para=para_idx,
                    closed_early=closed_early,
                    early_reason=early_reason,
                )
                chunks.append(chunk)
                if closed_early:
                    early_closes += 1

                current_paragraphs = []
                current_word_count = 0
                start_para_idx = para_idx + 1

        # Handle remaining paragraphs
        if current_paragraphs:
            self._handle_remainder(
                chunks, current_paragraphs, current_word_count,
                start_para_idx, len(paragraphs) - 1, cfg.paragraph_separator
            )

        # Calculate statistics
        total_words = sum(c.word_count for c in chunks)
        avg_words = total_words / len(chunks) if chunks else 0.0

        logger.info(
            f"Chunked text into {len(chunks)} chunks "
            f"(avg {avg_words:.0f} words, {early_closes} early closes)"
        )

        return ChunkingResult(
            chunks=chunks,
            total_chunks=len(chunks),
            total_words=total_words,
            total_paragraphs=len(paragraphs),
            avg_words_per_chunk=avg_words,
            early_closes=early_closes,
        )

    def _count_words(self, text: str) -> int:
        """Count words in text."""
        return len(text.split())

    def _should_close_chunk(
        self, word_count: int, paragraph: str
    ) -> tuple[bool, bool, Optional[str]]:
        """
        Determine if chunk should close after this paragraph.
        
        Returns:
            Tuple of (should_close, closed_early, early_reason)
        """
        cfg = self.config
        should_close = False
        closed_early = False
        early_reason = None

        # Hard max: must close
        if word_count >= cfg.hard_max_words:
            return True, False, None

        # In target range: close at good stopping point
        if word_count >= cfg.target_min_words:
            # Check for early close pattern
            if self._early_close_regex and word_count >= cfg.min_words:
                match = self._early_close_regex.search(paragraph.lower())
                if match:
                    return True, True, match.group(0)

            # Close if past target max
            if word_count >= cfg.target_max_words:
                return True, False, None

        # Above minimum: only close on strong early signal
        elif word_count >= cfg.min_words:
            if self._early_close_regex:
                match = self._early_close_regex.search(paragraph.lower())
                if match:
                    return True, True, match.group(0)

        return should_close, closed_early, early_reason

    def _create_chunk(
        self,
        paragraphs: List[str],
        index: int,
        start_para: int,
        end_para: int,
        closed_early: bool = False,
        early_reason: Optional[str] = None,
    ) -> Chunk:
        """Create a Chunk from accumulated paragraphs."""
        text = self.config.paragraph_separator.join(paragraphs)
        return Chunk(
            text=text,
            index=index,
            word_count=self._count_words(text),
            paragraph_count=len(paragraphs),
            start_paragraph=start_para,
            end_paragraph=end_para,
            closed_early=closed_early,
            early_close_reason=early_reason,
        )

    def _handle_remainder(
        self,
        chunks: List[Chunk],
        remaining: List[str],
        word_count: int,
        start_para: int,
        end_para: int,
        separator: str,
    ) -> None:
        """Handle remaining paragraphs after main loop."""
        cfg = self.config

        # Enough words: create new chunk
        if word_count >= cfg.min_words:
            chunk = self._create_chunk(remaining, len(chunks), start_para, end_para)
            chunks.append(chunk)
        # Merge with previous chunk if exists
        elif chunks:
            prev = chunks[-1]
            merged_text = prev.text + separator + separator.join(remaining)
            chunks[-1] = Chunk(
                text=merged_text,
                index=prev.index,
                word_count=self._count_words(merged_text),
                paragraph_count=prev.paragraph_count + len(remaining),
                start_paragraph=prev.start_paragraph,
                end_paragraph=end_para,
                closed_early=False,
                early_close_reason=None,
            )
        # No previous chunk: create anyway (short doc)
        else:
            chunk = self._create_chunk(remaining, 0, start_para, end_para)
            chunks.append(chunk)
