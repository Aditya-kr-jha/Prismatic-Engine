"""
Stage 3: Generate Content.

Format-specific content generation using GenerationContext from Stage 2.
Produces ReelContent, CarouselContent, or QuoteContent based on format.
"""

import json
import logging
from typing import Optional, Union

from langchain_openai import ChatOpenAI

from app.config import settings
from app.creation.prompts.stage_3_carousel import STAGE3_CAROUSEL_PROMPT
from app.creation.prompts.stage_3_quote import STAGE3_QUOTE_PROMPT
from app.creation.prompts.stage_3_reel import STAGE3_REEL_PROMPT
from app.creation.schemas import (
    CarouselContent,
    GenerationContext,
    QuoteContent,
    ReelContent,
    Stage3Result,
)
from app.creation.temperature_config import creation_temperatures

logger = logging.getLogger(__name__)

# Type alias for generated content
GeneratedContent = Union[ReelContent, CarouselContent, QuoteContent]


class Stage3Generator:
    """
    LLM-based content generator for Stage 3.

    Selects format-specific prompts and schemas based on GenerationContext.
    Uses temperature settings from creation_temperatures config.
    """

    def __init__(
        self,
        model: Optional[str] = None,
    ):
        """
        Initialize the Stage 3 generator.

        Args:
            model: LLM model name (defaults to settings.CREATION_LLM_MODEL)
        """
        self.model = model or settings.CREATION_LLM_MODEL

        # Build format-specific chains
        self._chains = {}
        self._build_chains()

    def _build_chains(self) -> None:
        """Build LLM chains for each format with appropriate temperatures."""
        formats = {
            "REEL": (STAGE3_REEL_PROMPT, ReelContent),
            "CAROUSEL": (STAGE3_CAROUSEL_PROMPT, CarouselContent),
            "QUOTE": (STAGE3_QUOTE_PROMPT, QuoteContent),
        }

        for format_type, (prompt, schema) in formats.items():
            temperature = creation_temperatures.stage_3_generate.get(format_type)

            llm = ChatOpenAI(
                model=self.model,
                temperature=temperature,
                api_key=settings.OPENAI_API_KEY,
            )

            structured_llm = llm.with_structured_output(
                schema,
                method="json_schema",
            )

            self._chains[format_type] = prompt | structured_llm

    def get_chain_for_format(
        self,
        format_type: str,
        attempt: int = 1,
    ):
        """
        Get the LLM chain for a specific format with retry temperature adjustment.

        Args:
            format_type: REEL, CAROUSEL, or QUOTE
            attempt: Retry attempt number (1, 2, or 3)

        Returns:
            The appropriate prompt | structured_llm chain
        """
        format_upper = format_type.upper()

        # For retries, rebuild chain with adjusted temperature
        if attempt > 1:
            temperature = creation_temperatures.get_stage3_temperature(
                format_upper,
                attempt=attempt,
            )

            prompt, schema = {
                "REEL": (STAGE3_REEL_PROMPT, ReelContent),
                "CAROUSEL": (STAGE3_CAROUSEL_PROMPT, CarouselContent),
                "QUOTE": (STAGE3_QUOTE_PROMPT, QuoteContent),
            }[format_upper]

            llm = ChatOpenAI(
                model=self.model,
                temperature=temperature,
                api_key=settings.OPENAI_API_KEY,
            )

            structured_llm = llm.with_structured_output(
                schema,
                method="json_schema",
            )

            return prompt | structured_llm

        return self._chains.get(format_upper)

    def _build_rewrite_context(self, context: GenerationContext) -> str:
        """
        Build rewrite context block for Stage 4 retry injections.

        Returns empty string for first attempt, critique feedback for retries.
        """
        if context.attempt_number <= 1:
            return ""

        lines = [
            f"## REWRITE CONTEXT",
            f"",
            f"This is attempt #{context.attempt_number}. Previous attempt failed critique.",
            f"",
        ]

        if context.rewrite_focus:
            lines.append(f"**Rewrite Focus**: {context.rewrite_focus}")
            lines.append("")

        if context.specific_failures:
            lines.append("**Specific Failures**:")
            for failure in context.specific_failures:
                lines.append(f"- **{failure.criterion}**: {failure.issue}")
                lines.append(f"  - Fix: {failure.fix}")
            lines.append("")

        if context.ai_voice_violations:
            lines.append("**AI Voice Violations Detected**:")
            for violation in context.ai_voice_violations:
                lines.append(f"- {violation}")
            lines.append("")
            lines.append("You MUST eliminate these violations in this attempt.")
            lines.append("")

        lines.append("Address these issues while maintaining mode fidelity and emotional targeting.")

        return "\n".join(lines)

    async def generate(
        self,
        context: GenerationContext,
        attempt: int = 1,
        skeleton_json: Optional[str] = None,
    ) -> Stage3Result:
        """
        Generate content for the given GenerationContext.

        Args:
            context: GenerationContext from Stage 2
            attempt: Retry attempt number for temperature adjustment
            skeleton_json: JSON string of skeleton from Stage 2.5 (optional)

        Returns:
            Stage3Result with format-specific content
        """
        format_type = context.required_format.upper()

        result = Stage3Result(
            schedule_id=context.schedule_id,
            trace_id=context.trace_id,
            format_type=format_type,
        )

        chain = self.get_chain_for_format(format_type, attempt=attempt)
        if not chain:
            result.error = f"Unknown format type: {format_type}"
            logger.error("[CREATION:S3] unknown_format format=%s", format_type)
            return result

        # Build reframe note if needed
        reframe_note = ""
        if context.requires_heavy_reframe and context.suggested_reframe:
            reframe_note = (
                f"**Note**: The raw material needs heavy reframing. "
                f"Use the suggested reframe:\n{context.suggested_reframe}"
            )

        # Build prompt input with mode sequence and emotional arc
        prompt_input = {
            # Mode sequence fields
            "resolved_mode": context.resolved_mode,
            "tone_shift_instruction": context.tone_shift_instruction or "N/A",
            "opener_mode": context.mode_sequence.opener.mode,
            "opener_energy": context.mode_sequence.opener.energy,
            "opener_function": context.mode_sequence.opener.function,
            "bridge_mode": context.mode_sequence.bridge.mode,
            "bridge_energy": context.mode_sequence.bridge.energy,
            "bridge_function": context.mode_sequence.bridge.function,
            "closer_mode": context.mode_sequence.closer.mode,
            "closer_energy": context.mode_sequence.closer.energy,
            "closer_function": context.mode_sequence.closer.function,
            # Emotional arc fields
            "entry_state": context.emotional_arc.entry_state,
            "destabilization_trigger": context.emotional_arc.destabilization_trigger,
            "resistance_point": context.emotional_arc.resistance_point,
            "breakthrough_moment": context.emotional_arc.breakthrough_moment,
            "landing_state": context.emotional_arc.landing_state,
            "pacing_note": context.emotional_arc.pacing_note,
            # Engagement triggers
            "physical_response_goal": context.physical_response_goal,
            "share_trigger": context.share_trigger,
            "share_target": context.share_target,
            "save_trigger": context.share_trigger,  # Use share_trigger as fallback
            # Content context
            "counter_truth": context.counter_truth,
            "core_truth": context.core_truth,
            "contrast_pair": context.contrast_pair,
            "strongest_hook": context.strongest_hook,
            "primary_emotion": context.primary_emotion,
            "required_pillar": context.required_pillar,
            "reframe_note": reframe_note,
            "rewrite_context": self._build_rewrite_context(context),
            "brief": json.dumps(context.brief, indent=2, default=str),
            # Skeleton from Stage 2.5
            "skeleton_json": skeleton_json or "Not provided",
        }

        logger.debug(
            "[CREATION:S3] generating format=%s mode=%s attempt=%d",
            format_type,
            context.resolved_mode,
            attempt,
        )

        try:
            content = await chain.ainvoke(prompt_input)

            # Assign to appropriate field based on format
            if format_type == "REEL":
                result.reel_content = content
            elif format_type == "CAROUSEL":
                result.carousel_content = content
            elif format_type == "QUOTE":
                result.quote_content = content

            logger.debug(
                "[CREATION:S3] complete format=%s trace_id=%s",
                format_type,
                context.trace_id,
            )

        except Exception as e:
            result.error = str(e)
            logger.error(
                "[CREATION:S3] failed format=%s trace_id=%s error=%s",
                format_type,
                context.trace_id,
                str(e)[:100],
            )

        return result
