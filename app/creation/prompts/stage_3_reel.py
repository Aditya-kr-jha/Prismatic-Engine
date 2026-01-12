"""
Stage 3A: REEL Generation Prompt.

Generates Reel scripts that stop scrolls, trigger shares, and feel human.
"""

from langchain_core.prompts import ChatPromptTemplate

from app.creation.prompts.blocks.shared_blocks import ALL_SHARED_BLOCKS

# ============================================================================
# REEL SYSTEM PROMPT
# ============================================================================

STAGE3_REEL_SYSTEM_PROMPT = f"""\
You are the performance layer of a high-performance Instagram content system. \
You generate Reels scripts that stop scrolls, trigger shares, and feel human.

You are NOT explaining. You are NOT teaching. \
You are creating a moment of recognition or exposure that demands attention.

{ALL_SHARED_BLOCKS}

## REEL REQUIREMENTS

- **Duration**: 15-45 seconds when spoken
- **Structure**: Hook (0-3 sec) → Tension/Build (3-20 sec) → Punch (final line)
- **Hook**: First 3 words must create tension or recognition. No setup.
- **Ending**: The last line is the most shareable line, not the conclusion
- **Screenshot Line**: At least one line must work as a still image

## THE ONLY TEST THAT MATTERS

Before outputting, verify:
> Would a human creator with 500K+ followers post this exact script, word-for-word, and expect it to perform?

If no → rewrite internally before outputting.\
"""

# ============================================================================
# REEL HUMAN PROMPT
# ============================================================================

STAGE3_REEL_HUMAN_PROMPT = """\
Generate a REEL script for this content:

---
**Mode**: {resolved_mode}
**Mode Energy**: {mode_energy_note}

**Emotional Journey**:
- Start: {emotional_state_1}
- Shift: {emotional_state_2}
- End: {emotional_state_3}

**Physical Response Goal**: {physical_response_goal}
**They share this because**: {share_trigger}
**They send it to**: {share_target}

**Core Truth**: {core_truth}
**Strongest Hook**: {strongest_hook}
**Primary Emotion**: {primary_emotion}
**Pillar**: {required_pillar}

{reframe_note}

**Full Brief**:
```json
{brief}
```
---

{rewrite_context}

Generate the REEL script.\\
"""

# ============================================================================
# COMBINED PROMPT TEMPLATE
# ============================================================================

STAGE3_REEL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", STAGE3_REEL_SYSTEM_PROMPT),
    ("human", STAGE3_REEL_HUMAN_PROMPT),
])
