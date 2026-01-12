"""
Prohibited Phrases Filter (Stage 5).

Scans content for banned phrases and patterns:
- AI-sounding language ("As an AI", "I understand", etc.)
- Platform-banned words
- Generic/cliche phrases
- Overly formal language

Placeholder for future implementation.
"""

import re
from typing import Dict, List, Tuple

# Phrases that indicate AI-generated content
AI_VOICE_PHRASES = [
    r"\bAs an AI\b",
    r"\bI understand\b",
    r"\bIt'?s important to\b",
    r"\bLet'?s dive in\b",
    r"\bIn conclusion\b",
    r"\bTo summarize\b",
    r"\bFirstly\b.*\bSecondly\b",
    r"\bIn this article\b",
    r"\bI hope this helps\b",
    r"\bRemember that\b",
    r"\bIt'?s worth noting\b",
    r"\bKey takeaway\b",
]

# Generic cliches to avoid
CLICHE_PHRASES = [
    r"\bAt the end of the day\b",
    r"\bThink outside the box\b",
    r"\bGame changer\b",
    r"\bTake it to the next level\b",
    r"\bLow-hanging fruit\b",
    r"\bSynergy\b",
]


def check_prohibited_phrases(
    text: str,
) -> Tuple[bool, List[str]]:
    """
    Scan text for prohibited phrases.

    Args:
        text: Content text to check

    Returns:
        Tuple of (passes, list of found violations)
    """
    violations = []

    for pattern in AI_VOICE_PHRASES + CLICHE_PHRASES:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(f"Found prohibited pattern: {pattern}")

    return len(violations) == 0, violations
