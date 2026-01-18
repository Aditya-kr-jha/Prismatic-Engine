"""
Stage 2.5 Prompt: Logic Skeleton for QUOTE.

Simplified skeleton for single-image quotes.
Defines the tension, resolution style, and screenshot quality.
"""

from langchain_core.prompts import ChatPromptTemplate

# ============================================================================
# SYSTEM PROMPT — Structural Architect
# ============================================================================

STAGE2_5_QUOTE_SYSTEM_PROMPT = """\
You are the structural architect of a high-performance Instagram content system. \
You design the LOGICAL SKELETON for Quotes before any text is written.

## YOUR TASK

Define the structural intent for this quote. Unlike carousels and reels, quotes are single units—\
but they still need architectural clarity.

## QUOTE ARCHITECTURE

A great quote has:
1. **A single, clear tension**: What dissonance does it create?
2. **A resolution style**: Does it resolve (statement) or leave open (implication)?
3. **Screenshot quality**: Why would someone screenshot this? (The "tattoo test")

## THE TATTOO TEST

Before outputting, verify:
> Would someone tattoo this if they were that kind of person?

If no → the quote lacks the required density and impact.\
"""

# ============================================================================
# HUMAN PROMPT — Skeleton Request
# ============================================================================

STAGE2_5_QUOTE_HUMAN_PROMPT = """\
Construct the skeleton for this QUOTE:

---
**Core Truth**: {core_truth}
**Pillar**: {required_pillar}

**Mode (from Stage 2)**: {opener_mode}
**Energy**: {opener_energy}

**Primary Emotion**: {primary_emotion}
**They share this because**: {share_trigger}
**They send it to**: {share_target}
---

Define the tension this quote creates, the resolution style, and why someone would screenshot it.\
"""

# ============================================================================
# COMBINED PROMPT TEMPLATE
# ============================================================================

STAGE2_5_QUOTE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", STAGE2_5_QUOTE_SYSTEM_PROMPT),
    ("human", STAGE2_5_QUOTE_HUMAN_PROMPT),
])
