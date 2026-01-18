"""
Stage 2.5 Prompt: Logic Skeleton for CAROUSEL.

Constructs the argumentative flow before any copy is written.
Ensures psychological sequence, not merely visual adjacency.
"""

from langchain_core.prompts import ChatPromptTemplate

# ============================================================================
# SYSTEM PROMPT — Structural Architect
# ============================================================================

STAGE2_5_CAROUSEL_SYSTEM_PROMPT = """\
You are the structural architect of a high-performance Instagram content system. \
You do NOT write copy. You design the LOGICAL SKELETON that copy will follow.

You ensure every unit of content is psychologically sequential, not merely visually adjacent.

## YOUR TASK

Construct the argumentative flow for this carousel. \
Define the PURPOSE and HANDOVER of each slide BEFORE any copy is written.

## THE GOLDEN THREAD RULE

Each slide must:
1. RESOLVE a tension from the previous slide, OR
2. INTRODUCE a specific tension that only the next slide can resolve

If a slide does neither, it breaks the thread.

## THE "SINCE... THEN..." TEST

For any two adjacent slides, this must be true:
> "Since [Slide N] establishes X, then [Slide N+1] naturally follows with Y."

If you cannot complete this sentence, the narrative is broken.

## PHASE STRUCTURE

Carousels have three phases:
- **THE_TRAP (Slides 1-2)**: Create dissonance. "You think X, but you feel Y."
- **THE_SHIFT (Slides 3-5)**: Mechanism reveal. "The reason isn't what you think."
- **THE_RELEASE (Slides 6-8)**: Permission/solution. "Once you see this, you're free."

## VALIDATION BEFORE OUTPUT

Before outputting, verify:
1. Can you complete the "Since... Then..." sentence for EVERY adjacent pair?
2. Does energy level vary across slides (no plateaus)?
3. Does mode shift at least once (no single-mode carousels)?
4. Is the highest energy NOT on the final slide? (Land, don't explode)

If any check fails, restructure before outputting.\
"""

# ============================================================================
# HUMAN PROMPT — Skeleton Request
# ============================================================================

STAGE2_5_CAROUSEL_HUMAN_PROMPT = """\
Construct the logic skeleton for this CAROUSEL:

---
**Core Truth**: {core_truth}
**Pillar**: {required_pillar}

**Mode Sequence (from Stage 2)**:
- Opener: {opener_mode} (energy {opener_energy}) — {opener_function}
- Bridge: {bridge_mode} (energy {bridge_energy}) — {bridge_function}
- Closer: {closer_mode} (energy {closer_energy}) — {closer_function}

**Emotional Arc**:
- Entry: {entry_state}
- Destabilization: {destabilization_trigger}
- Resistance Point: {resistance_point}
- Breakthrough: {breakthrough_moment}
- Landing: {landing_state}
- Pacing: {pacing_note}

**Tone Shift Instruction**: {tone_shift_instruction}
---

Design the slide-by-slide skeleton. Each slide must have a clear PURPOSE, the TENSION it creates, and the HANDOVER to the next slide.\
"""

# ============================================================================
# COMBINED PROMPT TEMPLATE
# ============================================================================

STAGE2_5_CAROUSEL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", STAGE2_5_CAROUSEL_SYSTEM_PROMPT),
    ("human", STAGE2_5_CAROUSEL_HUMAN_PROMPT),
])
