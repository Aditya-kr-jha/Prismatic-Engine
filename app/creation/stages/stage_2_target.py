"""
Stage 2: Mode Sequence + Emotional Arc Targeting.

Designs the mode journey (Manson Protocol) and emotional arc using LLM.
No mode matrix—the LLM determines the full sequence based on content.
"""

import logging
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI

from app.config import settings
from app.creation.prompts.stage_2 import STAGE2_PROMPT
from app.creation.schemas import (
    EmotionalJourney,
    GenerationContext,
    Stage1Analysis,
    Stage2Targeting,
)
from app.creation.temperature_config import creation_temperatures

logger = logging.getLogger(__name__)


class Stage2Targeter:
    """
    LLM-based mode sequencing and emotional targeting for Stage 2.

    Generates the full mode journey (opener → bridge → closer) and
    continuous emotional arc with pacing notes.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the Stage 2 targeter.

        Args:
            model: LLM model name (defaults to settings.CREATION_LLM_MODEL)
            temperature: LLM temperature (defaults to creation_temperatures.stage_2_target)
        """
        self.model = model or settings.CREATION_LLM_MODEL
        self.temperature = (
            temperature
            if temperature is not None
            else creation_temperatures.stage_2_target
        )

        self.llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=settings.OPENAI_API_KEY,
        )

        # Use structured output for deterministic parsing
        self.structured_llm = self.llm.with_structured_output(
            Stage2Targeting,
            method="json_schema",
        )

        # Build the chain: prompt -> structured LLM
        self.chain = STAGE2_PROMPT | self.structured_llm

    async def target(
        self,
        schedule_id: str,
        trace_id: str,
        required_format: str,
        required_pillar: str,
        brief: Dict[str, Any],
        stage1_analysis: Stage1Analysis,
    ) -> GenerationContext:
        """
        Generate mode sequence and emotional targeting for a content piece.

        The LLM determines the full mode journey (opener → bridge → closer)
        and the continuous emotional arc with pacing notes.

        Args:
            schedule_id: UUID of the ContentSchedule row
            trace_id: Trace ID for lineage
            required_format: REEL, CAROUSEL, or QUOTE
            required_pillar: Content pillar
            brief: Original content brief
            stage1_analysis: Result from Stage 1 analysis

        Returns:
            GenerationContext with all data needed for Stage 3

        Raises:
            Exception: If LLM call fails
        """
        # Run LLM targeting — LLM now determines the full mode sequence
        targeting: Stage2Targeting = await self.chain.ainvoke(
            {
                "required_format": required_format,
                "required_pillar": required_pillar,
                "counter_truth": stage1_analysis.counter_truth,
                "core_truth": stage1_analysis.core_truth,
                "primary_emotion": stage1_analysis.emotional_core.primary_emotion,
                "why_someone_shares_this": stage1_analysis.emotional_core.why_someone_shares_this,
                "requires_heavy_reframe": str(stage1_analysis.requires_heavy_reframe),
                "suggested_reframe": stage1_analysis.suggested_reframe or "N/A",
            }
        )

        # Derive resolved_mode from opener.mode for backward compatibility
        resolved_mode = targeting.mode_sequence.opener.mode

        logger.debug(
            "Stage2 mode sequence: opener=%s, bridge=%s, closer=%s",
            targeting.mode_sequence.opener.mode,
            targeting.mode_sequence.bridge.mode,
            targeting.mode_sequence.closer.mode,
        )

        logger.debug(
            "Stage2 emotional arc: entry=%s → breakthrough=%s → landing=%s",
            targeting.emotional_arc.entry_state[:30]
            if targeting.emotional_arc.entry_state
            else "N/A",
            targeting.emotional_arc.breakthrough_moment[:30]
            if targeting.emotional_arc.breakthrough_moment
            else "N/A",
            targeting.emotional_arc.landing_state[:30]
            if targeting.emotional_arc.landing_state
            else "N/A",
        )

        # Build deprecated EmotionalJourney for backward compatibility
        deprecated_journey = EmotionalJourney(
            state_1=targeting.emotional_arc.entry_state,
            state_2=targeting.emotional_arc.breakthrough_moment,
            state_3=targeting.emotional_arc.landing_state,
        )

        # Compile GenerationContext
        context = GenerationContext(
            # From ContentSchedule
            schedule_id=schedule_id,
            trace_id=trace_id,
            required_format=required_format,
            required_pillar=required_pillar,
            brief=brief,
            # From Stage 1
            core_truth=stage1_analysis.core_truth,
            counter_truth=stage1_analysis.counter_truth,
            contrast_pair=stage1_analysis.contrast_pair,
            requires_heavy_reframe=stage1_analysis.requires_heavy_reframe,
            suggested_reframe=stage1_analysis.suggested_reframe,
            strongest_hook=stage1_analysis.strongest_hook_in_material,
            primary_emotion=stage1_analysis.emotional_core.primary_emotion,
            secondary_emotion=stage1_analysis.emotional_core.secondary_emotion,
            # From Stage 2: New fields
            mode_sequence=targeting.mode_sequence,
            emotional_arc=targeting.emotional_arc,
            tone_shift_instruction=targeting.tone_shift_instruction,
            # From Stage 2: Engagement triggers
            physical_response_goal=targeting.physical_response_goal,
            share_trigger=targeting.share_trigger,
            share_target=targeting.share_target,
            # Backward compatibility
            resolved_mode=resolved_mode,
            structural_note=targeting.mode_sequence.opener.function,
            emotional_journey=deprecated_journey,
            mode_energy_note=f"Opener: {targeting.mode_sequence.opener.energy}, "
            f"Bridge: {targeting.mode_sequence.bridge.energy}, "
            f"Closer: {targeting.mode_sequence.closer.energy}",
        )

        return context
