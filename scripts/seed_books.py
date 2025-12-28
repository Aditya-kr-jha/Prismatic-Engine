#!/usr/bin/env python3
"""
Book Seeder Script.

Processes books from books.yaml configuration and seeds them into the
content reservoir for the Prismatic Engine.

Usage:
    # Process all pending books
    python scripts/seed_books.py

    # Process specific book
    python scripts/seed_books.py --file deep-work.pdf

    # Dry run (no DB writes)
    python scripts/seed_books.py --dry-run

    # Verbose logging
    python scripts/seed_books.py --verbose
"""

import argparse
import logging
import shutil
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.db.db_session import get_session
from app.db.enums import (
    EvergreenSourceType,
    EvergreenSourceStatus,
    FileType,
)
from app.ingestion.db_services import (
    get_or_create_evergreen_source,
    get_evergreen_source_by_title,
    update_evergreen_source_status,
    insert_elite_chunks,
)
from app.ingestion.reservoir import PDFExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("seeder")


@dataclass
class BookConfig:
    """Configuration for a single book."""
    title: str
    author: str
    file: str


@dataclass
class ProcessingResult:
    """Result from processing a single book."""
    book: BookConfig
    success: bool
    chunks_extracted: int = 0
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


class BookSeeder:
    """Orchestrates book processing and content reservoir seeding."""

    def __init__(
        self,
        books_dir: Path,
        processed_dir: Path,
        config_path: Path,
        dry_run: bool = False,
    ):
        """
        Initialize seeder.

        Args:
            books_dir: Directory containing book files
            processed_dir: Directory to move processed files
            config_path: Path to books.yaml config
            dry_run: If True, don't write to DB or move files
        """
        self.books_dir = books_dir
        self.processed_dir = processed_dir
        self.config_path = config_path
        self.dry_run = dry_run
        self.extractor = PDFExtractor()

    def load_config(self) -> list[BookConfig]:
        """Load books configuration from YAML."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")

        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        books = []
        for book_data in config.get("books", []):
            books.append(BookConfig(
                title=book_data["title"],
                author=book_data["author"],
                file=book_data["file"],
            ))

        logger.info(f"Loaded {len(books)} books from config")
        return books

    def process_book(self, book: BookConfig) -> ProcessingResult:
        """
        Process a single book through the full pipeline.

        Steps:
            1. Check if already in evergreen_sources (skip if COMPLETED)
            2. Create/update evergreen_sources entry (status=PROCESSING)
            3. Process PDF through extraction pipeline
            4. Insert elite chunks into content_reservoir
            5. Update evergreen_sources (status=COMPLETED)
            6. Move file to /processed
        """
        logger.info(f"Processing: {book.title} by {book.author}")
        
        file_path = self.books_dir / book.file
        
        # Validate file exists
        if not file_path.exists():
            return ProcessingResult(
                book=book,
                success=False,
                error=f"File not found: {file_path}",
            )

        # Determine file type
        file_type = FileType.PDF if file_path.suffix.lower() == ".pdf" else FileType.EPUB

        if self.dry_run:
            logger.info(f"[DRY RUN] Would process: {book.title}")
            # Still run extraction to show what would happen
            try:
                extraction_result, chunking_result, elimination_result, dropped = \
                    self.extractor.process(file_path)
                
                logger.info(
                    f"[DRY RUN] Would extract {elimination_result.total_elite} elite chunks"
                )
                return ProcessingResult(
                    book=book,
                    success=True,
                    chunks_extracted=elimination_result.total_elite,
                )
            except Exception as e:
                return ProcessingResult(
                    book=book,
                    success=False,
                    error=str(e),
                )

        # Real processing with DB
        with next(get_session()) as session:
            try:
                # Step 1: Check if already completed
                existing = get_evergreen_source_by_title(
                    session, book.title, book.author
                )
                
                if existing and existing.status == EvergreenSourceStatus.COMPLETED:
                    logger.info(f"Skipping (already completed): {book.title}")
                    return ProcessingResult(
                        book=book,
                        success=True,
                        skipped=True,
                        skip_reason="Already completed",
                        chunks_extracted=existing.chunks_extracted,
                    )

                # Step 2: Create/update evergreen_sources entry
                source, created = get_or_create_evergreen_source(
                    session=session,
                    source_type=EvergreenSourceType.BOOK,
                    title=book.title,
                    author=book.author,
                    file_path=str(file_path),
                    file_type=file_type,
                )

                if not created:
                    source.status = EvergreenSourceStatus.PROCESSING
                    source.error_message = None
                    session.add(source)
                else:
                    update_evergreen_source_status(
                        session, source.id, EvergreenSourceStatus.PROCESSING
                    )
                
                session.commit()
                logger.info(f"Created/updated source: {source.id}")

                # Step 3: Process PDF
                logger.info(f"Running extraction pipeline...")
                extraction_result, chunking_result, elimination_result, dropped = \
                    self.extractor.process(file_path)

                logger.info(
                    f"Extraction complete: {elimination_result.total_elite} elite chunks, "
                    f"{len(dropped)} dropped by filter"
                )

                # Step 4: Insert elite chunks
                chunks_inserted = insert_elite_chunks(
                    session=session,
                    source_id=source.id,
                    chunks=elimination_result.elite_chunks,
                    source_type=EvergreenSourceType.BOOK.value,
                    source_name=book.title,
                    source_author=book.author,
                )

                # Step 5: Update evergreen_sources
                update_evergreen_source_status(
                    session=session,
                    source_id=source.id,
                    status=EvergreenSourceStatus.COMPLETED,
                    chunks_extracted=chunks_inserted,
                )

                session.commit()
                logger.info(f"Committed {chunks_inserted} chunks to database")

                # Step 6: Move file to processed
                self._move_to_processed(file_path)

                return ProcessingResult(
                    book=book,
                    success=True,
                    chunks_extracted=chunks_inserted,
                )

            except Exception as e:
                session.rollback()
                error_msg = f"{type(e).__name__}: {str(e)}"
                logger.error(f"Failed to process {book.title}: {error_msg}")
                logger.debug(traceback.format_exc())

                # Update source with error
                if existing or 'source' in locals():
                    source_id = existing.id if existing else source.id
                    update_evergreen_source_status(
                        session=session,
                        source_id=source_id,
                        status=EvergreenSourceStatus.FAILED,
                        error_message=error_msg,
                    )
                    session.commit()

                return ProcessingResult(
                    book=book,
                    success=False,
                    error=error_msg,
                )

    def _move_to_processed(self, file_path: Path) -> None:
        """Move processed file to processed directory."""
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        dest = self.processed_dir / file_path.name
        
        if dest.exists():
            # Add timestamp suffix to avoid overwrite
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = self.processed_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
        
        shutil.move(str(file_path), str(dest))
        logger.info(f"Moved to: {dest}")

    def run(self, specific_file: Optional[str] = None) -> list[ProcessingResult]:
        """
        Run seeder on all books or a specific file.

        Args:
            specific_file: If provided, only process this file

        Returns:
            List of ProcessingResult for each book
        """
        books = self.load_config()
        
        if specific_file:
            books = [b for b in books if b.file == specific_file]
            if not books:
                logger.error(f"File not found in config: {specific_file}")
                return []

        results: list[ProcessingResult] = []
        
        for book in books:
            result = self.process_book(book)
            results.append(result)

        return results


def print_summary(results: list[ProcessingResult]) -> None:
    """Print processing summary."""
    total = len(results)
    successful = sum(1 for r in results if r.success and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)
    failed = sum(1 for r in results if not r.success)
    total_chunks = sum(r.chunks_extracted for r in results if r.success)

    print("\n" + "=" * 60)
    print("SEEDING SUMMARY")
    print("=" * 60)
    print(f"Total books:     {total}")
    print(f"Successful:      {successful}")
    print(f"Skipped:         {skipped}")
    print(f"Failed:          {failed}")
    print(f"Total chunks:    {total_chunks}")
    print("=" * 60)

    if failed > 0:
        print("\nFailed books:")
        for r in results:
            if not r.success:
                print(f"  - {r.book.title}: {r.error}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Seed books into content reservoir",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Process only this specific file (must be in books.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run extraction but don't write to DB or move files",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--books-dir",
        type=Path,
        default=project_root / "Books",
        help="Directory containing book files",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=project_root / "Books" / "processed",
        help="Directory to move processed files",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "scripts" / "books.yaml",
        help="Path to books.yaml config file",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("seeder").setLevel(logging.DEBUG)

    if args.dry_run:
        logger.info("DRY RUN MODE - No database writes or file moves")

    seeder = BookSeeder(
        books_dir=args.books_dir,
        processed_dir=args.processed_dir,
        config_path=args.config,
        dry_run=args.dry_run,
    )

    try:
        results = seeder.run(specific_file=args.file)
        print_summary(results)
        
        # Exit with error code if any failed
        if any(not r.success for r in results):
            sys.exit(1)
            
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(2)
    except Exception as e:
        logger.exception(f"Seeder failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
