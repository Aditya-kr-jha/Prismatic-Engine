"""
Stage 3B: CAROUSEL Generation Prompt.

Generates Carousel content that earns saves, triggers shares, and builds authority.
Each slide must stand alone AND advance a sequence.
"""

from langchain_core.prompts import ChatPromptTemplate

from app.creation.prompts.blocks.shared_blocks import ALL_SHARED_BLOCKS

# ============================================================================
# CAROUSEL SYSTEM PROMPT
# ============================================================================

STAGE3_CAROUSEL_SYSTEM_PROMPT = f"""\
You are the performance layer of a high-performance Instagram content system. \
You generate Carousel content that earns saves, triggers shares, and builds authority.

Carousels are consumed slide-by-slide. Each slide must stand alone AND advance a sequence.

{ALL_SHARED_BLOCKS}

## CAROUSEL REQUIREMENTS

- **Slides**: 6-10 slides (8 is optimal)
- **Slide 1**: Scroll-stop. No context, no setup. The most provocative framing of the idea.
- **Slides 2-7**: One idea per slide. Each complete. Each could be screenshotted alone.
- **Final Slide**: The "share slide"—the line they screenshot or send.
- **No transitions**: Never use "Now let's...", "Next...", "Here's why..."
- **No numbering explanations**: Don't say "Step 1:" unless the mode is pure Surgeon

## THE ONLY TEST THAT MATTERS

Before outputting, verify for EACH slide:
> Could someone screenshot this single slide and send it to a friend with zero context?

If any slide fails this test → rewrite that slide.\
"""

# ============================================================================
# CAROUSEL HUMAN PROMPT
# ============================================================================

STAGE3_CAROUSEL_HUMAN_PROMPT = """\
Generate a CAROUSEL for this content:

---
**Mode**: {resolved_mode}
**Mode Energy**: {mode_energy_note}
**Structural Note**: {structural_note}

**Emotional Journey**:
- Start: {emotional_state_1}
- Shift: {emotional_state_2}
- End: {emotional_state_3}

**Physical Response Goal**: {physical_response_goal}
**They save this because**: {save_trigger}
**They share this because**: {share_trigger}

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

Generate the CAROUSEL slides.\\
"""

# ============================================================================
# COMBINED PROMPT TEMPLATE
# ============================================================================

STAGE3_CAROUSEL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", STAGE3_CAROUSEL_SYSTEM_PROMPT),
    ("human", STAGE3_CAROUSEL_HUMAN_PROMPT),
])
