"""
Stage B: Multi-Axis Scoring (WITH FIXES).

Every chunk gets scored 0-100 on 5 independent axes:
- PUNCH: First TWO sentences stopping power (max of sentence 1 or 2)
- IDENTITY: Tribal/superiority + identity cost patterns
- TENSION: Contrast/negation + moral blame vector
- QUOTABILITY: Extractable quotes with specificity penalty
- NOVELTY: (Handled separately in embeddings.py, with conditional penalty)
"""

import re
from dataclasses import dataclass
from typing import List, Set

from app.ingestion.reservoir.elimination.signals import EMOTIONAL_WORDS


# ============================================================================
# Identity Cost Patterns (forced value alignment / implied reader fault)
# ============================================================================

IDENTITY_COST_PATTERNS: List[str] = [
    r"if you (care|respect yourself)",
    r"people who (stay|settle)",
    r"this is why you feel stuck",
    r"most advice fails because",
    r"you're not unlucky",
    r"you're not lazy",
    r"it's not about (luck|talent)",
    r"the reason you (fail|struggle|can't)",
]

# ============================================================================
# Blame Terms for Moral Tension Detection
# ============================================================================

BLAME_TERMS: Set[str] = {"you", "they", "society", "culture", "schools", "parents", "system", "world"}

# ============================================================================
# Quotability Specificity - Concrete nouns and action verbs
# ============================================================================

CONCRETE_NOUNS: Set[str] = {
    "time", "money", "work", "job", "habits", "people", "decisions", "life",
    "hours", "days", "years", "energy", "focus", "attention", "results",
    "goals", "success", "failure", "pain", "fear", "brain", "mind", "body",
    "morning", "night", "routine", "task", "project", "deadline", "boss",
    "family", "friends", "health", "wealth", "career", "business", "skill",
}

ACTION_VERBS: Set[str] = {
    "stop", "start", "build", "avoid", "choose", "quit", "leave", "make",
    "take", "give", "do", "change", "create", "destroy", "break", "fix",
    "learn", "teach", "grow", "shrink", "win", "lose", "fight", "run",
    "focus", "ignore", "accept", "reject", "embrace", "resist", "commit",
}


@dataclass
class AxisScores:
    """Scores for the 5 viral axes (0-100 each)."""
    punch: int = 0
    identity: int = 0
    tension: int = 0
    quotability: int = 0
    novelty: int = 0
    
    @property
    def total(self) -> int:
        return self.punch + self.identity + self.tension + self.quotability + self.novelty
    
    def to_dict(self) -> dict:
        return {
            "punch": self.punch,
            "identity": self.identity,
            "tension": self.tension,
            "quotability": self.quotability,
            "novelty": self.novelty,
            "total": self.total,
        }


def _score_single_sentence_punch(sentence: str, full_chunk: str) -> int:
    """Score a single sentence for punch (used internally)."""
    first_50_words = " ".join(full_chunk.split()[:50]).lower()
    sentence_lower = sentence.lower()
    
    score = 0
    
    # Emotional vocabulary density (max 30 points)
    words = set(re.findall(r'\b\w+\b', first_50_words))
    emotion_hits = len(words & EMOTIONAL_WORDS)
    score += min(emotion_hits * 10, 30)
    
    # Contrast/tension words (max 30 points)
    contrast_words = ["but", "yet", "however", "instead", "actually", "really"]
    contrast_hits = sum(1 for w in contrast_words if f" {w} " in f" {first_50_words} ")
    score += min(contrast_hits * 15, 30)
    
    # Direct address (20 points)
    if " you " in first_50_words or first_50_words.startswith("you"):
        score += 20
    
    # Short punchy sentence < 15 words (20 points)
    if len(sentence.split()) < 15:
        score += 20
    
    return min(score, 100)


def score_punch(chunk: str) -> int:
    """
    Score 0-100 for first-impression stopping power.
    
    FIX: Evaluates FIRST TWO sentences, takes max score.
    
    Measures:
    - Emotional vocabulary density in first 50 words
    - Contrast/tension words presence
    - Direct address ("you")
    - Short punchy opener (<15 words)
    """
    sentences = [s.strip() for s in chunk.split(". ") if s.strip()]
    
    if not sentences:
        return 0
    
    # Score first sentence
    score1 = _score_single_sentence_punch(sentences[0], chunk)
    
    # Score second sentence if exists
    score2 = 0
    if len(sentences) > 1:
        score2 = _score_single_sentence_punch(sentences[1], chunk)
    
    # Return max of first two sentences
    return max(score1, score2)


def score_identity(chunk: str) -> int:
    """
    Score 0-100 for "sharing this says something about me" potential.
    
    FIX: Added identity cost patterns for forced value alignment.
    
    Measures:
    - Tribal markers (us vs them language)
    - Superiority/aspiration signals
    - Identity cost patterns (implied reader fault)
    """
    text = chunk.lower()
    
    score = 0
    
    # Tribal markers (max 60 points)
    tribal_phrases = [
        "most people", "few people", "the difference between",
        "successful people", "the best", "the worst",
        "winners", "losers", "those who", "the ones who",
        "amateurs", "professionals", "beginners", "masters",
        "average", "exceptional", "ordinary", "extraordinary",
        "the masses", "the elite", "common mistake",
    ]
    for phrase in tribal_phrases:
        if phrase in text:
            score += 12
    
    # Superiority/aspiration signals (max 40 points)
    aspiration_words = [
        "elite", "rare", "secret", "hidden", "real", "truth",
        "exclusive", "insider", "few know", "most miss",
        "counterintuitive", "surprising", "unexpected",
    ]
    for word in aspiration_words:
        if word in text:
            score += 8
    
    # FIX: Identity cost patterns - implied reader fault / forced alignment (+20 bonus)
    for pattern in IDENTITY_COST_PATTERNS:
        if re.search(pattern, text):
            score += 20
            break  # Only apply bonus once
    
    return min(score, 100)


def score_tension(chunk: str) -> int:
    """
    Score 0-100 for psychological discomfort/friction.
    
    FIX: Added moral blame vector detection.
    
    Measures:
    - Contrast density (but, yet, however)
    - Negation patterns (not, never, don't)
    - Paradox structures
    - Questions implying reader is wrong
    - Moral blame (blame terms near negation/contrast)
    """
    text = chunk.lower()
    
    score = 0
    
    # Contrast density (max 36 points)
    contrast_words = ["but", "yet", "however", "although", "despite", "instead"]
    contrast_count = sum(text.count(f" {w} ") for w in contrast_words)
    score += min(contrast_count * 12, 36)
    
    # Negation patterns (max 24 points)
    negations = ["not", "don't", "doesn't", "never", "no one", "nothing", "nobody"]
    negation_count = sum(text.count(w) for w in negations)
    score += min(negation_count * 8, 24)
    
    # Paradox structures (20 points)
    if re.search(r"the more .{5,30}, the (less|more)", text):
        score += 20
    
    # Question implying reader is wrong (20 points)
    if re.search(r"\?.*you (think|believe|assume)", text):
        score += 20
    
    # FIX: Moral blame vector - blame term near negation/contrast (+15 bonus)
    # Check if any blame term appears within 50 chars of a negation or contrast
    has_blame_near_tension = False
    for blame_term in BLAME_TERMS:
        if blame_term not in text:
            continue
        # Find positions of blame term
        for match in re.finditer(rf'\b{blame_term}\b', text):
            pos = match.start()
            # Check 50 chars before and after for negation/contrast
            context = text[max(0, pos-50):min(len(text), pos+50)]
            if any(neg in context for neg in negations) or \
               any(f" {cw} " in f" {context} " for cw in contrast_words):
                has_blame_near_tension = True
                break
        if has_blame_near_tension:
            break
    
    if has_blame_near_tension:
        score += 15
    
    return min(score, 100)


def score_quotability(chunk: str) -> int:
    """
    Score 0-100 for extractable standalone quotes.
    
    FIX: Added specificity penalty for abstract quotes.
    
    Finds the best sentence that could work as a standalone quote/post.
    Penalizes sentences lacking concrete nouns AND action verbs.
    """
    sentences = [s.strip() for s in chunk.split(". ") if len(s.strip()) > 10]
    
    best_sentence_score = 0
    
    for sentence in sentences:
        s_score = 0
        words = sentence.split()
        word_count = len(words)
        sentence_lower = sentence.lower()
        sentence_words = set(re.findall(r'\b\w+\b', sentence_lower))
        
        # Ideal length: 8-20 words (30 points)
        if 8 <= word_count <= 20:
            s_score += 30
        elif word_count < 8:
            s_score += 15
        
        # No context-dependent pronouns at start (20 points)
        context_starters = ("he ", "she ", "it ", "they ", "this ", "that ", "these ", "those ")
        if not sentence_lower.startswith(context_starters):
            s_score += 20
        
        # Has emotional word (25 points)
        if sentence_words & EMOTIONAL_WORDS:
            s_score += 25
        
        # Universal/imperative language (25 points)
        imperative_starters = ["stop", "start", "never", "always", "remember", "forget", "don't", "do"]
        first_word = words[0].lower() if words else ""
        if " you " in sentence_lower or first_word in imperative_starters:
            s_score += 25
        
        # FIX: Specificity penalty - penalize if lacking concrete nouns AND action verbs
        has_concrete = bool(sentence_words & CONCRETE_NOUNS)
        has_action = bool(sentence_words & ACTION_VERBS)
        
        if not has_concrete and not has_action:
            s_score -= 20  # Penalty for abstract "pretty nothingness"
        
        best_sentence_score = max(best_sentence_score, max(0, s_score))
    
    return min(best_sentence_score, 100)


# ============================================================================
# Polarization Threshold for Novelty Penalty
# ============================================================================

POLARIZATION_THRESHOLD = 60  # Combined identity + tension minimum


class AxisScorer:
    """Scores chunks across all 5 viral axes."""
    
    def __init__(self, novelty_scorer=None):
        """
        Initialize scorer.
        
        Args:
            novelty_scorer: Optional NoveltyScorer instance for NOVELTY axis.
                           If None, novelty scores will be 0.
        """
        self.novelty_scorer = novelty_scorer
    
    def score(self, chunk: str) -> AxisScores:
        """
        Score a chunk on all 5 axes.
        
        FIX: Applies conditional novelty penalty if low polarization.
        """
        # Score all axes
        punch = score_punch(chunk)
        identity = score_identity(chunk)
        tension = score_tension(chunk)
        quotability = score_quotability(chunk)
        
        novelty = 0
        if self.novelty_scorer:
            novelty = self.novelty_scorer.score_novelty(chunk)
        
        # FIX: Conditional novelty penalty if low polarization
        combined_polarization = identity + tension
        if combined_polarization < POLARIZATION_THRESHOLD:
            novelty = int(novelty * 0.6)
        
        return AxisScores(
            punch=punch,
            identity=identity,
            tension=tension,
            quotability=quotability,
            novelty=novelty,
        )
    
    def score_batch(self, chunks: List[str]) -> List[AxisScores]:
        """Score multiple chunks."""
        return [self.score(chunk) for chunk in chunks]
