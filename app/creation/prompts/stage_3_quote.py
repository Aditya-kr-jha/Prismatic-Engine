"""
Stage 3C: QUOTE Generation Prompt.

Generates single-image Quotes that stop scrolls, earn saves, and get shared in DMs.
Quotes succeed on immediate recognition. No setup. No context. Just truth that lands.
"""

from langchain_core.prompts import ChatPromptTemplate

from app.creation.prompts.blocks.shared_blocks import ALL_SHARED_BLOCKS

# ============================================================================
# QUOTE SYSTEM PROMPT
# ============================================================================

STAGE3_QUOTE_SYSTEM_PROMPT = f"""\
You are the performance layer of a high-performance Instagram content system. \
You generate single-image Quotes that stop scrolls, earn saves, and get shared in DMs.

Quotes succeed on immediate recognition. No setup. No context. Just truth that lands.

{ALL_SHARED_BLOCKS}

## QUOTE REQUIREMENTS

- **Length**: 1-3 sentences maximum. Ideally 1.
- **No setup**: The quote IS the setup and the punch
- **Zero context needed**: Must work for someone who's never seen your content
- **Physical response**: Must trigger a sharp exhale, a screenshot, or a "send to" impulse
- **Tattoo test**: Write the line someone would tattoo if they were that kind of person

## THE ONLY TEST THAT MATTERS

Before outputting, verify:
> If this quote appeared on a plain background with no username, would someone still screenshot it?

If no → rewrite. The quote must carry its own weight.\
"""

# ============================================================================
# QUOTE HUMAN PROMPT
# ============================================================================

STAGE3_QUOTE_HUMAN_PROMPT = """\
Generate a QUOTE for this content:

---
**Primary Mode**: {resolved_mode}
**Tone Shift**: {tone_shift_instruction}

**Mode Sequence (Manson Protocol)**:
- **Opener** ({opener_mode}, energy {opener_energy}): {opener_function}
- **Bridge** ({bridge_mode}, energy {bridge_energy}): {bridge_function}
- **Closer** ({closer_mode}, energy {closer_energy}): {closer_function}

**Emotional Arc**:
- Entry: {entry_state}
- Destabilization: {destabilization_trigger}
- Breakthrough: {breakthrough_moment}
- Landing: {landing_state}
- Pacing: {pacing_note}

**The Journey (A → B)**:
- **Counter-Truth (State A)**: {counter_truth}
- **Core Truth (State B)**: {core_truth}
- **Contrast**: {contrast_pair}

**Physical Response Goal**: {physical_response_goal}
**They share this because**: {share_trigger}
**They send it to**: {share_target}

**Strongest Hook**: {strongest_hook}
**Primary Emotion**: {primary_emotion}
**Pillar**: {required_pillar}

{reframe_note}

---

## QUOTE SKELETON (FROM STAGE 2.5)

Follow this structural plan for the quote architecture.

```json
{skeleton_json}
```

---

**Full Brief**:
```json
{brief}
```
---

{rewrite_context}

Generate the QUOTE following the skeleton structure.\\
"""

# ============================================================================
# COMBINED PROMPT TEMPLATE
# ============================================================================

STAGE3_QUOTE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", STAGE3_QUOTE_SYSTEM_PROMPT),
    ("human", STAGE3_QUOTE_HUMAN_PROMPT),
])
