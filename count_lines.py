#!/usr/bin/env python3
"""
Line of Code Counter for Prismatic-Engine

This script counts the lines of code written by the developer,
excluding pre-generated files like:
- Alembic migrations
- __pycache__ directories
- .git, .idea directories
- poetry.lock, .env files
- Empty lines and comment-only lines (optional)
"""

import os
from pathlib import Path
from collections import defaultdict

# Project root
PROJECT_ROOT = Path(__file__).parent

# Directories to scan (your actual code)
INCLUDE_DIRS = [
    "app",
    "scripts",
]

# Patterns/directories to exclude
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".git",
    ".idea",
    "alembic/versions",  # Auto-generated migrations
    ".env",
    "*.pyc",
    ".DS_Store",
]

# File extensions to count
CODE_EXTENSIONS = {".py", ".yaml", ".yml"}


def should_exclude(path: Path) -> bool:
    """Check if a path should be excluded from counting."""
    path_str = str(path)
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return True
    return False


def count_lines_in_file(file_path: Path) -> dict:
    """
    Count different types of lines in a file.
    
    Returns:
        dict with keys: total, code, blank, comment
    """
    stats = {"total": 0, "code": 0, "blank": 0, "comment": 0}
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            in_multiline_string = False
            for line in f:
                stats["total"] += 1
                stripped = line.strip()
                
                # Blank line
                if not stripped:
                    stats["blank"] += 1
                # Comment line (Python)
                elif stripped.startswith("#"):
                    stats["comment"] += 1
                # Docstring detection (simple heuristic)
                elif stripped.startswith('"""') or stripped.startswith("'''"):
                    if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                        stats["comment"] += 1
                    else:
                        in_multiline_string = not in_multiline_string
                        stats["comment"] += 1
                elif in_multiline_string:
                    stats["comment"] += 1
                    if '"""' in stripped or "'''" in stripped:
                        in_multiline_string = False
                else:
                    stats["code"] += 1
    except Exception as e:
        print(f"  ⚠️  Error reading {file_path}: {e}")
    
    return stats


def scan_directory(directory: Path) -> dict:
    """Scan a directory and return file statistics."""
    results = defaultdict(lambda: {"files": 0, "total": 0, "code": 0, "blank": 0, "comment": 0})
    
    for root, dirs, files in os.walk(directory):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d)]
        
        for file in files:
            file_path = Path(root) / file
            
            if should_exclude(file_path):
                continue
            
            ext = file_path.suffix.lower()
            if ext not in CODE_EXTENSIONS:
                continue
            
            stats = count_lines_in_file(file_path)
            results[ext]["files"] += 1
            for key in ["total", "code", "blank", "comment"]:
                results[ext][key] += stats[key]
    
    return dict(results)


def print_summary(all_results: dict, detailed: bool = True):
    """Print a formatted summary of the line counts."""
    
    print("\n" + "=" * 60)
    print("📊 PRISMATIC-ENGINE: Lines of Code Summary")
    print("=" * 60)
    
    grand_total = {"files": 0, "total": 0, "code": 0, "blank": 0, "comment": 0}
    
    for dir_name, results in all_results.items():
        print(f"\n📁 {dir_name}/")
        print("-" * 40)
        
        dir_total = {"files": 0, "total": 0, "code": 0, "blank": 0, "comment": 0}
        
        for ext, stats in sorted(results.items()):
            if detailed:
                print(f"  {ext:8} │ {stats['files']:3} files │ {stats['code']:5} code │ {stats['total']:5} total")
            for key in dir_total:
                dir_total[key] += stats[key]
                grand_total[key] += stats[key]
        
        print(f"  {'SUBTOTAL':8} │ {dir_total['files']:3} files │ {dir_total['code']:5} code │ {dir_total['total']:5} total")
    
    print("\n" + "=" * 60)
    print("🎯 GRAND TOTAL")
    print("=" * 60)
    print(f"""
  📄 Total Files:      {grand_total['files']}
  📝 Total Lines:      {grand_total['total']}
  💻 Lines of Code:    {grand_total['code']}
  📭 Blank Lines:      {grand_total['blank']}
  💬 Comment Lines:    {grand_total['comment']}
  
  ✨ Code Density:     {grand_total['code'] / max(grand_total['total'], 1) * 100:.1f}%
""")
    print("=" * 60)
    
    return grand_total


def main():
    print("\n🔍 Scanning project for lines of code...")
    print("   (Excluding: alembic migrations, __pycache__, .git, .idea, .env)")
    
    all_results = {}
    
    for dir_name in INCLUDE_DIRS:
        dir_path = PROJECT_ROOT / dir_name
        if dir_path.exists():
            all_results[dir_name] = scan_directory(dir_path)
        else:
            print(f"  ⚠️  Directory not found: {dir_name}")
    
    totals = print_summary(all_results)
    
    print(f"\n🚀 You've written {totals['code']:,} lines of actual code!")
    print("   Keep building! 💪\n")


if __name__ == "__main__":
    main()
