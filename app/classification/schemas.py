"""
Pydantic v2 Schemas for Phase 3 Classification.

These schemas define the HARD CONTRACT between the LLM and the system.
The LLM MUST output JSON matching these schemas exactly.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.db.enums import ContentPillar, Format, EmotionalTrigger, ProofType, HookMechanism


class AtomicComponents(BaseModel):
    """
    Extracted atomic content components.

    These are reusable building blocks for downstream content creation.
    """

    core_concept: str = Field(
        ...,
        description="The central insight or idea in 1-3 sentences",
    )
    emotional_hook: str = Field(
        ...,
        description="The pain point, desire, or emotional truth that makes this resonate",
    )
    supporting_evidence: str = Field(
        ...,
        description="Research, anecdote, statistic, or example that backs the concept",
    )
    actionable_insight: str = Field(
        ...,
        description="Practical takeaway the audience can apply",
    )
    quotable_snippet: str = Field(
        ...,
        description="A punchy, screenshot-worthy line (<25 words)",
    )


class ClassificationDimensions(BaseModel):
    """
    Multi-dimensional classification for content routing.
    """

    primary_pillar: ContentPillar = Field(
        ...,
        description="Primary content pillar",
    )
    secondary_pillars: list[ContentPillar] = Field(
        default_factory=list,
        description="Up to 3 secondary pillars",
    )
    format_fit: list[Format] = Field(
        ...,
        description="Formats this content works for: REEL, CAROUSEL, QUOTE",
    )
    complexity_score: int = Field(
        ...,
        ge=1,
        le=5,
        description="1=universal truth, 5=expert-level",
    )
    emotional_triggers: list[EmotionalTrigger] = Field(
        default_factory=list,
        description="Emotions this content triggers",
    )
    proof_type: ProofType = Field(
        ...,
        description="Type of proof/evidence used",
    )
    hook_mechanism: HookMechanism = Field(
        ...,
        description="Hook type used to capture attention",
    )


class ClassificationOutput(BaseModel):
    """
    Complete LLM classification output.

    This is the schema passed to `with_structured_output()`.
    """

    atomic_components: AtomicComponents = Field(
        ...,
        description="Extracted atomic content components",
    )
    classification: ClassificationDimensions = Field(
        ...,
        description="Multi-dimensional classification",
    )
    virality_estimate: float = Field(
        ...,
        ge=0,
        le=10,
        description="Estimated virality score (0-10)",
    )
    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Classifier confidence (0-1)",
    )
    classification_notes: Optional[str] = Field(
        default=None,
        description="Optional notes on edge cases or ambiguity",
    )
