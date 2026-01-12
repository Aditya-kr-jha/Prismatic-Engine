"""
Pydantic v2 Schemas for Phase 5 Creation.

These schemas define the HARD CONTRACT between the LLM and the system.
- Stage 1: Extract psychological cores from content briefs
- Stage 2: Resolve mode and set emotional targets
"""

from typing import Any, Dict, List, Literal, Optional, Union, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# STAGE 1: EXTRACT & ANALYZE
# ============================================================================


class EmotionalCore(BaseModel):
    """
    Emotional analysis of content material.

    Emotions must be VISCERAL (vindication, shame, relief, recognition,
    superiority, fear, desire) — not cognitive (understanding, learning).
    """

    primary_emotion: str = Field(
        ...,
        description="Primary visceral emotion triggered (e.g., vindication, shame, relief)",
    )
    secondary_emotion: str = Field(
        ...,
        description="Secondary emotion triggered",
    )
    why_someone_shares_this: str = Field(
        ...,
        description="One sentence explaining shareability motivation",
    )


class Stage1Analysis(BaseModel):
    """
    Stage 1 LLM output: Core analysis of content brief.

    This is passed to `with_structured_output()` for deterministic parsing.
    """

    core_truth: str = Field(
        ...,
        description="The irreducible insight in one sentence. Speakable in one breath.",
    )
    brief_quality_score: int = Field(
        ...,
        ge=1,
        le=10,
        description="Quality score 1-10. Most briefs score 5-7. A 7 is average.",
    )
    brief_quality_issues: List[str] = Field(
        default_factory=list,
        description="List of quality issues found in the brief",
    )
    requires_heavy_reframe: bool = Field(
        ...,
        description="True if brief is academic, verbose, or explanation-heavy",
    )
    suggested_reframe: Optional[str] = Field(
        default=None,
        description="Better angle if reframe needed. Null if not needed.",
    )
    emotional_core: EmotionalCore = Field(
        ...,
        description="Emotional analysis of the material",
    )
    strongest_hook_in_material: str = Field(
        ...,
        description="The best hook element found or invented",
    )
    instagram_readiness: Literal["READY", "NEEDS_WORK", "UNSUITABLE"] = Field(
        ...,
        description="Instagram readiness assessment",
    )
    unsuitable_reason: Optional[str] = Field(
        default=None,
        description="Only if UNSUITABLE. Why this can't work on Instagram.",
    )


# ============================================================================
# STAGE 1: BATCH RESULT
# ============================================================================


class Stage1Result(BaseModel):
    """Result from analyzing a single ContentSchedule row."""

    schedule_id: str = Field(..., description="UUID of the ContentSchedule row")
    trace_id: str = Field(..., description="Trace ID for lineage")
    analysis: Optional[Stage1Analysis] = Field(
        default=None,
        description="Stage 1 analysis result (None if error)",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if analysis failed",
    )
    skipped: bool = Field(
        default=False,
        description="True if marked UNSUITABLE and skipped",
    )


class Stage1BatchResult(BaseModel):
    """Result from a Stage 1 batch operation."""

    week_year: int
    week_number: int
    total_processed: int = 0
    successful: int = 0
    unsuitable: int = 0
    errors: int = 0
    results: List[Stage1Result] = Field(default_factory=list)
    duration_seconds: float = 0.0


# ============================================================================
# STAGE 2: RESOLVE MODE & SET EMOTIONAL TARGET
# ============================================================================


class EmotionalJourney(BaseModel):
    """
    Three-state emotional journey the content must create.

    Shows MOVEMENT through emotional states, not static feelings.
    """

    state_1: str = Field(
        ...,
        description="Starting emotional state (what they feel before)",
    )
    state_2: str = Field(
        ...,
        description="Middle state (the shift)",
    )
    state_3: str = Field(
        ...,
        description="End state (what they feel after)",
    )


class Stage2Targeting(BaseModel):
    """
    Stage 2 LLM output: Emotional targeting architecture.

    Defines the precise emotional journey the content must create.
    Instagram rewards emotional response, not information.
    """

    emotional_journey: EmotionalJourney = Field(
        ...,
        description="Three-state emotional journey",
    )
    physical_response_goal: str = Field(
        ...,
        description="Somatic response (sharp exhale, screenshot impulse, etc.)",
    )
    share_trigger: str = Field(
        ...,
        description="The specific reason they send this to someone",
    )
    share_target: str = Field(
        ...,
        description="Who they send it to (specific, not 'friends')",
    )
    comment_trigger: str = Field(
        ...,
        description="What would make someone comment",
    )
    save_trigger: str = Field(
        ...,
        description="Why they'd save this",
    )
    mode_energy_note: str = Field(
        ...,
        description="How this mode should feel for THIS specific piece",
    )


# ============================================================================
# STAGE 2: GENERATION CONTEXT (OUTPUT)
# ============================================================================


class GenerationContext(BaseModel):
    """
    Complete context for Stage 3 generation.

    Compiled from ContentSchedule, Stage 1, and Stage 2 outputs.
    This is the single input object for content generation.
    """

    # From ContentSchedule
    schedule_id: str = Field(..., description="UUID of the ContentSchedule row")
    trace_id: str = Field(..., description="Trace ID for lineage")
    required_format: str = Field(..., description="REEL, CAROUSEL, or QUOTE")
    required_pillar: str = Field(..., description="Content pillar")
    brief: Dict[str, Any] = Field(default_factory=dict, description="Original brief")

    # From Stage 1
    core_truth: str = Field(..., description="The irreducible insight")
    requires_heavy_reframe: bool = Field(default=False)
    suggested_reframe: Optional[str] = Field(default=None)
    strongest_hook: str = Field(..., description="Best hook element")
    primary_emotion: str = Field(..., description="Primary visceral emotion")
    secondary_emotion: str = Field(..., description="Secondary emotion")

    # From Stage 2 / Matrix
    resolved_mode: str = Field(..., description="Mode from Format × Pillar matrix")
    structural_note: str = Field(..., description="Structural guidance for the mode")
    emotional_journey: EmotionalJourney = Field(
        ...,
        description="Three-state emotional journey",
    )
    physical_response_goal: str = Field(...)
    share_trigger: str = Field(...)
    share_target: str = Field(...)
    mode_energy_note: str = Field(...)

    # Rewrite context (populated on Stage 4 retry)
    rewrite_focus: Optional[str] = Field(
        default=None,
        description="Single most important thing to fix on rewrite",
    )
    specific_failures: List["CritiqueFailure"] = Field(
        default_factory=list,
        description="Specific failures from Stage 4 critique",
    )
    ai_voice_violations: List[str] = Field(
        default_factory=list,
        description="AI voice violations detected in previous attempt",
    )
    attempt_number: int = Field(
        default=1,
        description="Current generation attempt (1, 2, or 3)",
    )


# ============================================================================
# STAGE 2: BATCH RESULT
# ============================================================================


class Stage2Result(BaseModel):
    """Result from targeting a single ContentSchedule row."""

    schedule_id: str = Field(..., description="UUID of the ContentSchedule row")
    trace_id: str = Field(..., description="Trace ID for lineage")
    context: Optional[GenerationContext] = Field(
        default=None,
        description="Generation context for Stage 3 (None if error)",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if targeting failed",
    )


# ============================================================================
# STAGE 3: GENERATE CONTENT - REEL
# ============================================================================


class ReelNotes(BaseModel):
    """Internal notes for Reel generation quality tracking."""

    mode_used: str = Field(..., description="Mode used for this reel")
    emotional_journey_achieved: str = Field(
        ...,
        description="The emotional journey achieved (e.g., 'frustration → recognition → vindication')",
    )
    why_this_works: str = Field(
        ...,
        description="One sentence on why this will perform",
    )


class ReelContent(BaseModel):
    """Stage 3 output for REEL format."""

    hook_line: str = Field(
        ...,
        description="First line. Must stop scroll in under 2 seconds.",
    )
    body: List[str] = Field(
        ...,
        description="Body lines of the script",
    )
    punch_line: str = Field(
        ...,
        description="Final line. The one they screenshot or share.",
    )
    screenshot_line: str = Field(
        ...,
        description="The single most shareable line",
    )
    estimated_duration_seconds: int = Field(
        ...,
        ge=15,
        le=60,
        description="Estimated duration when spoken (15-60 seconds)",
    )
    text_overlay_suggestion: Optional[str] = Field(
        default=None,
        description="Key phrase for on-screen text",
    )
    internal_notes: ReelNotes = Field(..., description="Generation metadata")


# ============================================================================
# STAGE 3: GENERATE CONTENT - CAROUSEL
# ============================================================================


class CarouselSlide(BaseModel):
    """Single slide in a carousel."""

    slide_number: int = Field(..., ge=1, description="Slide position (1-indexed)")
    headline: str = Field(..., description="Main text (large)")
    body: Optional[str] = Field(
        default=None,
        description="Supporting text (smaller). Can be null.",
    )
    design_note: Optional[str] = Field(
        default=None,
        description="Optional design guidance",
    )


class CarouselNotes(BaseModel):
    """Internal notes for Carousel generation quality tracking."""

    mode_used: str = Field(..., description="Primary mode used")
    mode_transitions: Optional[List[str]] = Field(
        default=None,
        description="Mode transitions per slide if hybrid (e.g., ['ROAST slide 1', 'SURGEON slides 2-7'])",
    )
    emotional_journey_achieved: str = Field(
        ...,
        description="The emotional journey achieved",
    )
    why_this_works: str = Field(
        ...,
        description="One sentence on why this will perform",
    )


class CarouselContent(BaseModel):
    """Stage 3 output for CAROUSEL format."""

    slides: List[CarouselSlide] = Field(
        ...,
        min_length=6,
        max_length=10,
        description="6-10 slides (8 is optimal)",
    )
    cover_slide_text: str = Field(
        ...,
        description="Text that appears on cover in grid view",
    )
    screenshot_slide: int = Field(
        ...,
        description="Which slide number is most screenshottable",
    )
    internal_notes: CarouselNotes = Field(..., description="Generation metadata")


# ============================================================================
# STAGE 3: GENERATE CONTENT - QUOTE
# ============================================================================


class QuoteNotes(BaseModel):
    """Internal notes for Quote generation quality tracking."""

    mode_used: str = Field(..., description="Mode used for this quote")
    primary_emotion_targeted: str = Field(
        ...,
        description="Primary emotion targeted",
    )
    why_this_works: str = Field(
        ...,
        description="One sentence on why this will perform",
    )
    tattoo_test_pass: bool = Field(
        ...,
        description="Would someone tattoo this? True/False",
    )


class QuoteContent(BaseModel):
    """Stage 3 output for QUOTE format."""

    quote_text: str = Field(
        ...,
        description="The quote. 1-3 sentences maximum.",
    )
    quote_text_alt: str = Field(
        ...,
        description="Alternative version with different framing",
    )
    caption: Optional[str] = Field(
        default=None,
        description="Optional Instagram caption (2-3 sentences max)",
    )
    internal_notes: QuoteNotes = Field(..., description="Generation metadata")


# ============================================================================
# STAGE 3: UNIFIED RESULT
# ============================================================================


class Stage3Result(BaseModel):
    """Result from generating content for a single ContentSchedule row."""

    schedule_id: str = Field(..., description="UUID of the ContentSchedule row")
    trace_id: str = Field(..., description="Trace ID for lineage")
    format_type: str = Field(..., description="REEL, CAROUSEL, or QUOTE")

    # Only one of these will be populated based on format_type
    reel_content: Optional[ReelContent] = Field(default=None)
    carousel_content: Optional[CarouselContent] = Field(default=None)
    quote_content: Optional[QuoteContent] = Field(default=None)

    error: Optional[str] = Field(default=None, description="Error if generation failed")


# ============================================================================
# STAGE 4: SELF-CRITIQUE
# ============================================================================


class CritiqueScores(BaseModel):
    """Scores from Stage 4 critique evaluation (1-10 scale)."""

    scroll_stop_power: int = Field(
        ...,
        ge=1,
        le=10,
        description="Does the opening create immediate tension, recognition, or intrigue?",
    )
    ai_voice_risk: int = Field(
        ...,
        ge=1,
        le=10,
        description="Does this sound AI-generated? Higher = more human.",
    )
    share_impulse: int = Field(
        ...,
        ge=1,
        le=10,
        description="Would someone send this to a specific person?",
    )
    emotional_precision: int = Field(
        ...,
        ge=1,
        le=10,
        description="Does this hit the target emotional journey?",
    )
    mode_fidelity: int = Field(
        ...,
        ge=1,
        le=10,
        description="Does the content stay in the assigned mode?",
    )
    format_execution: int = Field(
        ...,
        ge=1,
        le=10,
        description="Does the content work for its specific format?",
    )


class CritiqueFailure(BaseModel):
    """Details of a specific criterion failure."""

    criterion: str = Field(..., description="Which criterion failed")
    issue: str = Field(..., description="Specific problem identified")
    fix: str = Field(..., description="Specific fix recommendation")


class CritiqueResult(BaseModel):
    """
    Stage 4 LLM output: Self-critique evaluation.

    This is passed to `with_structured_output()` for deterministic parsing.
    """

    scores: CritiqueScores = Field(..., description="Scores for all 6 criteria")
    lowest_score_criterion: str = Field(..., description="Which criterion scored lowest")
    overall_pass: bool = Field(
        ...,
        description="True if all scores >= 6 and ai_voice_risk >= 7",
    )
    specific_failures: List[CritiqueFailure] = Field(
        default_factory=list,
        description="Details on each failing criterion",
    )
    ai_voice_violations: List[str] = Field(
        default_factory=list,
        description="Specific AI voice phrases or structures found",
    )
    rewrite_required: bool = Field(
        ...,
        description="True if content needs rewriting",
    )
    rewrite_focus: Optional[str] = Field(
        default=None,
        description="If rewrite required, the single most important thing to fix",
    )


class Stage4Result(BaseModel):
    """Result from Stage 4 critique loop."""

    schedule_id: str = Field(..., description="UUID of the ContentSchedule row")
    trace_id: str = Field(..., description="Trace ID for lineage")
    final_content: Optional[
        Union["ReelContent", "CarouselContent", "QuoteContent"]
    ] = Field(default=None, description="Final content after critique loop")
    final_critique: Optional[CritiqueResult] = Field(
        default=None,
        description="Final critique result",
    )
    attempts_used: int = Field(default=1, description="Number of attempts used (1-3)")
    passed: bool = Field(default=False, description="True if content passed critique")
    flagged_for_review: bool = Field(
        default=False,
        description="True if max attempts reached and still failing",
    )
    error: Optional[str] = Field(default=None, description="Error if critique failed")


# ============================================================================
# STAGE 5: HARD FILTERS & STORAGE
# ============================================================================


class HardFilterResult(BaseModel):
    """Result from Stage 5 automated hard filter checks."""

    passed: bool = Field(..., description="True if all filters passed")
    failures: List[str] = Field(
        default_factory=list,
        description="List of filter failure codes/messages",
    )


class Stage5Result(BaseModel):
    """Result from Stage 5 hard filters and storage."""

    schedule_id: str = Field(..., description="UUID of the ContentSchedule row")
    trace_id: str = Field(..., description="Trace ID for lineage")
    filter_result: HardFilterResult = Field(
        ...,
        description="Hard filter check results",
    )
    stored: bool = Field(default=False, description="True if content was stored")
    generated_content_id: Optional[str] = Field(
        default=None,
        description="UUID of the GeneratedContent row if stored",
    )
    final_status: str = Field(
        default="UNKNOWN",
        description="Final status: CONTENT_READY or NEEDS_REVIEW",
    )
    error: Optional[str] = Field(default=None, description="Error if storage failed")

