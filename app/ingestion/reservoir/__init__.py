"""
Book Source Pipeline - Reservoir Module.

Extracts, cleans, chunks, and filters content from evergreen sources
(books, blogs, podcasts) for the content reservoir.

Main Components:
- PDFExtractor: Extract text from PDF documents
- TextCleaner: Clean and normalize extracted text  
- ParagraphChunker: Split text into paragraph-based chunks
- HardFilter: Rule-based filtering of chunks
- EliteFilter: 4-stage elimination gate for Instagram-viral content
"""

# Schemas (Pydantic models)
from app.ingestion.reservoir.schemas import (
    # Cleaning
    CleaningConfig,
    CleaningStats,
    # Extraction
    ExtractionResult,
    # Chunking
    ChunkingConfig,
    Chunk,
    ChunkingResult,
    # Filtering
    FilterDecision,
    DropReason,
    FilterResult,
)

# PDF Extraction
from app.ingestion.reservoir.pdf_extractor import PDFExtractor

# Text Cleaning
from app.ingestion.reservoir.cleaner import TextCleaner

# Chunking
from app.ingestion.reservoir.chunker import ParagraphChunker

# Filtering
from app.ingestion.reservoir.filter import HardFilter

# Elimination Gate
from app.ingestion.reservoir.elimination import EliteFilter
from app.ingestion.reservoir.elimination.ranking import ScoredChunk, EliminationResult
from app.ingestion.reservoir.elimination.scoring import AxisScores

__all__ = [
    # Schemas
    "CleaningConfig",
    "CleaningStats",
    "ExtractionResult",
    "ChunkingConfig",
    "Chunk",
    "ChunkingResult",
    "FilterDecision",
    "DropReason",
    "FilterResult",
    # Elimination
    "AxisScores",
    "ScoredChunk",
    "EliminationResult",
    # Classes
    "PDFExtractor",
    "TextCleaner",
    "ParagraphChunker",
    "HardFilter",
    "EliteFilter",
]

