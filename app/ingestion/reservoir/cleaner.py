"""
Text cleaning utilities for PDF extraction.

Handles removal of:
- Page numbers
- Headers/footers
- Table of contents
- Back matter (bibliography, index)
- Acknowledgments
- Encoding artifacts
"""

import logging
import re
from collections import Counter
from typing import Tuple, List

from app.ingestion.reservoir.schemas import CleaningConfig, CleaningStats

logger = logging.getLogger(__name__)


class TextCleaner:
    """
    Text cleaning utility for PDF content.
    
    Applies configurable cleaning steps with statistics tracking.
    """

    def __init__(self, config: CleaningConfig):
        """
        Initialize cleaner with configuration.
        
        Args:
            config: Cleaning configuration with enabled steps and thresholds
        """
        self.config = config

    def clean_with_stats(
        self, raw_text: str, page_count: int
    ) -> Tuple[str, CleaningStats, List[str]]:
        """
        Apply cleaning pipeline with full statistics tracking.
        
        Args:
            raw_text: Raw extracted text
            page_count: Number of pages in source document
            
        Returns:
            Tuple of (cleaned_text, stats, warnings)
        """
        stats = CleaningStats(original_chars=len(raw_text))
        warnings: List[str] = []
        text = raw_text

        def track_step(name: str, before: str, after: str) -> None:
            removed = len(before) - len(after)
            if removed > 0:
                stats.chars_removed_by_step[name] = removed

        # Apply cleaning steps in order
        if self.config.fix_encoding:
            before = text
            text = self._fix_encoding(text)
            track_step("fix_encoding", before, text)

        if self.config.remove_page_numbers:
            before = text
            text = self._remove_page_numbers(text)
            track_step("remove_page_numbers", before, text)

        if self.config.remove_headers_footers:
            if len(text.split("\n")) >= self.config.min_lines_for_header_footer_removal:
                before = text
                text = self._remove_headers_footers(text)
                track_step("remove_headers_footers", before, text)
            else:
                warnings.append("Skipped header/footer removal: document too short")

        if self.config.remove_toc:
            if page_count >= self.config.min_pages_for_toc_removal:
                before = text
                text = self._remove_toc(text)
                track_step("remove_toc", before, text)
            else:
                warnings.append("Skipped TOC removal: document too short")

        if self.config.remove_acknowledgments:
            before = text
            text = self._remove_acknowledgments(text)
            track_step("remove_acknowledgments", before, text)

        if self.config.remove_back_matter:
            if page_count >= self.config.min_pages_for_back_matter_removal:
                before = text
                text = self._remove_back_matter(text)
                track_step("remove_back_matter", before, text)
            else:
                warnings.append("Skipped back-matter removal: document too short")

        if self.config.normalize_whitespace:
            before = text
            text = self._normalize_whitespace(text)
            track_step("normalize_whitespace", before, text)

        text = text.strip()
        stats.final_chars = len(text)

        if stats.removal_percentage > self.config.max_removal_percentage:
            warnings.append(
                f"High removal rate: {stats.removal_percentage:.1%} of text removed "
                f"(threshold: {self.config.max_removal_percentage:.0%})"
            )

        return text, stats, warnings

    def _fix_encoding(self, text: str) -> str:
        """Fix common encoding artifacts."""
        replacements = {
            "\ufffd": "",
            "\u201c": '"',
            "\u201d": '"',
            "\u2018": "'",
            "\u2019": "'",
            "\u2013": "-",
            "\u2014": "-",
            "\u2026": "...",
            "\u00a0": " ",
            "\u00ad": "",
            "\ufb01": "fi",
            "\ufb02": "fl",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _remove_page_numbers(self, text: str) -> str:
        """Remove page number patterns."""
        patterns = [
            r"^\s*\d{1,4}\s*$",
            r"^\s*[Pp]age\s+\d+(\s+of\s+\d+)?\s*$",
            r"^\s*[-–—]\s*\d+\s*[-–—]\s*$",
            r"^\s*[ivxlcdm]+\s*$",
            r"^\s*[IVXLCDM]+\s*$",
        ]
        lines = text.split("\n")
        cleaned_lines = [
            line
            for line in lines
            if not any(re.match(p, line, re.IGNORECASE) for p in patterns)
        ]
        return "\n".join(cleaned_lines)

    def _remove_headers_footers(self, text: str) -> str:
        """Remove repeated headers/footers."""
        lines = text.split("\n")
        if len(lines) < self.config.min_lines_for_header_footer_removal:
            return text

        line_counts: Counter = Counter()
        for line in lines:
            normalized = line.strip().lower()
            if normalized and 3 < len(normalized) < 100:
                line_counts[normalized] += 1

        threshold = self.config.header_footer_min_occurrences
        frequent_lines = {
            line
            for line, count in line_counts.items()
            if count >= threshold and len(line.split()) < 10
        }

        cleaned_lines = [
            line for line in lines if line.strip().lower() not in frequent_lines
        ]
        return "\n".join(cleaned_lines)

    def _remove_toc(self, text: str) -> str:
        """Remove table of contents."""
        lines = text.split("\n")
        toc_start_patterns = [
            r"^\s*table\s+of\s+contents\s*$",
            r"^\s*contents\s*$",
        ]
        toc_line_pattern = re.compile(r"^.{5,60}[.\s_]{3,}\d{1,4}\s*$")

        in_toc = False
        consecutive_non_toc = 0
        cleaned_lines = []

        for line in lines:
            line_lower = line.strip().lower()

            if any(re.match(p, line_lower) for p in toc_start_patterns):
                in_toc = True
                consecutive_non_toc = 0
                continue

            if in_toc:
                is_toc_line = bool(toc_line_pattern.match(line))
                if is_toc_line:
                    consecutive_non_toc = 0
                    continue
                elif line.strip():
                    consecutive_non_toc += 1
                    if consecutive_non_toc >= 5:
                        in_toc = False
                        cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _remove_back_matter(self, text: str) -> str:
        """Remove back matter (bibliography, index, references)."""
        back_matter_markers = [
            r"^\s*bibliography\s*$",
            r"^\s*references\s*$",
            r"^\s*works\s+cited\s*$",
            r"^\s*index\s*$",
            r"^\s*endnotes\s*$",
        ]

        lines = text.split("\n")
        total_lines = len(lines)

        if total_lines < 100:
            return text

        check_start = int(total_lines * 0.85)

        for i in range(check_start, total_lines):
            line_lower = lines[i].strip().lower()
            if any(re.match(p, line_lower) for p in back_matter_markers):
                return "\n".join(lines[:i])

        return text

    def _remove_acknowledgments(self, text: str) -> str:
        """Remove acknowledgments section."""
        ack_patterns = [
            r"^\s*acknowledgments?\s*$",
            r"^\s*acknowledgements?\s*$",
        ]

        lines = text.split("\n")
        total_lines = len(lines)

        if total_lines < 30:
            return text

        check_end = int(total_lines * 0.15)
        ack_start = None

        for i in range(check_end):
            if any(re.match(p, lines[i].strip().lower()) for p in ack_patterns):
                ack_start = i
                break

        if ack_start is None:
            return text

        chapter_patterns = [
            r"^\s*chapter\s+\d+",
            r"^\s*part\s+\d+",
            r"^\s*introduction\s*$",
            r"^\s*preface\s*$",
        ]

        for i in range(ack_start + 1, min(ack_start + 50, total_lines)):
            if any(re.match(p, lines[i].strip().lower()) for p in chapter_patterns):
                return "\n".join(lines[:ack_start] + lines[i:])

        return "\n".join(lines[:ack_start] + lines[ack_start + 1:])

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace."""
        text = re.sub(r"[^\S\n]+", " ", text)
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text
