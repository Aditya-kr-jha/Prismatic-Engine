#!/usr/bin/env python3
"""
Reservoir Harvester Verification Script.

Usage:
    # Check statistics (no changes)
    python scripts/verify_reservoir_harvest.py --stats
    
    # Dry-run with 6 items (preview only)
    python scripts/verify_reservoir_harvest.py --dry-run --count 6
    
    # Actual harvest with 6 items
    python scripts/verify_reservoir_harvest.py --harvest --count 6
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.db_session import get_session
from app.ingestion.service import IngestionService
from app.ingestion.db_services import count_ingest_by_status
from app.db.enums import IngestStatus, ReservoirStatus
from app.infra.http.generic import GenericHTTPClient
from sqlmodel import select, func
from app.db.db_models.pre_ingestion import ContentReservoir

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def show_statistics():
    """Show current reservoir and raw_ingest statistics."""
    print("\n" + "=" * 60)
    print("RESERVOIR STATISTICS")
    print("=" * 60)
    
    service = IngestionService(http_client=GenericHTTPClient())
    stats = service.get_reservoir_statistics()
    
    print("\nContentReservoir by source_type:")
    for source_type, count in stats.get("by_source_type", {}).items():
        print(f"  {source_type}: {count} AVAILABLE")
    
    print("\nContentReservoir by status:")
    for status, count in stats.get("by_status", {}).items():
        print(f"  {status}: {count}")
    
    with next(get_session()) as session:
        pending_count = count_ingest_by_status(session, IngestStatus.PENDING)
        print(f"\nRawIngest PENDING count: {pending_count}")
    
    print("=" * 60 + "\n")


def run_harvest(count: int, dry_run: bool):
    """Run the reservoir harvest."""
    action = "DRY-RUN" if dry_run else "HARVEST"
    print(f"\n{'=' * 60}")
    print(f"{action} - Target: {count} items")
    print("=" * 60)
    
    # Pre-check
    with next(get_session()) as session:
        pending_before = count_ingest_by_status(session, IngestStatus.PENDING)
        
        stmt = select(func.count()).where(ContentReservoir.status == ReservoirStatus.QUEUED)
        queued_before = session.exec(stmt).one()
    
    print(f"\nBefore harvest:")
    print(f"  RawIngest PENDING: {pending_before}")
    print(f"  ContentReservoir QUEUED: {queued_before}")
    
    # Run harvest
    service = IngestionService(http_client=GenericHTTPClient())
    result = service.harvest_from_reservoir(total_content=count, dry_run=dry_run)
    
    print(f"\nHarvest result:")
    print(f"  Items fetched: {result.items_fetched}")
    print(f"  By source type: {result.by_source_type}")
    
    if not dry_run:
        print(f"  Items queued: {result.items_queued}")
        print(f"  Items transferred: {result.items_transferred}")
        print(f"  Items skipped: {result.items_skipped}")
        
        # Post-check
        with next(get_session()) as session:
            pending_after = count_ingest_by_status(session, IngestStatus.PENDING)
            
            stmt = select(func.count()).where(ContentReservoir.status == ReservoirStatus.QUEUED)
            queued_after = session.exec(stmt).one()
        
        print(f"\nAfter harvest:")
        print(f"  RawIngest PENDING: {pending_after} (+{pending_after - pending_before})")
        print(f"  ContentReservoir QUEUED: {queued_after} (+{queued_after - queued_before})")
    
    print(f"\nDuration: {result.duration_seconds:.2f}s")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Verify reservoir harvester implementation"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show current statistics (no changes)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview what would be harvested without making changes"
    )
    parser.add_argument(
        "--harvest", action="store_true",
        help="Actually perform the harvest"
    )
    parser.add_argument(
        "--count", type=int, default=6,
        help="Number of items to harvest (default: 6)"
    )
    
    args = parser.parse_args()
    
    if args.stats:
        show_statistics()
    elif args.dry_run:
        run_harvest(args.count, dry_run=True)
    elif args.harvest:
        confirm = input(f"This will transfer {args.count} items to raw_ingest. Continue? [y/N] ")
        if confirm.lower() == 'y':
            run_harvest(args.count, dry_run=False)
        else:
            print("Cancelled.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
