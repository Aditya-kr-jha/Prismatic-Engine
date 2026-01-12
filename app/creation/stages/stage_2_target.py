"""
Stage 2: Resolve Mode & Set Emotional Target.

Resolves generation mode from Format × Pillar matrix and defines
emotional architecture using LLM-based targeting.
"""

import logging
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI

from app.config import settings
from app.creation.mode_matrix import resolve_mode
from app.creation.prompts.stage_2 import STAGE2_PROMPT
from app.creation.schemas import (
    GenerationContext,
    Stage1Analysis,
    Stage2Targeting,
)
from app.creation.temperature_config import creation_temperatures

logger = logging.getLogger(__name__)


class Stage2Targeter:
    """
    LLM-based emotional targeting for Stage 2.

    Combines mode matrix lookup with LLM-generated emotional architecture.
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
        Resolve mode and generate emotional targeting for a content piece.

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
        # Step 1: Resolve mode from matrix
        resolved_mode, structural_note = resolve_mode(required_format, required_pillar)

        logger.debug(
            "Stage2 mode resolved: format=%s, pillar=%s -> mode=%s",
            required_format,
            required_pillar,
            resolved_mode,
        )

        # Step 2: Run LLM targeting
        targeting: Stage2Targeting = await self.chain.ainvoke(
            {
                "required_format": required_format,
                "required_pillar": required_pillar,
                "resolved_mode": resolved_mode,
                "structural_note": structural_note,
                "core_truth": stage1_analysis.core_truth,
                "primary_emotion": stage1_analysis.emotional_core.primary_emotion,
                "why_someone_shares_this": stage1_analysis.emotional_core.why_someone_shares_this,
                "requires_heavy_reframe": str(stage1_analysis.requires_heavy_reframe),
                "suggested_reframe": stage1_analysis.suggested_reframe or "N/A",
            }
        )

        logger.debug(
            "Stage2 targeting complete: share_target=%s, physical_response=%s",
            targeting.share_target[:30] if targeting.share_target else "N/A",
            targeting.physical_response_goal[:30]
            if targeting.physical_response_goal
            else "N/A",
        )

        # Step 3: Compile GenerationContext
        context = GenerationContext(
            # From ContentSchedule
            schedule_id=schedule_id,
            trace_id=trace_id,
            required_format=required_format,
            required_pillar=required_pillar,
            brief=brief,
            # From Stage 1
            core_truth=stage1_analysis.core_truth,
            requires_heavy_reframe=stage1_analysis.requires_heavy_reframe,
            suggested_reframe=stage1_analysis.suggested_reframe,
            strongest_hook=stage1_analysis.strongest_hook_in_material,
            primary_emotion=stage1_analysis.emotional_core.primary_emotion,
            secondary_emotion=stage1_analysis.emotional_core.secondary_emotion,
            # From Stage 2 / Matrix
            resolved_mode=resolved_mode,
            structural_note=structural_note,
            emotional_journey=targeting.emotional_journey,
            physical_response_goal=targeting.physical_response_goal,
            share_trigger=targeting.share_trigger,
            share_target=targeting.share_target,
            mode_energy_note=targeting.mode_energy_note,
        )

        return context
