"""
Pydantic Schemas for Book Source Pipeline.

All FastAPI-ready models for PDF extraction, text cleaning, chunking, and filtering.
"""

from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# Cleaning Schemas
# ============================================================================


class CleaningConfig(BaseModel):
    """Configuration for PDF text cleaning."""

    model_config = ConfigDict(frozen=False)

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


# ============================================================================
# Extraction Schemas
# ============================================================================


class ExtractionResult(BaseModel):
    """Structured result from PDF extraction with full provenance."""

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

    text: str = Field(..., description="Cleaned text content")
    raw_text: str = Field(..., description="Original text before cleaning")
    title: str = Field(default="", description="Document title")
    author: str = Field(default="", description="Document author")
    pages: int = Field(default=0, ge=0, description="Number of pages")
    file_size: int = Field(default=0, ge=0, description="File size in bytes")
    filename: str = Field(default="", description="Original filename")
    stats: CleaningStats = Field(default_factory=CleaningStats)
    config_used: Optional[CleaningConfig] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)


# ============================================================================
# Chunking Schemas
# ============================================================================


class ChunkingConfig(BaseModel):
    """Configuration for text chunking."""

    model_config = ConfigDict(frozen=False)

    min_words: int = Field(default=250, ge=50)
    target_min_words: int = Field(default=350, ge=100)
    target_max_words: int = Field(default=700, ge=100)
    hard_max_words: int = Field(default=900, ge=100)
    paragraph_separator: str = Field(default="\n\n")
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
    """A text chunk extracted from a document."""

    text: str = Field(..., description="Chunk text content")
    index: int = Field(..., ge=0, description="0-based chunk index")
    word_count: int = Field(..., ge=0, description="Number of words in chunk")
    paragraph_count: int = Field(..., ge=0, description="Number of paragraphs")
    start_paragraph: int = Field(..., ge=0, description="Starting paragraph index")
    end_paragraph: int = Field(..., ge=0, description="Ending paragraph index")
    closed_early: bool = Field(default=False)
    early_close_reason: Optional[str] = Field(default=None)


class ChunkingResult(BaseModel):
    """Result from chunking operation with statistics."""

    chunks: List[Chunk] = Field(default_factory=list)
    total_chunks: int = Field(default=0, ge=0)
    total_words: int = Field(default=0, ge=0)
    total_paragraphs: int = Field(default=0, ge=0)
    avg_words_per_chunk: float = Field(default=0.0, ge=0.0)
    early_closes: int = Field(default=0, ge=0)


# ============================================================================
# Filter Schemas
# ============================================================================


class FilterDecision(str, Enum):
    """Binary filter decision - no scoring allowed."""

    PASS = "PASS"
    DROP = "DROP"


class DropReason(str, Enum):
    """Categorized drop reasons for debugging."""

    META_STRUCTURAL = "META_STRUCTURAL"
    INDEX_REFERENCE = "INDEX_REFERENCE"
    PURE_BIOGRAPHY = "PURE_BIOGRAPHY"
    QUOTATION_DUMP = "QUOTATION_DUMP"
    LIST_WITHOUT_MEANING = "LIST_WITHOUT_MEANING"
    WORD_COUNT_LOW = "WORD_COUNT_LOW"
    WORD_COUNT_HIGH = "WORD_COUNT_HIGH"
    NO_SIGNAL = "NO_SIGNAL"


class FilterResult(BaseModel):
    """Result from hard filter evaluation."""

    decision: FilterDecision
    drop_reason: Optional[DropReason] = None
    drop_details: Optional[str] = None
    signals_found: List[str] = Field(default_factory=list)
    word_count: int = Field(default=0, ge=0)
