#!/usr/bin/env python3
"""
Initialize the Intake System from Blog Authors Config.

Run once to set up the authors.json and tracker.json files from
the existing authors_config.py configuration.

Usage:
    python scripts/intern_tools/init_from_config.py
"""

import json
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


def main() -> None:
    """Generate authors.json from blog_authors.py config."""

    print("\n" + "=" * 60)
    print("🔧 INITIALIZING FROM BLOG AUTHORS CONFIG")
    print("=" * 60)

    # Ensure directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    authors_data: dict = {
        "authors": {},
        "url_patterns": {},
    }

    for i, author in enumerate(AUTHORS, start=1):
        author_id = f"{i:02d}"  # 01, 02, 03...
        name = author["name"]
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

        authors_data["authors"][author_id] = {
            "name": name,
            "blog_url": blog_url,
            "platform": platform,
            "pillars": pillars,
            "max_articles": max_articles,
        }

        # Add URL patterns
        for pattern in extract_domain_patterns(blog_url):
            authors_data["url_patterns"][pattern] = author_id

        print(f"  {author_id}: {name} ({platform})")

    # Save authors.json
    AUTHORS_FILE.write_text(json.dumps(authors_data, indent=2))
    print(f"\n✅ Saved {len(AUTHORS)} authors to {AUTHORS_FILE}")

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
