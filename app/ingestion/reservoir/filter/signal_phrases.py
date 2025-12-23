"""
Signal phrase patterns for hard filter detection.

Organized by Section C of the Hard Filter spec:
- C1: Academic / Evidence signals
- C2: Contrarian / Observational signals
- C3: Meaning / Generalization signals
- C4: Implicit insight markers

Also includes Section A drop patterns.
"""

from typing import List


# ============================================================================
# SECTION A - ABSOLUTE DROP PATTERNS
# ============================================================================

# A1: Meta / Structural text patterns
META_STRUCTURAL_PATTERNS: List[str] = [
    r"in this chapter we will",
    r"in this chapter,? we",
    r"as discussed earlier",
    r"as mentioned (earlier|above|before|previously)",
    r"in the previous (section|chapter)",
    r"this book will explore",
    r"let us now turn to",
    r"we will (now )?(explore|examine|discuss|consider)",
    r"this (section|chapter) (will )?(cover|discuss|explore)",
    r"as we (will |shall )see",
    r"in the (next|following) (section|chapter)",
    r"to summarize (this|the) (section|chapter)",
    r"before we (proceed|continue|begin)",
]

# A2: Index / Reference / Bibliography patterns
INDEX_REFERENCE_PATTERNS: List[str] = [
    r"\d{1,3}\s*[-–]\s*\d{1,3}",  # Page ranges like "123-145"
    r"\([A-Z][a-z]+,?\s*\d{4}\)",  # Citation like "(Smith, 2020)"
    r"\[\d+\]",  # Numbered citations like "[1]"
    r"ibid\.",
    r"op\.\s*cit\.",
    r"et\s+al\.",
    r"pp?\.\s*\d+",  # Page references like "p. 123"
    r"see\s+also\s+chapter",
    r"cf\.\s+",
]

# A3: Pure biography indicators (without insight)
BIOGRAPHY_PATTERNS: List[str] = [
    r"was born (in|on)",
    r"died (in|on)",
    r"graduated from",
    r"received (his|her|their) (degree|diploma)",
    r"married .+ in \d{4}",
    r"had \d+ children",
    r"moved to .+ in \d{4}",
    r"joined .+ (in|as) \d{4}",
]


# ============================================================================
# SECTION C - SIGNAL DETECTION PATTERNS
# ============================================================================

# C1: Academic / Evidence signals
ACADEMIC_SIGNALS: List[str] = [
    r"research shows",
    r"research (has )?(shown|demonstrated|found|revealed)",
    r"studies (show|suggest|indicate|demonstrate|reveal)",
    r"study (shows?|suggests?|indicates?|found)",
    r"evidence (indicates?|suggests?|shows?)",
    r"data (reveals?|shows?|suggests?|indicates?)",
    r"experiments? (show|demonstrate|reveal|found)",
    r"scientists (have )?(found|discovered|shown)",
    r"researchers (have )?(found|discovered|shown)",
    r"according to (research|studies|data|evidence)",
    r"the (findings|results) (show|indicate|suggest)",
    r"empirical (evidence|research|data)",
    r"meta-analysis",
    r"randomized (controlled )?trial",
    r"statistically significant",
]

# C2: Contrarian / Observational signals
CONTRARIAN_SIGNALS: List[str] = [
    r"most people (think|believe|assume)",
    r"people (often )?(assume|think|believe)",
    r"the common (assumption|belief|wisdom)",
    r"conventional wisdom (says|suggests|holds)",
    r"nobody talks about",
    r"rarely (discussed|mentioned|acknowledged)",
    r"the real reason",
    r"the uncomfortable truth",
    r"the hidden (truth|reality|reason)",
    r"this is why",
    r"what actually (matters|works|happens)",
    r"the (real|actual|true) (problem|issue|reason)",
    r"contrary to (popular belief|what)",
    r"(but|yet) (here'?s|the) (thing|truth|reality)",
    r"what (most|many) (people|folks) (don'?t|miss|overlook)",
    r"the counterintuitive",
    r"paradoxically",
]

# C3: Meaning / Generalization signals
MEANING_SIGNALS: List[str] = [
    r"this (means|shows|demonstrates|proves|reveals) that",
    r"the (key )?(lesson|insight|takeaway|point) (is|here)",
    r"the (reason|explanation) (is|for this)",
    r"the (mistake|error|problem) (is|most people make)",
    r"what (this|we) (learn|discover|realize|understand)",
    r"what (works|matters|counts) (is|here)",
    r"this (explains?|illustrates?) (why|how)",
    r"the (pattern|principle|rule) (is|here)",
    r"in other words",
    r"put (simply|differently|another way)",
    r"the bottom line",
    r"ultimately",
    r"the implication (is|here)",
    r"the consequence (is|of this)",
    r"the (fundamental|core|essential) (truth|insight|lesson)",
]

# C4: Implicit insight markers (causal/reasoning language)
IMPLICIT_INSIGHT_MARKERS: List[str] = [
    r"because of this",
    r"as a result",
    r"therefore",
    r"consequently",
    r"this (leads?|led) to",
    r"the (effect|impact|result) (is|was)",
    r"which (means|explains|shows)",
    r"and (so|thus)",
    r"for this reason",
    r"that'?s (why|how|what)",
    r"hence",
    r"thus",
    r"accordingly",
]


# ============================================================================
# COMBINED PATTERN GROUPS
# ============================================================================

ALL_SIGNAL_PATTERNS: List[str] = (
    ACADEMIC_SIGNALS + CONTRARIAN_SIGNALS + MEANING_SIGNALS + IMPLICIT_INSIGHT_MARKERS
)

ALL_DROP_PATTERNS: List[str] = (
    META_STRUCTURAL_PATTERNS + INDEX_REFERENCE_PATTERNS + BIOGRAPHY_PATTERNS
)
