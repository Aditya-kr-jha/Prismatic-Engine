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

Generate the QUOTE.\\
"""

# ============================================================================
# COMBINED PROMPT TEMPLATE
# ============================================================================

STAGE3_QUOTE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", STAGE3_QUOTE_SYSTEM_PROMPT),
    ("human", STAGE3_QUOTE_HUMAN_PROMPT),
])
