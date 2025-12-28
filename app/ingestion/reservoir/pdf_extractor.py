"""
PDF Extractor - Thin Orchestration Layer.

Composes modular pipeline components for book extraction:
  STEP 1: Extract raw text from PDF
  STEP 2: Structural cleanup (via TextCleaner)
  STEP 3: Split into candidate blocks (via ParagraphChunker)
  STEP 4: Hard filter rule-based drops (via HardFilter)
  STEP 5: LLM validation for semantic quality
  STEP 6: Elite filter for Instagram-viral content (via EliteFilter)
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import fitz  # PyMuPDF
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama

from app.infra.llm.pre_injection_prompts import (
    CONTENT_VALIDATOR_SYSTEM_PROMPT,
    CONTENT_VALIDATOR_USER_PROMPT,
)
from app.ingestion.reservoir.chunker import ParagraphChunker
from app.ingestion.reservoir.cleaner import TextCleaner
from app.ingestion.reservoir.elimination import EliteFilter
from app.ingestion.reservoir.elimination.ranking import EliminationResult
from app.ingestion.reservoir.filter import HardFilter
from app.ingestion.reservoir.schemas import (
    CleaningConfig,
    CleaningStats,
    ExtractionResult,
    ChunkingConfig,
    Chunk,
    ChunkingResult,
    FilterResult,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Internal Model (position-aware block)
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
    def y_ratio(self) -> float:
        return self.y0 / self.page_height if self.page_height > 0 else 0

    @property
    def width_ratio(self) -> float:
        width = self.x1 - self.x0
        return width / self.page_width if self.page_width > 0 else 0

    @property
    def is_full_width(self) -> bool:
        return self.width_ratio > 0.7


# ============================================================================
# PDFExtractor Class
# ============================================================================


class PDFExtractor:
    """
    Production-grade PDF extractor with modular pipeline.

    Pipeline Steps:
        1. extract() - Raw text from PDF + structural cleanup
        2. chunk() - Split into paragraph-based chunks
        3. filter_chunks() - Rule-based hard filter
        4. validate_chunks_with_llm() - LLM validation
        5. elite_filter() - Elite filtering for Instagram-viral content
        6. process() - Full pipeline in one call
    """

    def __init__(self, config: Optional[CleaningConfig] = None):
        """
        Initialize extractor with optional cleaning configuration.

        Args:
            config: Cleaning configuration. Uses defaults if not provided.
        """
        self.config = config or CleaningConfig()
        self.cleaner = TextCleaner(self.config)
        self.chunker: Optional[ParagraphChunker] = None
        self.hard_filter = HardFilter()
        self.elite_filter_instance = EliteFilter(enable_novelty=True)
        self.supported_formats = [".pdf"]

    # ========================================================================
    # Validation
    # ========================================================================

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

    # ========================================================================
    # STEP 1 + 2: Extract and Clean
    # ========================================================================

    def extract(self, file_path: Path) -> ExtractionResult:
        """
        Extract and clean text from PDF file.

        Pipeline Steps 1 & 2: Raw extraction + structural cleanup.
        """
        logger.info(f"Extracting text from: {file_path}")

        try:
            with fitz.open(file_path) as doc:
                metadata = self._extract_metadata_from_doc(
                    doc, file_path.stat().st_size, file_path.name
                )
                blocks = self._extract_blocks_from_doc(doc)
                page_count = len(doc)

            raw_text = self._blocks_to_text(blocks)
            cleaned_text, stats, warnings = self.cleaner.clean_with_stats(
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

            raw_text = self._blocks_to_text(blocks)
            cleaned_text, stats, warnings = self.cleaner.clean_with_stats(
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

    # ========================================================================
    # STEP 3: Chunk
    # ========================================================================

    def chunk(
        self, text: str, config: Optional[ChunkingConfig] = None
    ) -> ChunkingResult:
        """
        Split text into paragraph-based chunks.

        Pipeline Step 3: Accumulate paragraphs until word thresholds met.
        """
        chunker = ParagraphChunker(config)
        return chunker.chunk_text(text)

    # ========================================================================
    # STEP 4: Hard Filter
    # ========================================================================

    def filter_chunks(
        self, chunks: List[Chunk]
    ) -> Tuple[List[Chunk], List[Tuple[Chunk, FilterResult]]]:
        """
        Apply rule-based hard filter to chunks.

        Pipeline Step 4: Binary PASS/DROP for each chunk.

        Returns:
            Tuple of (passed_chunks, dropped with reasons)
        """
        passed, dropped = self.hard_filter.filter_batch(chunks)
        return passed, dropped

    # ========================================================================
    # STEP 5: LLM Validation
    # ========================================================================

    def validate_chunks_with_llm(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Validate chunks using local LLM (Ollama).

        Pipeline Step 5: Semantic validation using qwen2.5:7b-instruct-q4_K_M.

        Args:
            chunks: List of chunks that passed hard filter.

        Returns:
            List of chunks that passed LLM validation.
        """
        if not chunks:
            return []

        llm = ChatOllama(
            # model="qwen2.5:7b-instruct-q4_K_M",
            model="llama3.1:8b",
            temperature=0,
        )

        validated_chunks: List[Chunk] = []

        for chunk in chunks:
            user_prompt = CONTENT_VALIDATOR_USER_PROMPT.replace(
                "{CHUNK_TEXT}", chunk.text
            )

            messages = [
                SystemMessage(content=CONTENT_VALIDATOR_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]

            try:
                response = llm.invoke(messages)
                response_text = response.content.strip()

                # Parse JSON response
                result = json.loads(response_text)

                if isinstance(result, dict) and result.get("pass") is True:
                    validated_chunks.append(chunk)

            except (json.JSONDecodeError, KeyError, TypeError):
                # Malformed response -> treat as pass = false
                pass

        return validated_chunks

    # ========================================================================
    # STEP 6: Elite Filter
    # ========================================================================

    def elite_filter(self, chunks: List[Chunk]) -> EliminationResult:
        """
        Apply 4-stage elimination gate to produce elite chunks.

        Pipeline Step 6: Elite filtering for Instagram-viral content.

        Stages:
            A: Hard Signal Detection (binary elimination)
            B: Multi-Axis Scoring (PUNCH/IDENTITY/TENSION/QUOTABILITY/NOVELTY)
            C: Competitive Ranking (top N per axis)
            D: Quota Enforcement (20-30 chunks)

        Args:
            chunks: List of chunks that passed LLM validation.

        Returns:
            EliminationResult with elite chunks and statistics.
        """
        return self.elite_filter_instance.filter(chunks)

    # ========================================================================
    # Full Pipeline
    # ========================================================================

    def process(
        self,
        file_path: Path,
        chunking_config: Optional[ChunkingConfig] = None,
    ) -> Tuple[
        ExtractionResult,
        ChunkingResult,
        EliminationResult,
        List[Tuple[Chunk, FilterResult]],
    ]:
        """
        Run full extraction pipeline.

        Returns:
            Tuple of (extraction_result, chunking_result, elimination_result, dropped_chunks)
        """
        is_valid, reason = self.validate_pdf(file_path)
        if not is_valid:
            raise ValueError(f"PDF validation failed: {reason} ({file_path})")

        # Step 1+2: Extract and clean
        extraction_result = self.extract(file_path)

        # Step 3: Chunk
        chunking_result = self.chunk(extraction_result.text, chunking_config)

        # Step 4: Hard filter
        passed, dropped = self.filter_chunks(chunking_result.chunks)

        # Step 5: LLM validation
        # validated = self.validate_chunks_with_llm(passed)

        # Step 6: Elite filter
        elimination_result = self.elite_filter(passed)

        # logger.info(
        #     f"Pipeline complete: {elimination_result.total_elite} elite chunks, "
        #     f"{len(validated)} validated, {len(dropped)} dropped by filter"
        # )

        return extraction_result, chunking_result, elimination_result, dropped

    # ========================================================================
    # Internal Helpers
    # ========================================================================

    def _extract_blocks_from_doc(self, doc: fitz.Document) -> List[PageBlock]:
        """Extract text blocks with position information."""
        all_blocks = []

        for page_num, page in enumerate(doc):
            page_height = page.rect.height
            page_width = page.rect.width
            raw_blocks = page.get_text("blocks")

            for block in raw_blocks:
                if block[6] != 0:  # Skip image blocks
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

                # Skip footer blocks
                if (
                    self.config.skip_footer_blocks
                    and page_block.y_ratio > self.config.footer_block_threshold
                ):
                    continue

                all_blocks.append(page_block)

        return all_blocks

    def _blocks_to_text(self, blocks: List[PageBlock]) -> str:
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

    def _extract_metadata_from_doc(
        self, doc: fitz.Document, file_size: int, filename: str
    ) -> Dict[str, Any]:
        """Extract metadata from PyMuPDF document."""
        metadata = doc.metadata
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "pages": len(doc),
            "file_size": file_size,
            "filename": filename,
        }

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
        elif chars_per_page < 500:
            confidence -= 0.2

        confidence -= len(warnings) * 0.02

        return max(0.0, min(1.0, confidence))


# app/ingestion/reservoir/pdf_extractor.py

if __name__ == "__main__":
    import sys
    from pathlib import Path

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    project_root = Path(__file__).resolve().parents[3]
    pdf_path = project_root / "Books" / "deep-work.pdf"

    extractor = PDFExtractor()

    is_valid, reason = extractor.validate_pdf(pdf_path)
    if not is_valid:
        logger.error(f"PDF validation failed: {reason} ({pdf_path})")
        sys.exit(2)

    try:
        extraction_result, chunking_result, elimination_result, dropped = (
            extractor.process(pdf_path)
        )
    except Exception as exc:
        logger.exception(f"Pipeline failed for {pdf_path}: {exc}")
        sys.exit(1)

    print("\n=== PDF Extraction Pipeline Result ===")
    print(f"File: {pdf_path}")
    print(f"Pages: {extraction_result.pages}")
    print(f"File size (bytes): {extraction_result.file_size}")
    print(f"Title: {extraction_result.title}")
    print(f"Author: {extraction_result.author}")
    print(f"Confidence: {extraction_result.confidence:.2f}")
    print(f"Warnings: {len(extraction_result.warnings)}")
    if extraction_result.warnings:
        for w in extraction_result.warnings[:10]:
            print(f"  - {w}")
        if len(extraction_result.warnings) > 10:
            print(f"  ... (+{len(extraction_result.warnings) - 10} more)")

    print("\n--- Text sizes ---")
    print(f"Raw chars: {len(extraction_result.raw_text):,}")
    print(f"Cleaned chars: {len(extraction_result.text):,}")

    print("\n--- Chunking/Filtering ---")
    print(f"Candidate chunks: {len(chunking_result.chunks)}")
    print(f"Dropped by hard filter: {len(dropped)}")

    print("\n--- Elimination Gate ---")
    print(f"Elite chunks: {elimination_result.total_elite}")
    print(f"Eliminated by signal: {elimination_result.eliminated_by_signal}")
    print(f"Eliminated by ranking: {elimination_result.eliminated_by_ranking}")
    print(f"Low yield: {elimination_result.is_low_yield}")
    print(f"Axis distribution: {elimination_result.axis_distribution}")

    if elimination_result.elite_chunks:
        print("\n--- Elite Chunk Scores (first 5) ---")
        for i, scored_chunk in enumerate(elimination_result.elite_chunks[:5]):
            print(f"\n[{i+1}] Qualified axes: {scored_chunk.qualified_axes}")
            print(
                f"    Scores: P={scored_chunk.scores.punch} I={scored_chunk.scores.identity} "
                f"T={scored_chunk.scores.tension} Q={scored_chunk.scores.quotability} "
                f"N={scored_chunk.scores.novelty} (Total: {scored_chunk.scores.total})"
            )
            print(f"    Preview: {scored_chunk.chunk.text[:150]}...")
        print(
            "*******************************************************************************"
        )
        print(
            "*******************************************************************************"
        )
        print(
            "*******************************************************************************"
        )
        # print(elimination_result.elite_chunks)
