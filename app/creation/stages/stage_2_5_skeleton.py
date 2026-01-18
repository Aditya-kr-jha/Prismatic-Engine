"""
Stage 2.5: Logic Skeleton Generator.

Constructs the structural plan BEFORE any copy is written.
Format-specific: Carousel (slides), Reel (beats), Quote (simplified).
"""

import json
import logging
from typing import Optional, Union

from langchain_openai import ChatOpenAI

from app.config import settings
from app.creation.prompts.stage_2_5_carousel import STAGE2_5_CAROUSEL_PROMPT
from app.creation.prompts.stage_2_5_reel import STAGE2_5_REEL_PROMPT
from app.creation.prompts.stage_2_5_quote import STAGE2_5_QUOTE_PROMPT
from app.creation.schemas import (
    CarouselSkeleton,
    GenerationContext,
    QuoteSkeleton,
    ReelSkeleton,
    Stage2_5Result,
)
from app.creation.temperature_config import creation_temperatures

logger = logging.getLogger(__name__)

# Type alias for skeletons
Skeleton = Union[CarouselSkeleton, ReelSkeleton, QuoteSkeleton]


class Stage2_5SkeletonGenerator:
    """
    LLM-based logic skeleton generator for Stage 2.5.

    Constructs the structural plan that Stage 3 must follow:
    - Carousel: Slide-by-slide skeleton with phases and handovers
    - Reel: Beat structure with pacing and breath points
    - Quote: Simplified skeleton with tension and resolution
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the Stage 2.5 skeleton generator.

        Args:
            model: LLM model name (defaults to settings.CREATION_LLM_MODEL)
            temperature: LLM temperature (defaults to stage_2_target temperature)
        """
        self.model = model or settings.CREATION_LLM_MODEL
        # Use a slightly lower temperature for structural planning
        self.temperature = (
            temperature
            if temperature is not None
            else creation_temperatures.stage_2_target * 0.9
        )

        # Build format-specific chains
        self._chains = {}
        self._build_chains()

    def _build_chains(self) -> None:
        """Build LLM chains for each format."""
        formats = {
            "CAROUSEL": (STAGE2_5_CAROUSEL_PROMPT, CarouselSkeleton),
            "REEL": (STAGE2_5_REEL_PROMPT, ReelSkeleton),
            "QUOTE": (STAGE2_5_QUOTE_PROMPT, QuoteSkeleton),
        }

        for format_type, (prompt, schema) in formats.items():
            llm = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                api_key=settings.OPENAI_API_KEY,
            )

            structured_llm = llm.with_structured_output(
                schema,
                method="json_schema",
            )

            self._chains[format_type] = prompt | structured_llm

    async def generate_skeleton(
        self,
        context: GenerationContext,
    ) -> Stage2_5Result:
        """
        Generate the logic skeleton for the given GenerationContext.

        Args:
            context: GenerationContext from Stage 2

        Returns:
            Stage2_5Result with format-specific skeleton
        """
        format_type = context.required_format.upper()

        result = Stage2_5Result(
            schedule_id=context.schedule_id,
            trace_id=context.trace_id,
            format_type=format_type,
        )

        chain = self._chains.get(format_type)
        if not chain:
            result.error = f"Unknown format type: {format_type}"
            logger.error("[CREATION:S2.5] unknown_format format=%s", format_type)
            return result

        # Build prompt input from GenerationContext
        prompt_input = {
            # Core content
            "core_truth": context.core_truth,
            "required_pillar": context.required_pillar,
            # Mode sequence
            "opener_mode": context.mode_sequence.opener.mode,
            "opener_energy": context.mode_sequence.opener.energy,
            "opener_function": context.mode_sequence.opener.function,
            "bridge_mode": context.mode_sequence.bridge.mode,
            "bridge_energy": context.mode_sequence.bridge.energy,
            "bridge_function": context.mode_sequence.bridge.function,
            "closer_mode": context.mode_sequence.closer.mode,
            "closer_energy": context.mode_sequence.closer.energy,
            "closer_function": context.mode_sequence.closer.function,
            # Emotional arc
            "entry_state": context.emotional_arc.entry_state,
            "destabilization_trigger": context.emotional_arc.destabilization_trigger,
            "resistance_point": context.emotional_arc.resistance_point,
            "breakthrough_moment": context.emotional_arc.breakthrough_moment,
            "landing_state": context.emotional_arc.landing_state,
            "pacing_note": context.emotional_arc.pacing_note,
            # Tone
            "tone_shift_instruction": context.tone_shift_instruction,
            # For Quote
            "primary_emotion": context.primary_emotion,
            "share_trigger": context.share_trigger,
            "share_target": context.share_target,
        }

        logger.debug(
            "[CREATION:S2.5] generating skeleton format=%s trace_id=%s",
            format_type,
            context.trace_id,
        )

        try:
            skeleton = await chain.ainvoke(prompt_input)

            # Assign to appropriate field based on format
            if format_type == "CAROUSEL":
                result.carousel_skeleton = skeleton
            elif format_type == "REEL":
                result.reel_skeleton = skeleton
            elif format_type == "QUOTE":
                result.quote_skeleton = skeleton

            logger.debug(
                "[CREATION:S2.5] skeleton complete format=%s trace_id=%s",
                format_type,
                context.trace_id,
            )

        except Exception as e:
            result.error = str(e)
            logger.error(
                "[CREATION:S2.5] failed format=%s trace_id=%s error=%s",
                format_type,
                context.trace_id,
                str(e)[:100],
            )

        return result

    def get_skeleton_for_stage3(
        self,
        result: Stage2_5Result,
    ) -> Optional[str]:
        """
        Extract skeleton as JSON string for Stage 3 prompt injection.

        Args:
            result: Stage2_5Result from generate_skeleton

        Returns:
            JSON string of the skeleton, or None if no skeleton
        """
        skeleton = None
        if result.carousel_skeleton:
            skeleton = result.carousel_skeleton
        elif result.reel_skeleton:
            skeleton = result.reel_skeleton
        elif result.quote_skeleton:
            skeleton = result.quote_skeleton

        if skeleton:
            return json.dumps(skeleton.model_dump(), indent=2, default=str)
        return None
