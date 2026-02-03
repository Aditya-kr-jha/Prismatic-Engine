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
        description="The irreducible insight in one sentence. THE DESTINATION.",
    )
    counter_truth: str = Field(
        ...,
        description="The lie, delusion, or anxiety the audience currently holds. THE STARTING POINT.",
    )
    contrast_pair: str = Field(
        ...,
        description="The A→B journey: 'FROM [counter_truth] TO [core_truth]'",
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

    # Generalization Layer (for Broadcast Voice)
    universal_pattern: str = Field(
        ...,
        description="The observable human pattern this reveals (not individual-specific)",
    )
    population_anchor: str = Field(
        ...,
        description="Who else experiences this? Multiple archetypes, not one.",
    )
    mechanism_name: str = Field(
        ...,
        description="A shareable name for this pattern (e.g., 'the silent scorekeeper', 'the validation audit')",
    )

    # Platform-Native Extraction (CRITICAL FOR RETENTION)
    hook_ammunition: List[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="3 specific, visceral opening lines that create immediate recognition. NOT concepts—specific behaviors, moments, or physical sensations.",
    )
    hyper_specific_moment: str = Field(
        ...,
        description="One extremely specific behavior that signals the larger pattern. Should trigger 'how do they know I do this' response.",
    )
    screenshot_candidates: List[str] = Field(
        ...,
        min_length=2,
        max_length=3,
        description="2-3 standalone lines (max 15 words each) that work without context and trigger 'I need to send this to someone' response.",
    )
    accusation_angle: str = Field(
        ...,
        description="The uncomfortable truth framed as 'what you're actually doing'. Behavior exposure, not diagnosis.",
    )
    share_trigger_person: str = Field(
        ...,
        description="The SPECIFIC person type they'll send this to. Not 'friends'—the exact archetype.",
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

    DEPRECATED: Use EmotionalArc instead for new implementations.
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


# ============================================================================
# STAGE 2: MODE SEQUENCE (MANSON PROTOCOL)
# ============================================================================


class ModeStep(BaseModel):
    """
    Single step in the mode sequence.

    Each step defines a mode, its function at that point, and energy level.
    """

    mode: str = Field(
        ...,
        description="Mode name: ROAST_MASTER, MIRROR, ORACLE, SURGEON, etc.",
    )
    function: str = Field(
        ...,
        description="What this mode achieves at this point in the sequence",
    )
    energy: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Energy level 0.0 (calm/clinical) to 1.0 (sharp/intense)",
    )


class ModeSequence(BaseModel):
    """
    The three-part mode journey (Manson Protocol).

    Trust requires CONTRAST: Mean then kind. Confusing then clear.
    A 60-second Roast is verbal abuse. A 10-slide Oracle is a lecture.
    """

    opener: ModeStep = Field(
        ...,
        description="The Callout - create dissonance, wake them up",
    )
    bridge: ModeStep = Field(
        ...,
        description="The Validation - soften, show you understand the pain",
    )
    closer: ModeStep = Field(
        ...,
        description="The Truth - reveal the mechanism, give them the truth",
    )


class EmotionalArc(BaseModel):
    """
    Continuous emotional arc with pacing notes.

    Replaces discrete EmotionalJourney. Shows a continuous arc with
    destabilization, resistance, and earned breakthrough.
    """

    entry_state: str = Field(
        ...,
        description="Where they are before (usually unconscious avoidance)",
    )
    destabilization_trigger: str = Field(
        ...,
        description="The specific moment of recognition - they see themselves",
    )
    resistance_point: str = Field(
        ...,
        description="Where they want to dismiss this - MUST be addressed",
    )
    breakthrough_moment: str = Field(
        ...,
        description="The reframe they can't unsee - must feel EARNED by resistance",
    )
    landing_state: str = Field(
        ...,
        description="Implication, not resolution. What now? Leave something open.",
    )
    pacing_note: str = Field(
        ...,
        description="Timing guidance (e.g., 'Breakthrough must feel EARNED. Don't rush past resistance.')",
    )


class Stage2Targeting(BaseModel):
    """
    Stage 2 LLM output: Emotional targeting architecture.

    Defines the mode sequence (Manson Protocol) and continuous emotional arc.
    Instagram rewards emotional response, not information.
    """

    # New: Mode Sequence (Manson Protocol)
    mode_sequence: ModeSequence = Field(
        ...,
        description="Three-part mode journey: opener → bridge → closer",
    )

    # New: Continuous Emotional Arc
    emotional_arc: EmotionalArc = Field(
        ...,
        description="5-stage continuous emotional arc with pacing",
    )

    # Engagement triggers
    physical_response_goal: str = Field(
        ...,
        description="Somatic response (sharp exhale at opener, screenshot impulse at closer, etc.)",
    )
    share_trigger: str = Field(
        ...,
        description="The specific reason they send this to someone",
    )
    share_target: str = Field(
        ...,
        description="Who they send it to (specific person type, not 'friends')",
    )
    comment_trigger: str = Field(
        ...,
        description="What would make someone comment",
    )
    save_trigger: str = Field(
        ...,
        description="Why they'd save this",
    )

    # Tone guidance
    tone_shift_instruction: str = Field(
        ...,
        description="How tone shifts across the piece (e.g., 'Start sharp → Move clinical → End warm')",
    )

    # Re-engagement Architecture (CRITICAL FOR RETENTION)
    primary_hook: str = Field(
        ...,
        description="The scroll-stopper (0-3 sec). Accusation, recognition, or pattern violation.",
    )
    secondary_hook: str = Field(
        ...,
        description="The re-engagement (8-12 sec). 'And it gets worse...' energy. Escalates when attention drifts.",
    )
    pivot_hook: str = Field(
        ...,
        description="The revelation setup (18-25 sec). 'But here's what's actually happening...' Signals payoff.",
    )
    screenshot_moment: str = Field(
        ...,
        description="The shareable line (25-35 sec). Isolated, quotable, standalone. The send-to-someone moment.",
    )
    open_loop: str = Field(
        ...,
        description="The implication (final 5 sec). NOT a conclusion—an open question that makes them sit with it.",
    )

    # Share Engineering
    share_message: str = Field(
        ...,
        description="What they'd type when sending it (e.g., 'this is literally you').",
    )

    # DEPRECATED: Keep for backward compatibility during transition
    emotional_journey: Optional[EmotionalJourney] = Field(
        default=None,
        description="DEPRECATED: Use emotional_arc instead",
    )
    mode_energy_note: Optional[str] = Field(
        default=None,
        description="DEPRECATED: Energy is now per-mode in mode_sequence",
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
    core_truth: str = Field(..., description="The irreducible insight (THE DESTINATION)")
    counter_truth: str = Field(..., description="The lie/anxiety the audience holds (THE STARTING POINT)")
    contrast_pair: str = Field(..., description="The A→B journey phrase")
    requires_heavy_reframe: bool = Field(default=False)
    suggested_reframe: Optional[str] = Field(default=None)
    strongest_hook: str = Field(..., description="Best hook element")
    primary_emotion: str = Field(..., description="Primary visceral emotion")
    secondary_emotion: str = Field(..., description="Secondary emotion")

    # From Stage 1: Platform-Native Extraction (RETENTION)
    hook_ammunition: List[str] = Field(
        default_factory=list,
        description="3 specific, visceral opening lines for immediate recognition",
    )
    hyper_specific_moment: str = Field(
        default="",
        description="One extremely specific behavior that signals the larger pattern",
    )
    screenshot_candidates: List[str] = Field(
        default_factory=list,
        description="2-3 standalone lines that work without context",
    )
    accusation_angle: str = Field(
        default="",
        description="The uncomfortable truth framed as behavior exposure",
    )
    share_trigger_person: str = Field(
        default="",
        description="The SPECIFIC person type they'll send this to",
    )

    # From Stage 2: New Mode Sequence (Manson Protocol)
    mode_sequence: ModeSequence = Field(
        ...,
        description="Three-part mode journey: opener → bridge → closer",
    )
    emotional_arc: EmotionalArc = Field(
        ...,
        description="5-stage continuous emotional arc with pacing",
    )
    tone_shift_instruction: str = Field(
        ...,
        description="How tone shifts across the piece",
    )

    # From Stage 2: Engagement triggers
    physical_response_goal: str = Field(...)
    share_trigger: str = Field(...)
    share_target: str = Field(...)

    # From Stage 2: Re-engagement Architecture (RETENTION)
    primary_hook: str = Field(
        default="",
        description="The scroll-stopper (0-3 sec)",
    )
    secondary_hook: str = Field(
        default="",
        description="The re-engagement (8-12 sec)",
    )
    pivot_hook: str = Field(
        default="",
        description="The revelation setup (18-25 sec)",
    )
    screenshot_moment: str = Field(
        default="",
        description="The shareable line (25-35 sec)",
    )
    open_loop: str = Field(
        default="",
        description="The implication (final 5 sec)",
    )
    share_message: str = Field(
        default="",
        description="What they'd type when sending it",
    )

    # BACKWARD COMPATIBILITY: resolved_mode derived from opener.mode
    resolved_mode: str = Field(
        ...,
        description="Primary mode (opener.mode) - kept for backward compatibility",
    )
    structural_note: Optional[str] = Field(
        default=None,
        description="DEPRECATED: Structural guidance now in mode.function",
    )

    # DEPRECATED: Keep for existing downstream consumers
    emotional_journey: Optional[EmotionalJourney] = Field(
        default=None,
        description="DEPRECATED: Use emotional_arc instead",
    )
    mode_energy_note: Optional[str] = Field(
        default=None,
        description="DEPRECATED: Energy is now per-mode in mode_sequence",
    )

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
# STAGE 2.5: LOGIC SKELETON (THE STRUCTURAL PLAN)
# ============================================================================


class CarouselSlideSpec(BaseModel):
    """Specification for a single slide in the carousel skeleton (RETENTION-OPTIMIZED)."""

    slide_number: int = Field(..., ge=1, le=10, description="Slide number (1-indexed)")
    phase: str = Field(
        ...,
        description="Phase: SCROLL_STOP, COMMITMENT, MECHANISM, TURN, SHARE, or SAVE_TRIGGER",
    )
    purpose: str = Field(..., description="What this slide accomplishes")
    mode: str = Field(..., description="Mode for this slide")
    energy: float = Field(..., ge=0.0, le=1.0, description="Energy level 0.0-1.0")
    swipe_trigger: str = Field(..., description="Why they MUST swipe to the next slide")
    content_direction: str = Field(..., description="Specific instruction for Stage 3")
    is_save_trigger: bool = Field(default=False, description="Whether this slide is designed to trigger saves")
    is_screenshot_worthy: bool = Field(default=False, description="Whether this slide works as a standalone screenshot")
    resolves_from_previous: Optional[str] = Field(
        default=None,
        description="What tension from previous slide this resolves (None for slide 1)",
    )
    creates_for_next: Optional[str] = Field(
        default=None,
        description="Tension this slide creates for the next (None for final slide)",
    )


class CarouselPhaseSpec(BaseModel):
    """Phase structure specification for carousel."""

    slides: List[int] = Field(..., description="Which slides belong to this phase")
    function: str = Field(..., description="What this phase accomplishes")


class CarouselSkeleton(BaseModel):
    """
    Stage 2.5 output for CAROUSEL format (RETENTION-OPTIMIZED).

    The structural plan that Stage 3 must follow.
    Ensures swipe architecture and save triggers.
    """

    total_slides: int = Field(..., ge=6, le=10, description="Total number of slides (6-10)")
    slides: List[CarouselSlideSpec] = Field(
        ...,
        min_length=6,
        max_length=10,
        description="The slide-by-slide skeleton",
    )
    primary_save_slides: List[int] = Field(
        default_factory=list,
        description="Which slides are designed as save triggers (typically 6-7)",
    )
    share_slide: int = Field(
        ...,
        ge=1,
        le=10,
        description="Which slide is the share trigger (usually the last slide)",
    )
    swipe_chain_validation: List[str] = Field(
        default_factory=list,
        description="List of 'Since slide N... then slide N+1...' validations",
    )
    # Legacy fields (optional for backward compatibility)
    narrative_arc_summary: Optional[str] = Field(
        default=None,
        description="From [State A] to [State B] via [Mechanism]",
    )
    phase_structure: Optional[Dict[str, CarouselPhaseSpec]] = Field(
        default=None,
        description="Phase structure (optional, derived from skeleton)",
    )
    tone_progression: Optional[str] = Field(
        default=None,
        description="How tone shifts across slides",
    )
    dependency_chain_valid: Optional[bool] = Field(
        default=None,
        description="True if all swipe chain tests pass",
    )


class ReelBeatSpec(BaseModel):
    """Specification for a single beat in the reel skeleton."""

    beat: int = Field(..., ge=1, le=6, description="Beat number (1-indexed)")
    name: str = Field(
        ...,
        description="Beat name: PRIMARY_HOOK, ESCALATION, SECONDARY_HOOK, THE_MECHANISM, SCREENSHOT_MOMENT, OPEN_LOOP",
    )
    mode: str = Field(..., description="Mode for this beat")
    function: str = Field(..., description="What this beat must accomplish")
    duration_seconds: int = Field(..., ge=1, le=20, description="Target duration in seconds")
    energy: float = Field(..., ge=0.0, le=1.0, description="Energy level 0.0-1.0")
    sentence_style: str = Field(
        ...,
        description="How sentences should be structured (e.g., 'Short. Punchy. Incomplete.')",
    )
    breath_point: bool = Field(
        default=False,
        description="True if this beat is a pause/breath moment",
    )
    ends_with: str = Field(..., description="What state/tension this beat ends with")
    hook_type: Optional[str] = Field(
        default=None,
        description="For beats 1 and 3: ACCUSATION, RECOGNITION, PATTERN_VIOLATION, or INCOMPLETE_LOOP",
    )
    content_direction: str = Field(
        default="",
        description="Specific instruction for Stage 3 generation",
    )


class ReelPacingValidation(BaseModel):
    """Validation results for reel pacing architecture."""

    has_breath_point: bool = Field(..., description="At least one breath beat exists")
    energy_varies: bool = Field(..., description="Energy level changes across beats")
    mode_shifts: bool = Field(..., description="Mode changes at least once")
    not_wall_of_sound: bool = Field(..., description="Not uniform intensity throughout")


class ReelSkeleton(BaseModel):
    """
    Stage 2.5 output for REEL format.

    The beat structure that Stage 3 must follow.
    Ensures rhythmic variation and breath architecture.
    """

    narrative_arc_summary: str = Field(
        ...,
        description="From [State A] to [State B] via [Mechanism]",
    )
    total_duration_target: int = Field(
        ...,
        ge=15,
        le=60,
        description="Target duration in seconds (15-60)",
    )
    beat_structure: List[ReelBeatSpec] = Field(
        ...,
        min_length=3,
        max_length=6,
        description="The beat-by-beat structure",
    )
    pacing_validation: ReelPacingValidation = Field(
        ...,
        description="Pacing architecture validation results",
    )


class QuoteSkeleton(BaseModel):
    """
    Stage 2.5 output for QUOTE format.

    Simplified skeleton for single-image quotes.
    """

    core_tension: str = Field(
        ...,
        description="The single tension the quote creates",
    )
    resolution_style: str = Field(
        ...,
        description="How the quote resolves or leaves open (implication vs statement)",
    )
    mode: str = Field(..., description="Primary mode for the quote")
    energy: float = Field(..., ge=0.0, le=1.0, description="Energy level")
    screenshot_quality: str = Field(
        ...,
        description="Why someone would screenshot this (the 'tattoo test')",
    )


class Stage2_5Result(BaseModel):
    """Result from Stage 2.5 logic skeleton generation."""

    schedule_id: str = Field(..., description="UUID of the ContentSchedule row")
    trace_id: str = Field(..., description="Trace ID for lineage")
    format_type: str = Field(..., description="REEL, CAROUSEL, or QUOTE")

    # Only one of these will be populated based on format_type
    carousel_skeleton: Optional[CarouselSkeleton] = Field(default=None)
    reel_skeleton: Optional[ReelSkeleton] = Field(default=None)
    quote_skeleton: Optional[QuoteSkeleton] = Field(default=None)

    error: Optional[str] = Field(default=None, description="Error if skeleton generation failed")


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
# STAGE 3.5: COHERENCE AUDIT (RETENTION-OPTIMIZED)
# ============================================================================


class TransitionAudit(BaseModel):
    """Audit of a single transition between units."""

    from_unit: int = Field(..., description="Source unit number (e.g., slide 1 or beat 1)")
    to_unit: int = Field(..., description="Target unit number (e.g., slide 2 or beat 2)")
    since_then_sentence: str = Field(
        ...,
        description="The completed 'Since... Then...' sentence",
    )
    passes: bool = Field(..., description="True if transition maintains narrative thread")
    failure_type: Optional[str] = Field(
        default=None,
        description="Failure type if invalid: PLATEAU, RESET, REDUNDANCY, BROKEN_HANDOVER, ORPHAN_PUNCH",
    )
    failure_detail: Optional[str] = Field(
        default=None,
        description="Specific issue description",
    )


class ModeAudit(BaseModel):
    """Audit of mode adherence for a single unit."""

    unit_number: int = Field(..., description="Unit number being audited")
    specified_mode: str = Field(..., description="Mode specified in skeleton")
    detected_mode: str = Field(..., description="Mode detected in generated content")
    passes: bool = Field(..., description="True if modes match")
    violation_detail: Optional[str] = Field(
        default=None,
        description="Description of the violation if modes don't match",
    )


class NarrativeCoherenceAudit(BaseModel):
    """Complete narrative coherence audit (Part 1 of Stage 3.5)."""

    sequence_integrity_score: int = Field(
        ...,
        ge=1,
        le=10,
        description="Overall sequence integrity score (must be >= 7 to pass)",
    )
    is_collection_not_sequence: bool = Field(
        ...,
        description="True if content is a collection of unrelated units, not a sequence",
    )
    transition_audits: List[TransitionAudit] = Field(
        ...,
        description="Audit results for each transition",
    )
    mode_audits: List[ModeAudit] = Field(
        ...,
        description="Mode adherence audit for each unit",
    )
    energy_curve_valid: bool = Field(..., description="Energy varies as specified")
    energy_plateaus: List[str] = Field(
        default_factory=list,
        description="Unit pairs with energy plateaus (e.g., '3→4')",
    )
    premature_peak: bool = Field(
        default=False,
        description="True if peak energy occurs too early",
    )
    peak_location: int = Field(
        default=1,
        description="Which unit has the peak energy",
    )
    narrative_passes: bool = Field(
        ...,
        description="True if narrative coherence passes all tests",
    )


# ============================================================================
# REEL RETENTION AUDIT
# ============================================================================


class ReelRetentionAudit(BaseModel):
    """Reel-specific retention mechanics audit."""

    # RT1: Hook Implementation
    hook_matches_type: bool = Field(..., description="Hook matches skeleton's hook_type")
    hook_is_specific: bool = Field(..., description="Hook uses specific, visceral language")
    hook_creates_recognition: bool = Field(..., description="Hook creates immediate recognition")
    hook_implementation_score: int = Field(..., ge=1, le=10, description="Overall hook score")
    hook_failure_detail: Optional[str] = Field(default=None, description="Hook failure details")

    # RT2: Re-engagement Beat
    reengagement_present: bool = Field(..., description="Secondary hook exists at 10-15s")
    reengagement_at_correct_position: bool = Field(..., description="Re-engagement at correct time")
    reengagement_has_pattern_interrupt: bool = Field(..., description="Re-engagement interrupts pattern")
    reengagement_failure_detail: Optional[str] = Field(default=None, description="Re-engagement failure details")

    # RT3: Screenshot Line
    screenshot_line_exists: bool = Field(..., description="Clear screenshot line exists")
    screenshot_line_isolated: bool = Field(..., description="Screenshot line is isolated")
    screenshot_line_standalone: bool = Field(..., description="Screenshot line works without context")
    screenshot_line_under_15_words: bool = Field(..., description="Screenshot line is under 15 words")
    screenshot_line_content: Optional[str] = Field(default=None, description="The screenshot line")
    screenshot_failure_detail: Optional[str] = Field(default=None, description="Screenshot failure details")

    # RT4: Open Loop Ending
    ending_is_open_loop: bool = Field(..., description="Ending creates incompleteness")
    ending_avoids_summary: bool = Field(..., description="Ending avoids summarizing")
    ending_avoids_advice: bool = Field(..., description="Ending avoids giving advice")
    ending_failure_detail: Optional[str] = Field(default=None, description="Ending failure details")

    # RT5: Breath Architecture
    has_breath_moment: bool = Field(..., description="At least one soft/validating moment")
    has_energy_variation: bool = Field(..., description="Energy drops below 0.5 somewhere")
    has_sentence_length_variation: bool = Field(..., description="Varied sentence lengths")
    breath_failure_detail: Optional[str] = Field(default=None, description="Breath failure details")

    # Overall
    retention_passes: bool = Field(..., description="True if all retention tests pass")


# ============================================================================
# CAROUSEL RETENTION AUDIT
# ============================================================================


class SlideSwipeAudit(BaseModel):
    """Audit of swipe trigger for a single slide."""

    slide_number: int = Field(..., description="Slide number")
    specified_swipe_trigger: str = Field(..., description="Swipe trigger from skeleton")
    swipe_trigger_implemented: bool = Field(..., description="Trigger properly implemented")
    slide_feels_complete: bool = Field(..., description="True if slide feels complete (bad except for final)")
    failure_detail: Optional[str] = Field(default=None, description="Swipe trigger failure details")


class CarouselRetentionAudit(BaseModel):
    """Carousel-specific retention mechanics audit."""

    # CT1: Slide 1 Incompleteness
    slide_1_incomplete: bool = Field(..., description="Slide 1 is an incomplete thought")
    slide_1_creates_swipe_compulsion: bool = Field(..., description="Slide 1 drives swipe action")
    slide_1_is_specific: bool = Field(..., description="Slide 1 uses specific language")
    slide_1_failure_detail: Optional[str] = Field(default=None, description="Slide 1 failure details")

    # CT2: Swipe Trigger Chain
    swipe_audits: List[SlideSwipeAudit] = Field(..., description="Audit of each slide's swipe trigger")
    swipe_chain_score: int = Field(..., ge=1, le=10, description="% of working swipe triggers")
    filler_slides: List[int] = Field(default_factory=list, description="Slide numbers that are filler")

    # CT3: Save Trigger Slides
    save_trigger_slides_specified: List[int] = Field(..., description="Slides marked as save triggers")
    save_triggers_valid: bool = Field(..., description="Save trigger slides are reference-worthy")
    save_trigger_failure_detail: Optional[str] = Field(default=None, description="Save trigger failure details")

    # CT4: Share Slide (Final)
    share_slide_standalone: bool = Field(..., description="Final slide works without context")
    share_slide_under_20_words: bool = Field(..., description="Final slide is under 20 words")
    share_slide_is_knockout: bool = Field(..., description="Final slide is a knockout punch, not conclusion")
    share_slide_content: Optional[str] = Field(default=None, description="The final slide content")
    share_slide_failure_detail: Optional[str] = Field(default=None, description="Share slide failure details")

    # CT5: Drip Architecture
    drip_not_dump: bool = Field(..., description="Mechanism revealed piece by piece")
    dump_slides: List[int] = Field(default_factory=list, description="Slides with info dumps")
    drip_failure_detail: Optional[str] = Field(default=None, description="Drip architecture failure details")

    # Overall
    retention_passes: bool = Field(..., description="True if all retention tests pass")


# ============================================================================
# QUOTE RETENTION AUDIT
# ============================================================================


class QuoteRetentionAudit(BaseModel):
    """Quote-specific retention mechanics audit."""

    # QT1: Standalone Power
    standalone_power: int = Field(..., ge=1, le=10, description="Standalone power score")
    works_without_context: bool = Field(..., description="Quote works with zero context")
    hits_immediately: bool = Field(..., description="Quote hits immediately without setup")
    standalone_failure_detail: Optional[str] = Field(default=None, description="Standalone failure details")

    # QT2: Specificity
    specificity_score: int = Field(..., ge=1, le=10, description="Specificity score")
    has_specific_behaviors: bool = Field(..., description="Contains specific moments/behaviors")
    avoids_abstractions: bool = Field(..., description="Avoids abstract concepts")
    specificity_failure_detail: Optional[str] = Field(default=None, description="Specificity failure details")

    # QT3: Visual Rhythm
    visual_rhythm_ok: bool = Field(..., description="Quote has good visual rhythm")
    appropriate_length: bool = Field(..., description="Quote is appropriate length")
    good_line_breaks: bool = Field(..., description="Natural line breaks in good places")
    visual_failure_detail: Optional[str] = Field(default=None, description="Visual rhythm failure details")

    # Overall
    retention_passes: bool = Field(..., description="True if all retention tests pass")


# ============================================================================
# REWRITE INSTRUCTION
# ============================================================================


class CoherenceRewriteInstruction(BaseModel):
    """Specific rewrite instruction from coherence audit."""

    priority: int = Field(..., ge=1, description="Priority (1 = highest)")
    failure_category: str = Field(..., description="NARRATIVE or RETENTION")
    failure_test: str = Field(..., description="Which test failed")
    unit_affected: str = Field(..., description="Beat number, slide number, or 'overall'")
    current_content: str = Field(..., description="Quote of the problematic content")
    what_is_wrong: str = Field(..., description="Specific description of the problem")
    rewrite_example: str = Field(..., description="Concrete example of how to fix")
    impact_on_retention: str = Field(..., description="CRITICAL, HIGH, or MEDIUM")


# ============================================================================
# COMPLETE AUDIT OUTPUT (REPLACES OLD CoherenceAuditResult)
# ============================================================================


class CoherenceAuditResult(BaseModel):
    """
    Stage 3.5 LLM output: Coherence + Retention audit evaluation.

    Evaluates BOTH narrative coherence AND format-specific retention mechanics.
    Both must pass for overall pass.
    """

    # Format
    format_detected: str = Field(..., description="REEL, CAROUSEL, or QUOTE")

    # Narrative audit (all formats)
    narrative_audit: NarrativeCoherenceAudit = Field(
        ...,
        description="Complete narrative coherence audit",
    )

    # Retention audit (format-specific, only one populated)
    reel_retention_audit: Optional[ReelRetentionAudit] = Field(
        default=None,
        description="Reel-specific retention audit (if format is REEL)",
    )
    carousel_retention_audit: Optional[CarouselRetentionAudit] = Field(
        default=None,
        description="Carousel-specific retention audit (if format is CAROUSEL)",
    )
    quote_retention_audit: Optional[QuoteRetentionAudit] = Field(
        default=None,
        description="Quote-specific retention audit (if format is QUOTE)",
    )

    # Overall results
    overall_passes: bool = Field(..., description="True if both narrative AND retention pass")
    narrative_passes: bool = Field(..., description="True if narrative coherence passes")
    retention_passes: bool = Field(..., description="True if retention mechanics pass")

    # Legacy field for backward compatibility
    coherence_pass: bool = Field(
        ...,
        description="Alias for overall_passes (backward compatibility)",
    )
    rewrite_required: bool = Field(
        ...,
        description="True if content must return to Stage 3",
    )

    # Rewrite instructions (if failed)
    rewrite_instructions: List[CoherenceRewriteInstruction] = Field(
        default_factory=list,
        description="Priority-ranked rewrite instructions",
    )

    # Summary
    audit_summary: str = Field(..., description="One-paragraph summary of audit")
    primary_failure: Optional[str] = Field(
        default=None,
        description="Most critical issue if failed",
    )
    rewrite_instruction: Optional[str] = Field(
        default=None,
        description="Legacy field: primary rewrite instruction for Stage 3",
    )

    # Legacy compatibility: sequence_integrity_score
    @property
    def sequence_integrity_score(self) -> int:
        """Backward compatibility: get sequence integrity score from narrative audit."""
        return self.narrative_audit.sequence_integrity_score

    model_config = {"arbitrary_types_allowed": True}


class Stage3_5Result(BaseModel):
    """Result from Stage 3.5 coherence audit."""

    schedule_id: str = Field(..., description="UUID of the ContentSchedule row")
    trace_id: str = Field(..., description="Trace ID for lineage")
    audit_result: Optional[CoherenceAuditResult] = Field(
        default=None,
        description="Coherence audit result (None if error)",
    )
    error: Optional[str] = Field(default=None, description="Error if audit failed")


# ============================================================================
# STAGE 4: SELF-CRITIQUE
# ============================================================================


class CritiqueScores(BaseModel):
    """
    Scores from Stage 4 critique evaluation (1-10 scale).

    7 criteria (revised):
    1. Scroll-stop power
    2. AI voice risk (expanded with uniformity detection)
    3. Share impulse
    4. Emotional precision (arc-based)
    5. Mode progression (replaces mode fidelity)
    6. Pacing & breath
    7. Format execution (revised for psychological flow)
    """

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
        description="Humanity detection. Higher = more human. Checks uniformity, contrast, rhythm.",
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
        description="Does this hit the target emotional arc with peaks and valleys?",
    )
    mode_progression: int = Field(
        ...,
        ge=1,
        le=10,
        description="Does content shift modes appropriately? Each shift earned and impactful?",
    )
    pacing_breath: int = Field(
        ...,
        ge=1,
        le=10,
        description="Rhythmic variation, energy peaks/valleys, strategic pauses?",
    )
    format_execution: int = Field(
        ...,
        ge=1,
        le=10,
        description="Format-specific execution: Reels=timing, Carousels=psychological flow, Quotes=standalone power",
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

