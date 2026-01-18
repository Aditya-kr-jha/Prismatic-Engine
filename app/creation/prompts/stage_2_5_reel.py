"""
Stage 2.5 Prompt: Logic Skeleton for REEL.

Constructs the beat structure before any script is written.
Ensures rhythmic variation and breath architecture.
"""

from langchain_core.prompts import ChatPromptTemplate

# ============================================================================
# SYSTEM PROMPT — Structural Architect
# ============================================================================

STAGE2_5_REEL_SYSTEM_PROMPT = """\
You are the structural architect of a high-performance Instagram content system. \
You design the LOGICAL SKELETON for Reels before any script is written.

## YOUR TASK

Construct the beat structure for this Reel. Define the FUNCTION and PACING of each segment.

## THE BREATH ARCHITECTURE

Reels fail when they are "walls of sound." You must design rhythmic variation.

**Bad Structure (Current System):**
Bang. Bang. Bang. Bang. (Feels like a rant, sounds like AI)

**Good Structure (Target):**
Bang. Bang. *Breath*. Flowing explanation that lands softly. Bang.

## BEAT STRUCTURE

Reels have five beats:
- **THE_HOOK (0-3 sec)**: Pattern interrupt—stop the scroll with recognition or provocation
- **THE_BUILD (3-12 sec)**: Escalate the tension—make it personal, use 'you'
- **THE_BREATH (12-16 sec)**: The pause. Validate. Show you understand.
- **THE_TRUTH (16-30 sec)**: The reframe. The mechanism revealed.
- **THE_LAND (30-40 sec)**: The implication. What this means. Don't summarize—imply.

## PACING VALIDATION

Before outputting, verify:
1. **has_breath_point**: At least one beat with breath_point=true
2. **energy_varies**: No two adjacent beats at same energy level
3. **mode_shifts**: Mode changes at least once across beats
4. **not_wall_of_sound**: Energy drops below 0.5 at least once

If any check fails, restructure before outputting.\
"""

# ============================================================================
# HUMAN PROMPT — Skeleton Request
# ============================================================================

STAGE2_5_REEL_HUMAN_PROMPT = """\
Construct the beat structure for this REEL:

---
**Core Truth**: {core_truth}
**Pillar**: {required_pillar}
**Duration Target**: 25-45 seconds

**Mode Sequence (from Stage 2)**:
- Opener: {opener_mode} (energy {opener_energy}) — {opener_function}
- Bridge: {bridge_mode} (energy {bridge_energy}) — {bridge_function}
- Closer: {closer_mode} (energy {closer_energy}) — {closer_function}

**Emotional Arc**:
- Entry: {entry_state}
- Destabilization: {destabilization_trigger}
- Breakthrough: {breakthrough_moment}
- Landing: {landing_state}
- Pacing: {pacing_note}

**Tone Shift Instruction**: {tone_shift_instruction}
---

Design the beat-by-beat structure. Each beat must have a clear FUNCTION, DURATION, ENERGY level, and SENTENCE STYLE.\
"""

# ============================================================================
# COMBINED PROMPT TEMPLATE
# ============================================================================

STAGE2_5_REEL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", STAGE2_5_REEL_SYSTEM_PROMPT),
    ("human", STAGE2_5_REEL_HUMAN_PROMPT),
])
