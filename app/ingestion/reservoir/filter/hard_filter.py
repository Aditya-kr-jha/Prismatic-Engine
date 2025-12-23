"""
Hard Filter for Book Source Pipeline.

Rule-based filtering to remove chunks where meaning cannot emerge.
This is NOT a ranking system - only binary PASS/DROP decisions.

Follows the Hard Filter Spec:
- Section A: Absolute drops (meta, index, biography, quotes, lists)
- Section B: Word count enforcement (250-900)
- Section C: Signal detection (academic, contrarian, meaning, implicit)
- Section D: Explicitly allowed patterns (do not drop for style)
"""

import logging
import re
from typing import List, Optional, Tuple

from app.ingestion.reservoir.schemas import (
    Chunk,
    FilterDecision,
    FilterResult,
    DropReason,
)
from app.ingestion.reservoir.filter.signal_phrases import (
    META_STRUCTURAL_PATTERNS,
    INDEX_REFERENCE_PATTERNS,
    BIOGRAPHY_PATTERNS,
    ACADEMIC_SIGNALS,
    CONTRARIAN_SIGNALS,
    MEANING_SIGNALS,
    IMPLICIT_INSIGHT_MARKERS,
)

logger = logging.getLogger(__name__)


class HardFilter:
    """
    Hard filter for text chunks.
    
    Applies rule-based filtering to remove chunks that cannot
    produce high-quality content before expensive LLM processing.
    
    Decision logic:
    1. IF any Section A rule applies → DROP
    2. ELSE IF word count fails → DROP
    3. ELSE IF no signal detected → DROP
    4. ELSE → PASS
    """

    # Word count thresholds (Section B)
    MIN_WORDS = 250
    MAX_WORDS = 900

    # Quotation threshold (Section A4)
    MAX_QUOTATION_RATIO = 0.30

    def __init__(self):
        """Initialize filter with compiled regex patterns."""
        # Compile drop patterns (Section A)
        self._meta_patterns = [
            re.compile(p, re.IGNORECASE) for p in META_STRUCTURAL_PATTERNS
        ]
        self._index_patterns = [
            re.compile(p, re.IGNORECASE) for p in INDEX_REFERENCE_PATTERNS
        ]
        self._bio_patterns = [
            re.compile(p, re.IGNORECASE) for p in BIOGRAPHY_PATTERNS
        ]

        # Compile signal patterns (Section C)
        self._academic_patterns = [
            re.compile(p, re.IGNORECASE) for p in ACADEMIC_SIGNALS
        ]
        self._contrarian_patterns = [
            re.compile(p, re.IGNORECASE) for p in CONTRARIAN_SIGNALS
        ]
        self._meaning_patterns = [
            re.compile(p, re.IGNORECASE) for p in MEANING_SIGNALS
        ]
        self._implicit_patterns = [
            re.compile(p, re.IGNORECASE) for p in IMPLICIT_INSIGHT_MARKERS
        ]

    def filter(self, chunk: Chunk) -> FilterResult:
        """
        Apply hard filter to a chunk.
        
        Args:
            chunk: The text chunk to evaluate
            
        Returns:
            FilterResult with PASS or DROP decision
        """
        text = chunk.text
        word_count = chunk.word_count

        # Section B: Word count enforcement
        if word_count < self.MIN_WORDS:
            return FilterResult(
                decision=FilterDecision.DROP,
                drop_reason=DropReason.WORD_COUNT_LOW,
                drop_details=f"Word count {word_count} < {self.MIN_WORDS}",
                word_count=word_count,
            )

        if word_count > self.MAX_WORDS:
            return FilterResult(
                decision=FilterDecision.DROP,
                drop_reason=DropReason.WORD_COUNT_HIGH,
                drop_details=f"Word count {word_count} > {self.MAX_WORDS}",
                word_count=word_count,
            )

        # Section A: Absolute drops
        drop_result = self._check_absolute_drops(text, word_count)
        if drop_result:
            return drop_result

        # Section C: Signal detection
        signals_found = self._detect_signals(text)

        if not signals_found:
            return FilterResult(
                decision=FilterDecision.DROP,
                drop_reason=DropReason.NO_SIGNAL,
                drop_details="No academic, contrarian, meaning, or implicit insight signals found",
                word_count=word_count,
            )

        # PASS - chunk has valid signals
        return FilterResult(
            decision=FilterDecision.PASS,
            signals_found=signals_found,
            word_count=word_count,
        )

    def _check_absolute_drops(
        self, text: str, word_count: int
    ) -> Optional[FilterResult]:
        """
        Check Section A absolute drop rules.
        
        Returns FilterResult if chunk should be dropped, None otherwise.
        """
        # A1: Meta / Structural text
        meta_count = sum(1 for p in self._meta_patterns if p.search(text))
        if meta_count >= 2:
            return FilterResult(
                decision=FilterDecision.DROP,
                drop_reason=DropReason.META_STRUCTURAL,
                drop_details=f"Contains {meta_count} meta/structural phrases",
                word_count=word_count,
            )

        # A2: Index / Reference / Bibliography
        index_count = sum(1 for p in self._index_patterns if p.search(text))
        if index_count >= 5:
            return FilterResult(
                decision=FilterDecision.DROP,
                drop_reason=DropReason.INDEX_REFERENCE,
                drop_details=f"Contains {index_count} index/reference patterns",
                word_count=word_count,
            )

        # A3: Pure biography (only if no insight signals present)
        bio_count = sum(1 for p in self._bio_patterns if p.search(text))
        if bio_count >= 3:
            # Check if there are ANY insight signals
            if not self._detect_signals(text):
                return FilterResult(
                    decision=FilterDecision.DROP,
                    drop_reason=DropReason.PURE_BIOGRAPHY,
                    drop_details=f"Pure biography with {bio_count} bio patterns and no insight",
                    word_count=word_count,
                )

        # A4: Quotation dumps
        quotation_ratio = self._calculate_quotation_ratio(text)
        if quotation_ratio > self.MAX_QUOTATION_RATIO:
            return FilterResult(
                decision=FilterDecision.DROP,
                drop_reason=DropReason.QUOTATION_DUMP,
                drop_details=f"Quotation ratio {quotation_ratio:.1%} > {self.MAX_QUOTATION_RATIO:.0%}",
                word_count=word_count,
            )

        # A5: Lists without meaning
        if self._is_list_without_meaning(text):
            return FilterResult(
                decision=FilterDecision.DROP,
                drop_reason=DropReason.LIST_WITHOUT_MEANING,
                drop_details="Primarily bullet/numbered list without synthesis",
                word_count=word_count,
            )

        return None

    def _detect_signals(self, text: str) -> List[str]:
        """
        Detect Section C signals in text.
        
        Returns list of signal categories found (inclusive OR).
        """
        signals = []

        # C1: Academic signals
        if any(p.search(text) for p in self._academic_patterns):
            signals.append("academic")

        # C2: Contrarian signals
        if any(p.search(text) for p in self._contrarian_patterns):
            signals.append("contrarian")

        # C3: Meaning signals
        if any(p.search(text) for p in self._meaning_patterns):
            signals.append("meaning")

        # C4: Implicit insight (causal language)
        if any(p.search(text) for p in self._implicit_patterns):
            signals.append("implicit_insight")

        return signals

    def _calculate_quotation_ratio(self, text: str) -> float:
        """Calculate ratio of text that is within quotation marks."""
        # Find all quoted sections
        quote_pattern = re.compile(r'["\u201c\u201d]([^"\u201c\u201d]*)["\u201c\u201d]')
        quoted_sections = quote_pattern.findall(text)
        
        if not quoted_sections:
            return 0.0

        quoted_chars = sum(len(q) for q in quoted_sections)
        total_chars = len(text)
        
        return quoted_chars / total_chars if total_chars > 0 else 0.0

    def _is_list_without_meaning(self, text: str) -> bool:
        """
        Check if text is primarily a list without synthesis.
        
        Returns True if:
        - More than 50% of lines start with bullet/number
        - AND no meaning signals present
        """
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) < 3:
            return False

        # Count list-like lines
        list_pattern = re.compile(r"^(\d+[\.\)]\s|[-•*]\s|[a-z][\.\)]\s)", re.IGNORECASE)
        list_lines = sum(1 for l in lines if list_pattern.match(l))
        
        list_ratio = list_lines / len(lines)
        
        if list_ratio > 0.5:
            # Check for meaning signals
            if not any(p.search(text) for p in self._meaning_patterns):
                return True

        return False

    def filter_batch(self, chunks: List[Chunk]) -> Tuple[List[Chunk], List[Chunk]]:
        """
        Filter a batch of chunks.
        
        Returns:
            Tuple of (passed_chunks, dropped_chunks)
        """
        passed = []
        dropped = []

        for chunk in chunks:
            result = self.filter(chunk)
            if result.decision == FilterDecision.PASS:
                passed.append(chunk)
            else:
                dropped.append(chunk)

        logger.info(
            f"Filtered {len(chunks)} chunks: {len(passed)} passed, {len(dropped)} dropped"
        )

        return passed, dropped
