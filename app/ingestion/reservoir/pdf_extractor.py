"""
PDF Extractor (FastAPI-Ready with Pydantic).

Extracts text from PDF documents with configurable cleaning and full provenance.
Uses Pydantic models for FastAPI integration.
"""

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import fitz  # PyMuPDF
from pydantic import BaseModel, Field, field_validator, ConfigDict

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration & Result Types (Pydantic Models)
# ============================================================================


class CleaningConfig(BaseModel):
    """
    Configuration for PDF text cleaning.

    All cleaning steps are opt-in and have safety thresholds.
    """

    model_config = ConfigDict(frozen=False)  # Allow mutation if needed

    # Master switches
    remove_page_numbers: bool = True
    remove_headers_footers: bool = True
    remove_toc: bool = True
    remove_acknowledgments: bool = True
    remove_back_matter: bool = True
    normalize_whitespace: bool = True
    fix_encoding: bool = True

    # Safety thresholds
    min_pages_for_toc_removal: int = Field(default=10, ge=1)
    min_pages_for_back_matter_removal: int = Field(default=20, ge=1)
    min_lines_for_header_footer_removal: int = Field(default=50, ge=1)
    max_removal_percentage: float = Field(default=0.30, ge=0.0, le=1.0)

    # Header/footer detection
    header_zone_ratio: float = Field(default=0.08, ge=0.0, le=0.5)
    footer_zone_ratio: float = Field(default=0.08, ge=0.0, le=0.5)
    header_footer_min_occurrences: int = Field(default=3, ge=1)

    # Block filtering
    skip_footer_blocks: bool = True
    footer_block_threshold: float = Field(default=0.92, ge=0.0, le=1.0)
    detect_full_width_blocks: bool = True


class CleaningStats(BaseModel):
    """Statistics about what was removed during cleaning."""

    original_chars: int = Field(default=0, ge=0)
    final_chars: int = Field(default=0, ge=0)
    chars_removed_by_step: Dict[str, int] = Field(default_factory=dict)

    @property
    def removal_percentage(self) -> float:
        if self.original_chars == 0:
            return 0.0
        return (self.original_chars - self.final_chars) / self.original_chars

    @property
    def chars_removed(self) -> int:
        return self.original_chars - self.final_chars


class ExtractionResult(BaseModel):
    """
    Structured result from PDF extraction with full provenance.

    This model is FastAPI-ready and can be returned directly from endpoints.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "Chapter 1: Introduction...",
                "raw_text": "Chapter 1: Introduction...",
                "title": "Deep Work",
                "author": "Cal Newport",
                "pages": 296,
                "file_size": 2048576,
                "filename": "deep-work.pdf",
                "confidence": 0.95,
            }
        }
    )

    # Core content
    text: str = Field(..., description="Cleaned text content")
    raw_text: str = Field(..., description="Original text before cleaning")

    # Metadata
    title: str = Field(default="", description="Document title")
    author: str = Field(default="", description="Document author")
    pages: int = Field(default=0, ge=0, description="Number of pages")
    file_size: int = Field(default=0, ge=0, description="File size in bytes")
    filename: str = Field(default="", description="Original filename")

    # Provenance
    stats: CleaningStats = Field(default_factory=CleaningStats)
    config_used: Optional[CleaningConfig] = None

    # Quality metrics
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction quality confidence score"
    )
    warnings: List[str] = Field(default_factory=list)

    # Keep your existing to_dict for backward compatibility if needed
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (legacy support)."""
        return self.model_dump()


class ChunkingConfig(BaseModel):
    """
    Configuration for text chunking.

    Chunks are created by accumulating paragraphs until word count
    thresholds are met, always closing at paragraph boundaries.
    """

    model_config = ConfigDict(frozen=False)

    # Word count thresholds
    min_words: int = Field(default=250, ge=50)
    target_min_words: int = Field(default=350, ge=100)
    target_max_words: int = Field(default=700, ge=100)
    hard_max_words: int = Field(default=900, ge=100)

    # Paragraph detection
    paragraph_separator: str = Field(default="\n\n")

    # Early close detection
    enable_early_close: bool = True
    early_close_patterns: List[str] = Field(
        default_factory=lambda: [
            r"(?:the (?:key|crucial|important|essential) (?:point|insight|lesson|takeaway) is)",
            r"(?:this (?:shows|demonstrates|proves|reveals|means) that)",
            r"(?:in other words|put simply|the bottom line|ultimately)",
            r"(?:what (?:this|we) (?:learn|discover|realize|understand))",
            r"(?:and that(?:'s| is) (?:why|how|what))",
            r"(?:this is (?:the|why|how|what))",
            r"(?:the (?:result|outcome|consequence|implication) (?:is|was))",
        ]
    )

    @field_validator("target_max_words")
    @classmethod
    def validate_target_max(cls, v: int, info) -> int:
        if "target_min_words" in info.data and v < info.data["target_min_words"]:
            raise ValueError("target_max_words must be >= target_min_words")
        return v

    @field_validator("hard_max_words")
    @classmethod
    def validate_hard_max(cls, v: int, info) -> int:
        if "target_max_words" in info.data and v < info.data["target_max_words"]:
            raise ValueError("hard_max_words must be >= target_max_words")
        return v


class Chunk(BaseModel):
    """
    A text chunk extracted from a document.

    Contains the text content along with metadata for provenance.
    """

    text: str = Field(..., description="Chunk text content")
    index: int = Field(..., ge=0, description="0-based chunk index")
    word_count: int = Field(..., ge=0, description="Number of words in chunk")
    paragraph_count: int = Field(..., ge=0, description="Number of paragraphs")
    start_paragraph: int = Field(..., ge=0, description="Starting paragraph index")
    end_paragraph: int = Field(..., ge=0, description="Ending paragraph index")
    closed_early: bool = Field(
        default=False, description="Closed before target due to insight"
    )
    early_close_reason: Optional[str] = Field(
        default=None, description="Reason for early close"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (legacy support)."""
        return self.model_dump()


class ChunkingResult(BaseModel):
    """Result from chunking operation with statistics."""

    chunks: List[Chunk] = Field(default_factory=list)
    total_chunks: int = Field(default=0, ge=0)
    total_words: int = Field(default=0, ge=0)
    total_paragraphs: int = Field(default=0, ge=0)
    avg_words_per_chunk: float = Field(default=0.0, ge=0.0)
    early_closes: int = Field(default=0, ge=0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (legacy support)."""
        return self.model_dump()


# ============================================================================
# Internal Models (Not exposed via API - can stay as regular classes)
# ============================================================================


class PageBlock:
    """A text block with position information (internal use only)."""

    def __init__(
        self,
        text: str,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        page_num: int,
        page_height: float,
        page_width: float,
    ):
        self.text = text
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.page_num = page_num
        self.page_height = page_height
        self.page_width = page_width

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def y_ratio(self) -> float:
        return self.y0 / self.page_height if self.page_height > 0 else 0

    @property
    def width_ratio(self) -> float:
        return self.width / self.page_width if self.page_width > 0 else 0

    @property
    def is_full_width(self) -> bool:
        return self.width_ratio > 0.7


# ============================================================================
# PDFExtractor Class (Implementation remains mostly the same)
# ============================================================================


class PDFExtractor:
    """
    Production-grade PDF document extractor with configurable cleaning.

    Returns structured ExtractionResult (Pydantic model) with:
    - Cleaned text
    - Original raw text (for audit/debug)
    - Cleaning statistics
    - Confidence score
    - Warnings for potential issues
    """

    def __init__(self, config: Optional[CleaningConfig] = None):
        """
        Initialize extractor with optional cleaning configuration.

        Args:
            config: Cleaning configuration. Uses defaults if not provided.
        """
        self.config = config or CleaningConfig()
        self.supported_formats = [".pdf"]

    # ============================================================================
    # Validation Methods
    # ============================================================================

    def validate_pdf(self, file_path: Path) -> Tuple[bool, str]:
        """Validate PDF file from path."""
        if not file_path.exists():
            return False, "File does not exist"

        if file_path.suffix.lower() not in self.supported_formats:
            return False, f"Unsupported format. Supported: {self.supported_formats}"

        try:
            with fitz.open(file_path) as doc:
                if len(doc) == 0:
                    return False, "PDF has no pages"
            return True, ""
        except Exception as e:
            return False, f"Invalid PDF: {str(e)}"

    def validate_pdf_bytes(self, file_content: bytes) -> Tuple[bool, str]:
        """Validate PDF from bytes."""
        try:
            with fitz.open(stream=file_content, filetype="pdf") as doc:
                if len(doc) == 0:
                    return False, "PDF has no pages"
            return True, ""
        except Exception as e:
            return False, f"Invalid PDF: {str(e)}"

    # ============================================================================
    # Main Extraction Methods
    # ============================================================================

    def extract(self, file_path: Path) -> ExtractionResult:
        """
        Extract and clean text from PDF file with full provenance.

        Args:
            file_path: Path to the PDF file

        Returns:
            ExtractionResult (Pydantic model) with cleaned text, stats, and provenance
        """
        logger.info(f"Extracting text from: {file_path}")

        try:
            with fitz.open(file_path) as doc:
                metadata = self._extract_metadata_from_doc(
                    doc, file_path.stat().st_size, file_path.name
                )
                blocks = self._extract_blocks_from_doc(doc)
                page_count = len(doc)

            raw_text = self._blocks_to_text(blocks, page_count)
            cleaned_text, stats, warnings = self._clean_text_with_stats(
                raw_text, page_count
            )
            confidence = self._calculate_confidence(stats, warnings, page_count)

            result = ExtractionResult(
                text=cleaned_text,
                raw_text=raw_text,
                title=metadata.get("title", ""),
                author=metadata.get("author", ""),
                pages=page_count,
                file_size=metadata.get("file_size", 0),
                filename=metadata.get("filename", ""),
                stats=stats,
                config_used=self.config,
                confidence=confidence,
                warnings=warnings,
            )

            logger.info(
                f"Extracted {len(cleaned_text):,} chars from {page_count} pages "
                f"(confidence: {confidence:.2f})"
            )
            return result

        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            raise

    def extract_text(self, file_path: Path) -> str:
        """Simple extraction returning just cleaned text."""
        return self.extract(file_path).text

    def extract_from_bytes(
        self, file_content: bytes, filename: str = "document.pdf"
    ) -> ExtractionResult:
        """Extract from bytes with full provenance."""
        logger.info("Extracting text from PDF bytes")

        try:
            with fitz.open(stream=file_content, filetype="pdf") as doc:
                metadata = self._extract_metadata_from_doc(
                    doc, len(file_content), filename
                )
                blocks = self._extract_blocks_from_doc(doc)
                page_count = len(doc)

            raw_text = self._blocks_to_text(blocks, page_count)
            cleaned_text, stats, warnings = self._clean_text_with_stats(
                raw_text, page_count
            )
            confidence = self._calculate_confidence(stats, warnings, page_count)

            return ExtractionResult(
                text=cleaned_text,
                raw_text=raw_text,
                title=metadata.get("title", ""),
                author=metadata.get("author", ""),
                pages=page_count,
                file_size=len(file_content),
                filename=filename,
                stats=stats,
                config_used=self.config,
                confidence=confidence,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Error extracting text from bytes: {str(e)}")
            raise

    def extract_raw_text(self, file_path: Path) -> str:
        """Extract raw text without any cleaning (for debugging)."""
        with fitz.open(file_path) as doc:
            blocks = self._extract_blocks_from_doc(doc)
            return self._blocks_to_text(blocks, len(doc))

    # ============================================================================
    # Text Chunking
    # ============================================================================

    def chunk_text(
        self,
        text: str,
        config: Optional[ChunkingConfig] = None,
    ) -> ChunkingResult:
        """
        Split text into chunks based on paragraph boundaries and word count rules.

        Returns ChunkingResult (Pydantic model) for easy FastAPI serialization.
        """
        cfg = config or ChunkingConfig()

        paragraphs = [
            p.strip() for p in text.split(cfg.paragraph_separator) if p.strip()
        ]

        if not paragraphs:
            return ChunkingResult(
                chunks=[],
                total_chunks=0,
                total_words=0,
                total_paragraphs=0,
                avg_words_per_chunk=0.0,
                early_closes=0,
            )

        early_close_regex = None
        if cfg.enable_early_close and cfg.early_close_patterns:
            combined_pattern = "|".join(cfg.early_close_patterns)
            early_close_regex = re.compile(combined_pattern, re.IGNORECASE)

        chunks: List[Chunk] = []
        current_paragraphs: List[str] = []
        current_word_count = 0
        start_para_idx = 0
        early_closes = 0

        def count_words(text: str) -> int:
            return len(text.split())

        def create_chunk(
            paras: List[str],
            start_idx: int,
            end_idx: int,
            closed_early: bool = False,
            early_reason: Optional[str] = None,
        ) -> Chunk:
            text_content = cfg.paragraph_separator.join(paras)
            return Chunk(
                text=text_content,
                index=len(chunks),
                word_count=count_words(text_content),
                paragraph_count=len(paras),
                start_paragraph=start_idx,
                end_paragraph=end_idx,
                closed_early=closed_early,
                early_close_reason=early_reason,
            )

        for para_idx, paragraph in enumerate(paragraphs):
            para_words = count_words(paragraph)
            current_paragraphs.append(paragraph)
            current_word_count += para_words

            should_close = False
            closed_early = False
            early_reason = None

            if current_word_count >= cfg.hard_max_words:
                should_close = True

            elif current_word_count >= cfg.target_min_words:
                if early_close_regex and current_word_count >= cfg.min_words:
                    match = early_close_regex.search(paragraph.lower())
                    if match:
                        should_close = True
                        closed_early = True
                        early_reason = match.group(0)

                if current_word_count >= cfg.target_max_words:
                    should_close = True

            elif current_word_count >= cfg.min_words:
                if early_close_regex:
                    match = early_close_regex.search(paragraph.lower())
                    if match:
                        should_close = True
                        closed_early = True
                        early_reason = match.group(0)

            if should_close and current_paragraphs:
                chunk = create_chunk(
                    current_paragraphs,
                    start_para_idx,
                    para_idx,
                    closed_early,
                    early_reason,
                )
                chunks.append(chunk)
                if closed_early:
                    early_closes += 1

                current_paragraphs = []
                current_word_count = 0
                start_para_idx = para_idx + 1

        if current_paragraphs:
            if current_word_count >= cfg.min_words:
                chunk = create_chunk(
                    current_paragraphs,
                    start_para_idx,
                    len(paragraphs) - 1,
                )
                chunks.append(chunk)
            elif chunks:
                prev_chunk = chunks[-1]
                merged_text = (
                    prev_chunk.text
                    + cfg.paragraph_separator
                    + cfg.paragraph_separator.join(current_paragraphs)
                )
                chunks[-1] = Chunk(
                    text=merged_text,
                    index=prev_chunk.index,
                    word_count=count_words(merged_text),
                    paragraph_count=prev_chunk.paragraph_count
                    + len(current_paragraphs),
                    start_paragraph=prev_chunk.start_paragraph,
                    end_paragraph=len(paragraphs) - 1,
                    closed_early=False,
                    early_close_reason=None,
                )
            else:
                chunk = create_chunk(
                    current_paragraphs,
                    start_para_idx,
                    len(paragraphs) - 1,
                )
                chunks.append(chunk)

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

    def extract_and_chunk(
        self,
        file_path: Path,
        chunking_config: Optional[ChunkingConfig] = None,
    ) -> Tuple[ExtractionResult, ChunkingResult]:
        """
        Extract text from PDF and chunk it in one operation.

        Returns Pydantic models ready for FastAPI serialization.
        """
        result = self.extract(file_path)
        chunks = self.chunk_text(result.text, chunking_config)
        return result, chunks

    # ============================================================================
    # Internal Methods (implementation details - keep as-is)
    # ============================================================================

    def _extract_blocks_from_doc(self, doc: fitz.Document) -> List[PageBlock]:
        """Extract text blocks with full position information."""
        all_blocks = []

        for page_num, page in enumerate(doc):
            page_height = page.rect.height
            page_width = page.rect.width
            raw_blocks = page.get_text("blocks")

            for block in raw_blocks:
                if block[6] != 0:
                    continue

                text = block[4].strip()
                if not text:
                    continue

                page_block = PageBlock(
                    text=text,
                    x0=block[0],
                    y0=block[1],
                    x1=block[2],
                    y1=block[3],
                    page_num=page_num,
                    page_height=page_height,
                    page_width=page_width,
                )

                if (
                    self.config.skip_footer_blocks
                    and page_block.y_ratio > self.config.footer_block_threshold
                ):
                    continue

                all_blocks.append(page_block)

        return all_blocks

    def _blocks_to_text(self, blocks: List[PageBlock], page_count: int) -> str:
        """Convert blocks to text with intelligent ordering."""
        if not blocks:
            return ""

        pages: Dict[int, List[PageBlock]] = {}
        for block in blocks:
            if block.page_num not in pages:
                pages[block.page_num] = []
            pages[block.page_num].append(block)

        full_text_parts = []

        for page_num in sorted(pages.keys()):
            page_blocks = pages[page_num]
            sorted_blocks = sorted(
                page_blocks,
                key=lambda b: (
                    0 if b.is_full_width else 1,
                    b.y0,
                    b.x0,
                ),
            )

            page_text = "\n\n".join(b.text for b in sorted_blocks)
            if page_text:
                full_text_parts.append(page_text)

        return "\n\n".join(full_text_parts)

    def _clean_text_with_stats(
        self, raw_text: str, page_count: int
    ) -> Tuple[str, CleaningStats, List[str]]:
        """Apply cleaning pipeline with full statistics tracking."""
        stats = CleaningStats(original_chars=len(raw_text))
        warnings = []
        text = raw_text

        def track_step(name: str, before: str, after: str):
            removed = len(before) - len(after)
            if removed > 0:
                stats.chars_removed_by_step[name] = removed

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

    def _calculate_confidence(
        self, stats: CleaningStats, warnings: List[str], page_count: int
    ) -> float:
        """Calculate confidence score based on extraction quality."""
        confidence = 1.0

        if stats.removal_percentage > 0.3:
            confidence -= 0.3
        elif stats.removal_percentage > 0.2:
            confidence -= 0.15
        elif stats.removal_percentage > 0.1:
            confidence -= 0.05

        chars_per_page = stats.final_chars / max(page_count, 1)
        if chars_per_page < 100:
            confidence -= 0.4
            warnings.append("Very low text density - PDF may be scanned/image-based")
        elif chars_per_page < 500:
            confidence -= 0.2
            warnings.append("Low text density")

        confidence -= len(warnings) * 0.02

        return max(0.0, min(1.0, confidence))

    # Text cleaning methods (keep as-is from original)
    def _remove_page_numbers(self, text: str) -> str:
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
            if not any(re.match(pattern, line, re.IGNORECASE) for pattern in patterns)
        ]
        return "\n".join(cleaned_lines)

    def _remove_headers_footers(self, text: str) -> str:
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
        """Remove back matter with safety constraints."""
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
        """Remove acknowledgments section from front matter."""
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

        return "\n".join(lines[:ack_start] + lines[ack_start + 1 :])

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace throughout the text."""
        text = re.sub(r"[^\S\n]+", " ", text)
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

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

    # ============================================================================
    # Metadata Extraction
    # ============================================================================

    def _extract_metadata_from_doc(
        self, doc: fitz.Document, file_size: int, filename: str
    ) -> Dict[str, Any]:
        """Extract metadata from PyMuPDF document."""
        metadata = doc.metadata
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
            "pages": len(doc),
            "file_size": file_size,
            "filename": filename,
        }

    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract PDF metadata from file."""
        try:
            with fitz.open(file_path) as doc:
                return self._extract_metadata_from_doc(
                    doc, file_path.stat().st_size, file_path.name
                )
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            return {
                "pages": 0,
                "file_size": file_path.stat().st_size if file_path.exists() else 0,
                "filename": file_path.name,
            }


# ============================================================================
# Convenience Functions
# ============================================================================


def extract_pdf(
    file_path: Path,
    config: Optional[CleaningConfig] = None,
) -> ExtractionResult:
    """
    Extract text from PDF with default or custom configuration.

    Args:
        file_path: Path to PDF file
        config: Optional cleaning configuration

    Returns:
        ExtractionResult (Pydantic model) with text, stats, and provenance
    """
    extractor = PDFExtractor(config=config)
    return extractor.extract(file_path)


if __name__ == "__main__":
    # Example usage
    from pathlib import Path

    extractor = PDFExtractor()
    project_root = Path(__file__).resolve().parents[3]
    pdf_path = (project_root / "Books" / "deep-work.pdf").resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at: {pdf_path}")

    result = extractor.extract(pdf_path)

    print("=== Extraction Result ===")
    print(f"Title: {result.title}")
    print(f"Author: {result.author}")
    print(f"Pages: {result.pages}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"\n=== Stats ===")
    print(f"Original: {result.stats.original_chars:,} chars")
    print(f"Final: {result.stats.final_chars:,} chars")
    print(f"Removed: {result.stats.removal_percentage:.1%}")
    print(f"\n=== By Step ===")
    for step, removed in result.stats.chars_removed_by_step.items():
        print(f"  {step}: {removed:,} chars")
    print(f"\n=== Warnings ===")
    for w in result.warnings:
        print(f"  - {w}")
    print(f"\n=== First 1500 chars ===")
    print(result.text[:1500])

    # Test JSON serialization (Pydantic feature)
    print("\n=== JSON Serialization Test ===")
    json_str = result.model_dump_json(indent=2)
    print(f"Successfully serialized to JSON ({len(json_str)} bytes)")

    # Test chunking
    print("\n=== Chunking Test ===")
    chunking_result = extractor.chunk_text(result.text)
    print(f"Created {chunking_result.total_chunks} chunks")
    print(f"Average words per chunk: {chunking_result.avg_words_per_chunk:.1f}")
    print(f"Early closes: {chunking_result.early_closes}")
