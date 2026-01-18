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
    """Specification for a single slide in the carousel skeleton."""

    slide: int = Field(..., ge=1, le=10, description="Slide number (1-indexed)")
    phase: str = Field(
        ...,
        description="Phase name: THE_TRAP, THE_SHIFT, or THE_RELEASE",
    )
    mode: str = Field(..., description="Mode for this slide (can include transitions like 'ROAST_MASTER → MIRROR')")
    purpose: str = Field(..., description="What this slide must accomplish")
    energy_level: float = Field(..., ge=0.0, le=1.0, description="Energy level 0.0-1.0")
    resolves_tension: Optional[str] = Field(
        default=None,
        description="What tension from previous slide this resolves (None for slide 1)",
    )
    creates_tension: str = Field(..., description="Tension this slide creates for the next")
    handover_to_next: str = Field(..., description="What the reader needs/wants after this slide")


class CarouselPhaseSpec(BaseModel):
    """Phase structure specification for carousel."""

    slides: List[int] = Field(..., description="Which slides belong to this phase")
    function: str = Field(..., description="What this phase accomplishes")


class CarouselSkeleton(BaseModel):
    """
    Stage 2.5 output for CAROUSEL format.

    The structural plan that Stage 3 must follow.
    Ensures psychological sequence, not just visual adjacency.
    """

    narrative_arc_summary: str = Field(
        ...,
        description="From [State A] to [State B] via [Mechanism]",
    )
    total_slides: int = Field(..., ge=6, le=10, description="Total number of slides (6-10)")
    skeleton: List[CarouselSlideSpec] = Field(
        ...,
        min_length=6,
        max_length=10,
        description="The slide-by-slide skeleton",
    )
    phase_structure: Dict[str, CarouselPhaseSpec] = Field(
        ...,
        description="THE_TRAP, THE_SHIFT, THE_RELEASE phases",
    )
    tone_progression: str = Field(
        ...,
        description="How tone shifts (e.g., 'Sharp (1-2) → Clinical (3-5) → Warm (6-8)')",
    )
    dependency_chain_valid: bool = Field(
        ...,
        description="True if all 'Since... Then...' tests pass",
    )
    golden_thread_test: str = Field(
        ...,
        description="The complete 'Since... Then...' chain as a string",
    )


class ReelBeatSpec(BaseModel):
    """Specification for a single beat in the reel skeleton."""

    beat: int = Field(..., ge=1, le=6, description="Beat number (1-indexed)")
    name: str = Field(
        ...,
        description="Beat name: THE_HOOK, THE_BUILD, THE_BREATH, THE_TRUTH, THE_LAND",
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
# STAGE 3.5: COHERENCE AUDIT
# ============================================================================


class TransitionResult(BaseModel):
    """Result from checking a single transition (e.g., slide 1→2)."""

    transition: str = Field(..., description="Transition label (e.g., '1→2')")
    valid: bool = Field(..., description="True if transition maintains narrative thread")
    failure_type: Optional[str] = Field(
        default=None,
        description="Failure type if invalid: PLATEAU, RESET, REDUNDANCY, etc.",
    )
    issue: Optional[str] = Field(default=None, description="Specific issue description")


class SinceThenCompletion(BaseModel):
    """Result from the 'Since... Then...' test for a transition pair."""

    pair: str = Field(..., description="Transition pair (e.g., '1→2')")
    completion: Optional[str] = Field(
        default=None,
        description="The completed 'Since X, then Y' sentence (None if cannot complete)",
    )
    issue: Optional[str] = Field(
        default=None,
        description="Why the sentence cannot be completed (if applicable)",
    )


class CoherenceFailure(BaseModel):
    """Details of a specific coherence failure requiring rewrite."""

    location: str = Field(..., description="Where the failure occurred (e.g., 'Slide 4')")
    failure_type: str = Field(
        ...,
        description="PLATEAU, RESET, REDUNDANCY, PREMATURE_PEAK, ORPHAN_PUNCH, MODE_VIOLATION, BROKEN_HANDOVER",
    )
    issue: str = Field(..., description="Specific problem identified")
    fix: str = Field(..., description="Specific fix instruction")


class CoherenceAuditResult(BaseModel):
    """
    Stage 3.5 LLM output: Coherence audit evaluation.

    Determines whether generated content functions as a SEQUENCE
    or merely a COLLECTION of unrelated units.
    """

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

    # Dependency chain validation
    dependency_chain_results: List[TransitionResult] = Field(
        ...,
        description="Results for each transition (slide-to-slide or beat-to-beat)",
    )

    # Energy curve validation
    energy_curve_valid: bool = Field(..., description="Energy varies as specified")
    energy_curve_issues: List[str] = Field(
        default_factory=list,
        description="Issues with energy curve (e.g., plateaus)",
    )

    # Mode adherence
    mode_adherence_valid: bool = Field(..., description="Modes match skeleton specification")
    mode_violations: List[str] = Field(
        default_factory=list,
        description="Mode violations found",
    )

    # Since... Then... test results
    since_then_completions: List[SinceThenCompletion] = Field(
        ...,
        description="Results of 'Since... Then...' test for each transition",
    )

    # Overall result
    coherence_pass: bool = Field(
        ...,
        description="True if content passes coherence audit",
    )
    failures_requiring_rewrite: List[CoherenceFailure] = Field(
        default_factory=list,
        description="Failures that require rewriting",
    )
    rewrite_required: bool = Field(
        ...,
        description="True if content must return to Stage 3",
    )
    rewrite_instruction: Optional[str] = Field(
        default=None,
        description="Specific rewrite instruction for Stage 3",
    )


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

