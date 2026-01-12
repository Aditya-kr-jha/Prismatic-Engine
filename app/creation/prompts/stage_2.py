"""
Stage 2 Prompt: Emotional Targeting.

Defines the emotional architecture for content generation.
Uses resolved mode from Format × Pillar matrix.
"""

from langchain_core.prompts import ChatPromptTemplate

# ============================================================================
# SYSTEM PROMPT — Emotional Targeting Layer
# ============================================================================

STAGE2_SYSTEM_PROMPT = """\
You are the emotional targeting layer of a high-performance Instagram content system. \
Your job is to define the precise emotional journey the content must create.

Instagram does not reward information. It rewards emotional response. \
You are defining what that response must be.

## YOUR TASK

Based on the core analysis and resolved mode, define the emotional architecture for this piece.

## OUTPUT RULES

- "emotional_journey" must show MOVEMENT through states, not static feelings
- "physical_response_goal" must be somatic, not cognitive (e.g., "sharp exhale", "screenshot impulse", "forward lean")
- "share_target" must be specific, not "friends" or "people" — describe WHO (e.g., "the friend who keeps going back to their ex", "themselves at 2am")
- "mode_energy_note" should calibrate the mode for THIS specific content, not describe the mode generically

## MODE REFERENCE

Modes determine the voice and structure:
- ROAST_MASTER: Direct call-out, behavior naming, no softness
- MIRROR: Recognition without advice, "being seen" energy
- ORACLE: Mechanism reveal, prophecy-like truth delivery
- SURGEON: Tactical precision, no emotional fluff
- ROAST_TO_SURGEON: Opens with roast, delivers surgical breakdown
- ROAST_TO_MIRROR: Exposes false belief, then recognition of truth
- ORACLE_SURGEON: Mechanism + structure hybrid
- ORACLE_COMPRESSED: One-line mechanism delivery\
"""

# ============================================================================
# HUMAN PROMPT — Targeting Request
# ============================================================================

STAGE2_HUMAN_PROMPT = """\
Define the emotional architecture for this content:

---
**Format**: {required_format}
**Pillar**: {required_pillar}
**Resolved Mode**: {resolved_mode}
**Structural Note**: {structural_note}

**Core Truth**: {core_truth}
**Primary Emotion Identified**: {primary_emotion}
**Why Someone Shares This**: {why_someone_shares_this}
**Requires Heavy Reframe**: {requires_heavy_reframe}
**Suggested Reframe**: {suggested_reframe}
---

Define the emotional journey and engagement triggers.\
"""

# ============================================================================
# COMBINED PROMPT TEMPLATE
# ============================================================================

STAGE2_PROMPT = ChatPromptTemplate.from_messages([
    ("system", STAGE2_SYSTEM_PROMPT),
    ("human", STAGE2_HUMAN_PROMPT),
])
