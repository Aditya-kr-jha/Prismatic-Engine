"""
Phase 5: Creation Module.

Content generation pipeline for Instagram-native posts.
Consumes ContentSchedule briefs and produces publish-ready content.

Stages:
    1. Extract & Analyze - Parse brief, extract psychological core
    2. Resolve Mode & Target - Mode sequence (Manson Protocol) + emotional arc
    2.5. Logic Skeleton - Structural plan before copy is written
    3. Generate Content - Format-specific content generation from skeleton
    3.5. Coherence Audit - Evaluate narrative sequence + retention mechanics
    4. Self-Critique Loop - Score and rewrite if needed
    5. Hard Filters & Storage - Final validation and DB storage
"""

from app.creation.schemas import (
    CarouselContent,
    CarouselRetentionAudit,
    CarouselSkeleton,
    CoherenceAuditResult,
    CoherenceRewriteInstruction,
    CritiqueFailure,
    CritiqueResult,
    CritiqueScores,
    EmotionalArc,
    EmotionalCore,
    EmotionalJourney,
    GenerationContext,
    HardFilterResult,
    ModeAudit,
    ModeSequence,
    ModeStep,
    NarrativeCoherenceAudit,
    QuoteContent,
    QuoteRetentionAudit,
    QuoteSkeleton,
    ReelContent,
    ReelRetentionAudit,
    ReelSkeleton,
    SlideSwipeAudit,
    Stage1Analysis,
    Stage2Targeting,
    Stage2_5Result,
    Stage3Result,
    Stage3_5Result,
    Stage4Result,
    Stage5Result,
    TransitionAudit,
)

__all__ = [
    "CarouselContent",
    "CarouselRetentionAudit",
    "CarouselSkeleton",
    "CoherenceAuditResult",
    "CoherenceRewriteInstruction",
    "CritiqueFailure",
    "CritiqueResult",
    "CritiqueScores",
    "EmotionalArc",
    "EmotionalCore",
    "EmotionalJourney",
    "GenerationContext",
    "HardFilterResult",
    "ModeAudit",
    "ModeSequence",
    "ModeStep",
    "NarrativeCoherenceAudit",
    "QuoteContent",
    "QuoteRetentionAudit",
    "QuoteSkeleton",
    "ReelContent",
    "ReelRetentionAudit",
    "ReelSkeleton",
    "SlideSwipeAudit",
    "Stage1Analysis",
    "Stage2Targeting",
    "Stage2_5Result",
    "Stage3Result",
    "Stage3_5Result",
    "Stage4Result",
    "Stage5Result",
    "TransitionAudit",
]
