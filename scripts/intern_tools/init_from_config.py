#!/usr/bin/env python3
"""
Initialize or Update the Intake System from Blog Authors Config.

SAFE TO RERUN: This script merges with existing data instead of overwriting.
- Existing authors are preserved (only updates if --force)
- Learned URL patterns are preserved
- New authors are added with stable slug-based IDs

Usage:
    python scripts/intern_tools/init_from_config.py          # Merge mode (safe)
    python scripts/intern_tools/init_from_config.py --force  # Full reset (destructive)
    python scripts/intern_tools/init_from_config.py --dry-run # Preview changes
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# Import directly from authors_config to avoid ingestion package chain
import importlib.util

authors_config_path = project_root / "scripts" / "authors_config.py"
spec = importlib.util.spec_from_file_location("authors_config", authors_config_path)
authors_config = importlib.util.module_from_spec(spec)
sys.modules["authors_config"] = authors_config
spec.loader.exec_module(authors_config)
AUTHORS = authors_config.AUTHORS


# ---------- PATHS ----------
DATA_DIR = project_root / "data"
AUTHORS_FILE = DATA_DIR / "authors.json"
TRACKER_FILE = DATA_DIR / "tracker.json"


def slugify(name: str) -> str:
    """
    Convert author name to stable slug ID.
    
    Examples:
        "Tim Urban" -> "tim_urban"
        "Alain de Botton (Relationships)" -> "alain_de_botton_relationships"
    """
    # Lowercase and replace special chars
    slug = name.lower()
    slug = re.sub(r"[''`]", "", slug)  # Remove apostrophes
    slug = re.sub(r"[^a-z0-9]+", "_", slug)  # Replace non-alphanumeric with underscore
    slug = slug.strip("_")  # Remove leading/trailing underscores
    return slug


def extract_domain_patterns(blog_url: str) -> list[str]:
    """
    Extract multiple URL patterns for matching.

    Args:
        blog_url: Blog URL to extract patterns from

    Returns:
        List of domain patterns for URL matching
    """
    parsed = urlparse(blog_url)
    domain = parsed.netloc.lower().replace("www.", "")

    patterns = [domain]

    # Add base domain without subdomains
    parts = domain.split(".")
    if len(parts) > 2:
        # e.g., "sahilbloom.substack.com" → also match "sahilbloom"
        patterns.append(parts[0])

    # For substack, add the subdomain alone
    if "substack.com" in domain:
        subdomain = domain.replace(".substack.com", "")
        patterns.append(subdomain)

    return patterns


def load_existing_authors() -> dict:
    """Load existing authors.json if it exists."""
    if AUTHORS_FILE.exists():
        try:
            return json.loads(AUTHORS_FILE.read_text())
        except json.JSONDecodeError:
            print("⚠️  Existing authors.json is corrupted, will create fresh")
    return {"authors": {}, "url_patterns": {}}


def main() -> None:
    """Generate or merge authors.json from authors_config.py."""
    
    # Parse arguments
    args = sys.argv[1:]
    force_mode = "--force" in args
    dry_run = "--dry-run" in args

    print("\n" + "=" * 60)
    if force_mode:
        print("🔧 INITIALIZING FROM CONFIG (FORCE MODE - FULL RESET)")
    elif dry_run:
        print("🔍 DRY RUN - Previewing changes")
    else:
        print("🔧 MERGING WITH EXISTING AUTHORS CONFIG")
    print("=" * 60)

    # Ensure directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing data (empty if force mode or doesn't exist)
    if force_mode:
        existing_data = {"authors": {}, "url_patterns": {}}
        print("\n⚠️  Force mode: existing data will be replaced")
    else:
        existing_data = load_existing_authors()
        if existing_data["authors"]:
            print(f"\n📂 Loaded {len(existing_data['authors'])} existing authors")
            print(f"   {len(existing_data['url_patterns'])} URL patterns")

    # Build new data structure with slug-based IDs
    new_authors: dict = {}
    new_url_patterns: dict = {}
    
    # Track changes
    added = []
    updated = []
    preserved = []

    for author in AUTHORS:
        name = author["name"]
        author_id = slugify(name)
        blog_url = author["blog_url"]
        platform = (
            author["platform"].value
            if hasattr(author["platform"], "value")
            else str(author["platform"])
        )
        pillars = [
            p.value if hasattr(p, "value") else str(p)
            for p in author["content_pillars"]
        ]
        max_articles = author["max_articles"]

        author_entry = {
            "name": name,
            "blog_url": blog_url,
            "platform": platform,
            "pillars": pillars,
            "max_articles": max_articles,
        }

        # Check if author already exists
        if author_id in existing_data["authors"]:
            # Preserve existing entry (don't overwrite)
            new_authors[author_id] = existing_data["authors"][author_id]
            preserved.append(author_id)
        else:
            # Add new author
            new_authors[author_id] = author_entry
            added.append(author_id)

        # Build URL patterns (from config)
        for pattern in extract_domain_patterns(blog_url):
            new_url_patterns[pattern] = author_id

    # Merge URL patterns: preserve user-added patterns
    merged_url_patterns = dict(existing_data.get("url_patterns", {}))
    
    # Add new patterns (won't overwrite existing user mappings)
    for pattern, author_id in new_url_patterns.items():
        if pattern not in merged_url_patterns:
            merged_url_patterns[pattern] = author_id

    # Build final data
    final_data = {
        "authors": new_authors,
        "url_patterns": merged_url_patterns,
    }

    # Report changes
    print(f"\n📊 Changes:")
    print(f"   ✅ Added: {len(added)} new authors")
    if added:
        for aid in added[:5]:  # Show first 5
            print(f"      + {aid}")
        if len(added) > 5:
            print(f"      ... and {len(added) - 5} more")
    
    print(f"   📂 Preserved: {len(preserved)} existing authors")
    print(f"   🔗 URL patterns: {len(merged_url_patterns)} total")

    if dry_run:
        print("\n🔍 DRY RUN - No changes written")
        print("   Run without --dry-run to apply changes")
        return

    # Save authors.json
    AUTHORS_FILE.write_text(json.dumps(final_data, indent=2))
    print(f"\n✅ Saved to {AUTHORS_FILE}")

    # Initialize tracker if doesn't exist
    if not TRACKER_FILE.exists():
        tracker = {
            "urls": {},
            "stats": {
                "total": 0,
                "by_author": {},
            },
        }
        TRACKER_FILE.write_text(json.dumps(tracker, indent=2))
        print(f"✅ Created tracker at {TRACKER_FILE}")
    else:
        print(f"ℹ️  Tracker already exists at {TRACKER_FILE}")

    # Print summary by platform
    print("\n📊 Authors by Platform:")
    platforms: dict[str, int] = {}
    for author in AUTHORS:
        p = (
            author["platform"].value
            if hasattr(author["platform"], "value")
            else str(author["platform"])
        )
        platforms[p] = platforms.get(p, 0) + 1

    for platform, count in platforms.items():
        print(f"   {platform}: {count}")

    target_articles = sum(a["max_articles"] for a in AUTHORS)
    print(f"\n🎯 Target articles: {target_articles}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
