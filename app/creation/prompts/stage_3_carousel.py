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

Before outputting, verify the SEQUENCE:

1. **The "Since... Then..." Test**: For every adjacent pair of slides, complete:
   > "Since Slide N establishes X, then Slide N+1 naturally follows with Y."
   If you cannot complete this sentence → the thread is broken → rewrite.

2. **The Screenshot Test** (FINAL SLIDE ONLY):
   > Could someone screenshot the final slide and share it with zero context?
   The final slide is the "share slide" — it must work alone. All other slides earn it.

3. **The Thread Test**: If Slide 4 were removed, would Slides 3 and 5 still make sense together?
   If yes → Slide 4 is not doing its job → rewrite Slide 4.\
"""

# ============================================================================
# CAROUSEL HUMAN PROMPT
# ============================================================================

STAGE3_CAROUSEL_HUMAN_PROMPT = """\
Generate a CAROUSEL for this content:

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
- Resistance Point: {resistance_point}
- Breakthrough: {breakthrough_moment}
- Landing: {landing_state}
- Pacing: {pacing_note}

**The Journey (A → B)**:
- **Counter-Truth (State A)**: {counter_truth}
- **Core Truth (State B)**: {core_truth}
- **Contrast**: {contrast_pair}

**Physical Response Goal**: {physical_response_goal}
**They save this because**: {save_trigger}
**They share this because**: {share_trigger}

**Strongest Hook**: {strongest_hook}
**Primary Emotion**: {primary_emotion}
**Pillar**: {required_pillar}

{reframe_note}

---

## LOGIC SKELETON (FROM STAGE 2.5)

This skeleton defines the EXACT structure. You MUST:

1. **Match Purpose**: Each slide's headline must accomplish its `purpose` field.
2. **Honor Mode**: Each slide must use the voice of its specified `mode`.
3. **Resolve Prior Tension**: Slides 2+ must open by addressing the `resolves_tension` from the previous slide.
4. **Create Forward Tension**: Each slide must end with the reader NEEDING what comes next (`creates_tension`).
5. **Vary Energy**: If the skeleton says slide 3 is 0.5 energy, it should feel calmer than slide 2 at 0.8.
6. **Deliver Handover**: Each slide must leave the reader with the `handover_to_next` state.

For EACH slide, before writing, ask:
- Does this accomplish [purpose]?
- Does this feel like [mode]?
- Does this resolve [resolves_tension]?
- Does this create [creates_tension]?
- Does the energy level match?

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

Generate the CAROUSEL slides following the skeleton structure.\\
"""

# ============================================================================
# COMBINED PROMPT TEMPLATE
# ============================================================================

STAGE3_CAROUSEL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", STAGE3_CAROUSEL_SYSTEM_PROMPT),
    ("human", STAGE3_CAROUSEL_HUMAN_PROMPT),
])
