"""
Phase 5: Creation Module.

Content generation pipeline for Instagram-native posts.
Consumes ContentSchedule briefs and produces publish-ready content.

Stages:
    1. Extract & Analyze - Parse brief, extract psychological core
    2. Resolve Mode & Target - Format × Pillar matrix lookup
    3. Generate Content - Format-specific content generation
    4. Self-Critique Loop - Score and rewrite if needed
    5. Hard Filters & Storage - Final validation and DB storage
"""

from app.creation.schemas import (
    CarouselContent,
    CritiqueFailure,
    CritiqueResult,
    CritiqueScores,
    EmotionalCore,
    EmotionalJourney,
    GenerationContext,
    HardFilterResult,
    QuoteContent,
    ReelContent,
    Stage1Analysis,
    Stage2Targeting,
    Stage3Result,
    Stage4Result,
    Stage5Result,
)

__all__ = [
    "CarouselContent",
    "CritiqueFailure",
    "CritiqueResult",
    "CritiqueScores",
    "EmotionalCore",
    "EmotionalJourney",
    "GenerationContext",
    "HardFilterResult",
    "QuoteContent",
    "ReelContent",
    "Stage1Analysis",
    "Stage2Targeting",
    "Stage3Result",
    "Stage4Result",
    "Stage5Result",
]

