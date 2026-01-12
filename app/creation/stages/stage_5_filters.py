"""
Stage 5: Hard Filters.

Automated validation checks that require no LLM:
1. Character limits per format
2. Prohibited phrase scan (AI voice detection)
3. Semicolon detection
4. Opening strength check (no weak openers)
5. Ending check (no summary endings)
"""

from typing import List, Union

from app.creation.schemas import (
    CarouselContent,
    HardFilterResult,
    QuoteContent,
    ReelContent,
)

# Type alias for content
GeneratedContent = Union[ReelContent, CarouselContent, QuoteContent]


# ============================================================================
# PROHIBITED PHRASES
# ============================================================================

PROHIBITED_PHRASES = []

WEAK_OPENERS = []

SUMMARY_ENDINGS = [
    "to sum up",
    "the takeaway",
    "remember,",
    "so remember",
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def extract_full_text(content: GeneratedContent) -> str:
    """Extract all text from content for scanning."""
    if isinstance(content, ReelContent):
        body_text = " ".join(content.body) if content.body else ""
        return f"{content.hook_line} {body_text} {content.punch_line}"
    elif isinstance(content, CarouselContent):
        texts = []
        for slide in content.slides:
            texts.append(slide.headline)
            if slide.body:
                texts.append(slide.body)
        return " ".join(texts)
    elif isinstance(content, QuoteContent):
        return f"{content.quote_text} {content.quote_text_alt}"
    return ""


def get_first_line(content: GeneratedContent) -> str:
    """Get the first line/hook for opener strength check."""
    if isinstance(content, ReelContent):
        return content.hook_line
    elif isinstance(content, CarouselContent):
        if content.slides:
            return content.slides[0].headline
        return ""
    elif isinstance(content, QuoteContent):
        return (
            content.quote_text.split(".")[0]
            if "." in content.quote_text
            else content.quote_text
        )
    return ""


def get_last_line(content: GeneratedContent) -> str:
    """Get the last line for ending strength check."""
    if isinstance(content, ReelContent):
        return content.punch_line
    elif isinstance(content, CarouselContent):
        if content.slides:
            last_slide = content.slides[-1]
            return last_slide.body if last_slide.body else last_slide.headline
        return ""
    elif isinstance(content, QuoteContent):
        parts = content.quote_text.split(".")
        return parts[-1].strip() if parts else content.quote_text
    return ""


# ============================================================================
# HARD FILTER CHECKS
# ============================================================================


def check_character_limits(
    content: GeneratedContent,
    format_type: str,
) -> List[str]:
    """Check character limits by format. Returns list of failures."""
    failures = []

    if format_type == "REEL":
        # Full script limit
        body_text = (
            " ".join(content.body) if hasattr(content, "body") and content.body else ""
        )
        full_script = f"{content.hook_line} {body_text} {content.punch_line}"
        if len(full_script) > 2200:
            failures.append(
                f"REEL_OVER_CHAR_LIMIT: {len(full_script)} chars (max 2200)"
            )

    elif format_type == "CAROUSEL":
        # Per-slide limits
        for slide in content.slides:
            slide_text = slide.headline + (slide.body or "")
            if len(slide_text) > 300:
                failures.append(
                    f"SLIDE_{slide.slide_number}_OVER_LIMIT: {len(slide_text)} chars (max 300)"
                )
        # Slide count
        if len(content.slides) < 5:
            failures.append(
                f"CAROUSEL_TOO_FEW_SLIDES: {len(content.slides)} slides (min 5)"
            )
        if len(content.slides) > 10:
            failures.append(
                f"CAROUSEL_TOO_MANY_SLIDES: {len(content.slides)} slides (max 10)"
            )

    elif format_type == "QUOTE":
        if len(content.quote_text) > 280:
            failures.append(
                f"QUOTE_OVER_LIMIT: {len(content.quote_text)} chars (max 280)"
            )

    return failures


def check_prohibited_phrases(full_text: str) -> List[str]:
    """Scan for prohibited AI-sounding phrases. Returns list of failures."""
    failures = []
    text_lower = full_text.lower()

    for phrase in PROHIBITED_PHRASES:
        if phrase.lower() in text_lower:
            failures.append(f"PROHIBITED_PHRASE: '{phrase}'")

    return failures


def check_semicolons(full_text: str) -> List[str]:
    """Detect semicolons (academic feel). Returns list of failures."""
    if ";" in full_text:
        count = full_text.count(";")
        return [f"SEMICOLON_DETECTED: {count} found"]
    return []


def check_opener_strength(first_line: str) -> List[str]:
    """Check for weak openers. Returns list of failures."""
    failures = []
    first_line_lower = first_line.lower()

    for opener in WEAK_OPENERS:
        if first_line_lower.startswith(opener):
            failures.append(f"WEAK_OPENER: starts with '{opener}'")
            break  # Only report first match

    return failures


def check_ending_strength(last_line: str) -> List[str]:
    """Check for summary endings. Returns list of failures."""
    failures = []
    last_line_lower = last_line.lower()

    for ending in SUMMARY_ENDINGS:
        if ending in last_line_lower:
            failures.append(f"SUMMARY_ENDING: contains '{ending}'")
            break  # Only report first match

    return failures


# ============================================================================
# MAIN FILTER RUNNER
# ============================================================================


def run_hard_filters(
    content: GeneratedContent,
    format_type: str,
) -> HardFilterResult:
    """
    Run all hard filters on generated content.

    Args:
        content: ReelContent, CarouselContent, or QuoteContent
        format_type: REEL, CAROUSEL, or QUOTE

    Returns:
        HardFilterResult with passed status and failure list
    """
    failures: List[str] = []

    # 1. Character Limits
    failures.extend(check_character_limits(content, format_type))

    # 2. Extract full text for text-based checks
    full_text = extract_full_text(content)

    # 3. Prohibited Phrase Scan
    failures.extend(check_prohibited_phrases(full_text))

    # 4. Semicolon Detection
    failures.extend(check_semicolons(full_text))

    # 5. Opening Strength Check
    first_line = get_first_line(content)
    failures.extend(check_opener_strength(first_line))

    # 6. Ending Check
    last_line = get_last_line(content)
    failures.extend(check_ending_strength(last_line))

    return HardFilterResult(
        passed=len(failures) == 0,
        failures=failures,
    )
