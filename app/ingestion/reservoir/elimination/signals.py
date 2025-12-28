"""
Stage A: Hard Signal Detection (RELAXED VERSION).

Binary elimination using regex + keyword + structural heuristics.
Chunks without viral surface are eliminated.

RELAXED for educational/non-fiction content:
- Only 1 signal required (was 2)
- Explanation threshold raised to 50% (was 40%)
- Expanded emotional vocabulary for professional content
"""

import re
from typing import Set, List

# Explainer sentence starters (>50% = explanation-heavy)
EXPLAINER_STARTERS: List[str] = [
    r"^this is because\b",
    r"^the reason (is|being|for)\b",
    r"^for example\b",
    r"^in other words\b",
    r"^to (understand|illustrate|explain)\b",
    r"^as (mentioned|discussed|noted)\b",
    r"^consider (the|how|why)\b",
    r"^let me explain\b",
]

# Emotional vocabulary - EXPANDED for professional/productivity content
EMOTIONAL_WORDS: Set[str] = {
    # Original intense words
    "pain", "fear", "anxiety", "stress", "worry", "panic", "dread",
    "terrified", "scared", "desperate", "trapped", "stuck", "lost",
    "obsess", "crave", "desire", "want", "need", "yearn", "hunger",
    "addicted", "compelled", "driven", "consumed",
    "hate", "anger", "rage", "frustration", "disgust", "shame",
    "guilt", "regret", "jealousy", "envy", "bitter", "resentment",
    "love", "joy", "hope", "pride", "confident", "free", "relief",
    "excited", "passionate", "inspired", "grateful",
    "secret", "truth", "lie", "hidden", "reveal", "expose", "discover",
    "mistake", "fail", "destroy", "ruin", "transform", "breakthrough",
    "never", "always", "forever", "impossible", "guaranteed",
    "dangerous", "wrong", "real", "ignore", "cost", "lose",
    "hard", "difficult", "easy", "simple", "important", "critical",
    "must", "struggle", "fight", "win", "success",
    
    # Professional/productivity vocabulary
    "distraction", "focus", "shallow", "deep", "valuable", "rare",
    "urgent", "busy", "productive", "wasted", "meaningless",
    "meaningful", "significant", "trivial", "crucial", "essential",
    "overwhelm", "clarity", "confusion", "purpose", "impact",
    "mediocre", "exceptional", "ordinary", "extraordinary", "elite",
    "effort", "reward", "sacrifice", "commitment",
    "resist", "temptation", "discipline", "willpower", "habit",
    "change", "impossible", "powerful", "weak", "strength",
}

# Strong opener words/phrases
STRONG_OPENER_WORDS: Set[str] = {
    "you", "your", "most", "few", "the problem", "the truth", "the real",
    "here's", "this is", "what", "why", "how", "imagine", "consider",
    "stop", "start", "never", "always", "don't", "if you",
}

# Instant-kill patterns (keep strict)
KILL_PATTERNS: List[str] = [
    # Meta/structural
    r"^this chapter\b",
    r"^in (this|the following) section\b",
    r"^let('s| us) (begin|start) (by|with)\b",
    r"^(table|figure|chart) \d",
    r"as mentioned earlier",
    r"as we (discussed|saw|learned|noted)",
    r"in (the )?(previous|next|following) (chapter|section)",
    
    # Copyright/publishing boilerplate
    r"copyright( act)?.*\d{4}",
    r"all rights reserved",
    r"permission of the publisher",
    r"without (the )?(prior )?(written )?permission",
    r"scanning.*uploading.*electronic sharing",
    r"ISBN[:\s]*[\d\-]+",
    r"Library of Congress",
    r"Printed in (the )?United States",
    r"First (published|edition|printing)",
]

# Anti-patterns that aren't instant kill but reduce score
ANTI_PATTERNS: List[str] = [
    r"is defined as",
    r"can be defined as",
]

# Compiled patterns for performance
_explainer_patterns = [re.compile(p, re.IGNORECASE) for p in EXPLAINER_STARTERS]
_kill_patterns = [re.compile(p, re.IGNORECASE) for p in KILL_PATTERNS]


def has_viral_surface(chunk: str) -> bool:
    """
    Stage A: Determine if chunk has minimum viral potential.
    
    RELAXED VERSION:
    - Only 1 signal required (was 2)
    - Explanation threshold raised to 50% (was 40%)
    - Expanded emotional/professional vocabulary
    
    Args:
        chunk: The text chunk to evaluate
        
    Returns:
        True if chunk has viral potential, False if it should be eliminated
    """
    chunk_lower = chunk.lower()
    sentences = [s.strip() for s in chunk.split(". ") if s.strip()]
    
    if not sentences:
        return False
    
    first_sentence = sentences[0].lower()
    first_100_words = " ".join(chunk.split()[:100]).lower()
    
    # INSTANT KILL (keep strict)
    for pattern in _kill_patterns:
        if pattern.search(first_sentence):
            return False
    
    # Count signals (RELAXED: need only 1)
    signals = 0
    
    # Question anywhere in first 2 sentences
    first_two = ". ".join(sentences[:2])
    if "?" in first_two:
        signals += 1
    
    # Direct address ("you")
    if " you " in first_100_words or first_sentence.startswith("you"):
        signals += 1
    
    # Contrast/tension words in first 100
    contrast_words = ["but", "yet", "however", "instead", "actually", "really"]
    if any(f" {w} " in f" {first_100_words} " for w in contrast_words):
        signals += 1
    
    # Emotional vocabulary in first 100 (need 2+ hits)
    word_set = set(re.findall(r'\b\w+\b', first_100_words))
    emotional_hits = len(word_set & EMOTIONAL_WORDS)
    if emotional_hits >= 2:
        signals += 1
    
    # Strong opener phrases
    if any(phrase in first_sentence for phrase in STRONG_OPENER_WORDS):
        signals += 1
    
    # Short punchy first sentence (<=20 words)
    if len(first_sentence.split()) <= 20:
        signals += 1
    
    # RELAXED: Only need 1 signal (was 2)
    has_signal = signals >= 1
    
    # Check for explanation dominance (RELAXED: threshold 50%, was 40%)
    explainer_count = sum(
        1 for s in sentences
        if any(p.match(s.strip().lower()) for p in _explainer_patterns)
    )
    explanation_heavy = len(sentences) > 3 and (explainer_count / len(sentences)) > 0.50
    
    return has_signal and not explanation_heavy
