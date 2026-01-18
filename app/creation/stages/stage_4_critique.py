"""
Stage 4: Self-Critique & Rewrite Loop.

Evaluates generated content against 6 performance criteria.
If content fails, injects critique context and triggers Stage 3 rewrite.
Maximum 2 rewrites (3 total attempts).
"""

import json
import logging
from typing import Optional, Union

from langchain_openai import ChatOpenAI

from app.config import settings
from app.creation.prompts.stage_4 import STAGE4_PROMPT
from app.creation.schemas import (
    CarouselContent,
    CritiqueResult,
    GenerationContext,
    QuoteContent,
    ReelContent,
    Stage3Result,
    Stage4Result,
)
from app.creation.temperature_config import creation_temperatures

logger = logging.getLogger(__name__)

# Type alias for generated content
GeneratedContent = Union[ReelContent, CarouselContent, QuoteContent]


class Stage4Critic:
    """
    LLM-based content critic for Stage 4 self-evaluation.

    Evaluates content against 7 performance criteria (revised):
    1. Scroll-stop power
    2. AI voice risk (with uniformity detection)
    3. Share impulse
    4. Emotional precision (arc-based)
    5. Mode progression (replaces mode fidelity)
    6. Pacing & breath
    7. Format execution (psychological flow)

    Pass thresholds are format-aware:
    - All >= 6, AI Voice >= 7 (all formats)
    - Mode Progression >= 6 (Reels/Carousels)
    - Pacing/Breath >= 7 for Reels, >= 6 for Carousels
    - Mode Progression and Pacing N/A for Quotes
    """

    # Pass thresholds
    MIN_SCORE_THRESHOLD = 6
    MIN_AI_VOICE_THRESHOLD = 7
    MIN_PACING_REEL_THRESHOLD = 7

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the Stage 4 critic.

        Args:
            model: LLM model name (defaults to settings.CREATION_LLM_MODEL)
            temperature: LLM temperature (defaults to creation_temperatures.stage_4_critique)
        """
        self.model = model or settings.CREATION_LLM_MODEL
        self.temperature = (
            temperature
            if temperature is not None
            else creation_temperatures.stage_4_critique
        )

        self.llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=settings.OPENAI_API_KEY,
        )

        # Use structured output for deterministic parsing
        self.structured_llm = self.llm.with_structured_output(
            CritiqueResult,
            method="json_schema",
        )

        # Build the chain: prompt -> structured LLM
        self.chain = STAGE4_PROMPT | self.structured_llm

    def _serialize_content(self, content: GeneratedContent) -> str:
        """Serialize content to JSON string for prompt."""
        return json.dumps(content.model_dump(), indent=2, default=str)

    def _extract_content_from_stage3(
        self,
        stage3_result: Stage3Result,
    ) -> Optional[GeneratedContent]:
        """Extract the correct content type from Stage3Result."""
        if stage3_result.reel_content:
            return stage3_result.reel_content
        elif stage3_result.carousel_content:
            return stage3_result.carousel_content
        elif stage3_result.quote_content:
            return stage3_result.quote_content
        return None

    async def critique(
        self,
        content: GeneratedContent,
        context: GenerationContext,
        coherence_audit_summary: str = "Not available",
    ) -> CritiqueResult:
        """
        Run single critique evaluation on content.

        Args:
            content: Generated content (ReelContent, CarouselContent, or QuoteContent)
            context: GenerationContext with emotional targeting
            coherence_audit_summary: Summary from Stage 3.5 coherence audit

        Returns:
            CritiqueResult with scores and pass/fail decision

        Raises:
            Exception: If LLM call fails
        """
        # Build prompt input with mode sequence and emotional arc
        prompt_input = {
            "required_format": context.required_format,
            "required_pillar": context.required_pillar,
            "core_truth": context.core_truth,
            # Mode sequence
            "mode_opener": context.mode_sequence.opener.mode,
            "mode_bridge": context.mode_sequence.bridge.mode,
            "mode_closer": context.mode_sequence.closer.mode,
            # Emotional arc
            "emotional_entry_state": context.emotional_arc.entry_state,
            "destabilization_trigger": context.emotional_arc.destabilization_trigger,
            "resistance_point": context.emotional_arc.resistance_point,
            "breakthrough_moment": context.emotional_arc.breakthrough_moment,
            "landing_state": context.emotional_arc.landing_state,
            "physical_response_goal": context.physical_response_goal,
            "pacing_note": context.emotional_arc.pacing_note,
            # Content and coherence
            "generated_content": self._serialize_content(content),
            "coherence_audit_summary": coherence_audit_summary,
        }

        logger.debug(
            "[CREATION:S4] critiquing format=%s mode_sequence=%s→%s→%s attempt=%d",
            context.required_format,
            context.mode_sequence.opener.mode,
            context.mode_sequence.bridge.mode,
            context.mode_sequence.closer.mode,
            context.attempt_number,
        )

        result: CritiqueResult = await self.chain.ainvoke(prompt_input)

        # Log all 7 scores
        scores = result.scores
        logger.info(
            "[CREATION:S4] scores trace_id=%s scroll=%d ai=%d share=%d emotion=%d mode_prog=%d pacing=%d format=%d pass=%s",
            context.trace_id,
            scores.scroll_stop_power,
            scores.ai_voice_risk,
            scores.share_impulse,
            scores.emotional_precision,
            scores.mode_progression,
            scores.pacing_breath,
            scores.format_execution,
            result.overall_pass,
        )

        return result

    async def run_critique_loop(
        self,
        generator,  # Stage3Generator - avoid circular import
        initial_stage3_result: Stage3Result,
        context: GenerationContext,
        max_attempts: int = 3,
    ) -> Stage4Result:
        """
        Full critique loop with rewrites.

        Process:
        1. Run critique on content
        2. If pass -> return success
        3. If fail and attempts < max -> inject critique, re-run Stage 3
        4. If 3 attempts failed -> flag for human review

        Args:
            generator: Stage3Generator instance
            initial_stage3_result: Initial Stage 3 output
            context: GenerationContext (will be mutated with critique data)
            max_attempts: Maximum generation attempts (default 3)

        Returns:
            Stage4Result with final content and critique outcome
        """
        result = Stage4Result(
            schedule_id=context.schedule_id,
            trace_id=context.trace_id,
        )

        # Extract initial content
        current_content = self._extract_content_from_stage3(initial_stage3_result)
        if not current_content:
            result.error = "No content in Stage 3 result"
            return result

        current_stage3_result = initial_stage3_result
        attempt = 1

        while attempt <= max_attempts:
            try:
                # Run critique
                critique = await self.critique(current_content, context)

                # Check if passed
                if critique.overall_pass:
                    result.final_content = current_content
                    result.final_critique = critique
                    result.attempts_used = attempt
                    result.passed = True
                    logger.info(
                        "[CREATION:S4] passed trace_id=%s attempts=%d",
                        context.trace_id,
                        attempt,
                    )
                    return result

                # Failed - check if we can retry
                if attempt >= max_attempts:
                    # Max attempts reached, flag for human review
                    result.final_content = current_content
                    result.final_critique = critique
                    result.attempts_used = attempt
                    result.passed = False
                    result.flagged_for_review = True
                    logger.warning(
                        "[CREATION:S4] max_attempts trace_id=%s flagged_for_review=True",
                        context.trace_id,
                    )
                    return result

                # Inject critique into context for rewrite
                context.rewrite_focus = critique.rewrite_focus
                context.specific_failures = critique.specific_failures
                context.ai_voice_violations = critique.ai_voice_violations
                context.attempt_number = attempt + 1

                logger.info(
                    "[CREATION:S4] rewrite_required trace_id=%s attempt=%d focus=%s",
                    context.trace_id,
                    attempt,
                    critique.rewrite_focus[:50] if critique.rewrite_focus else "N/A",
                )

                # Re-run Stage 3 with critique context
                current_stage3_result = await generator.generate(
                    context=context,
                    attempt=context.attempt_number,
                )

                if current_stage3_result.error:
                    result.error = f"Stage 3 rewrite failed: {current_stage3_result.error}"
                    result.attempts_used = attempt
                    return result

                current_content = self._extract_content_from_stage3(current_stage3_result)
                if not current_content:
                    result.error = "No content in Stage 3 rewrite result"
                    result.attempts_used = attempt
                    return result

                attempt += 1

            except Exception as e:
                logger.error(
                    "[CREATION:S4] error trace_id=%s attempt=%d error=%s",
                    context.trace_id,
                    attempt,
                    str(e)[:100],
                )
                result.error = str(e)
                result.attempts_used = attempt
                return result

        return result
