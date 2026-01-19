"""
Stage 3.5: Coherence Audit.

Evaluates generated content against its skeleton.
If content fails coherence checks, returns rewrite instructions for Stage 3.
"""

import json
import logging
from typing import Optional, Union

from langchain_openai import ChatOpenAI

from app.config import settings
from app.creation.prompts.stage_3_5_coherence import STAGE3_5_COHERENCE_PROMPT
from app.creation.schemas import (
    CarouselContent,
    CarouselSkeleton,
    CoherenceAuditResult,
    QuoteContent,
    QuoteSkeleton,
    ReelContent,
    ReelSkeleton,
    Stage2_5Result,
    Stage3Result,
    Stage3_5Result,
)
from app.creation.temperature_config import creation_temperatures

logger = logging.getLogger(__name__)

# Type aliases
GeneratedContent = Union[ReelContent, CarouselContent, QuoteContent]
Skeleton = Union[CarouselSkeleton, ReelSkeleton, QuoteSkeleton]


class Stage3_5CoherenceAuditor:
    """
    LLM-based coherence auditor for Stage 3.5.

    Evaluates whether generated content functions as a SEQUENCE
    or merely a COLLECTION of unrelated units.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the Stage 3.5 coherence auditor.

        Args:
            model: LLM model name (defaults to settings.CREATION_LLM_MODEL)
            temperature: LLM temperature (defaults to stage_4_critique temperature)
        """
        self.model = model or settings.CREATION_ANALYTICAL_MODEL
        self.temperature = (
            temperature
            if temperature is not None
            else creation_temperatures.stage_4_critique
        )

        llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=settings.OPENAI_API_KEY,
        )

        self.structured_llm = llm.with_structured_output(
            CoherenceAuditResult,
            method="json_schema",
        )

        self.chain = STAGE3_5_COHERENCE_PROMPT | self.structured_llm

    def _extract_content(self, stage3_result: Stage3Result) -> Optional[GeneratedContent]:
        """Extract the generated content from Stage3Result."""
        if stage3_result.reel_content:
            return stage3_result.reel_content
        elif stage3_result.carousel_content:
            return stage3_result.carousel_content
        elif stage3_result.quote_content:
            return stage3_result.quote_content
        return None

    def _extract_skeleton(self, stage2_5_result: Stage2_5Result) -> Optional[Skeleton]:
        """Extract the skeleton from Stage2_5Result."""
        if stage2_5_result.carousel_skeleton:
            return stage2_5_result.carousel_skeleton
        elif stage2_5_result.reel_skeleton:
            return stage2_5_result.reel_skeleton
        elif stage2_5_result.quote_skeleton:
            return stage2_5_result.quote_skeleton
        return None

    async def audit(
        self,
        stage3_result: Stage3Result,
        stage2_5_result: Stage2_5Result,
    ) -> Stage3_5Result:
        """
        Run coherence audit on generated content against its skeleton.

        Args:
            stage3_result: Result from Stage 3 generation
            stage2_5_result: Result from Stage 2.5 skeleton generation

        Returns:
            Stage3_5Result with audit results
        """
        result = Stage3_5Result(
            schedule_id=stage3_result.schedule_id,
            trace_id=stage3_result.trace_id,
        )

        # Extract content and skeleton
        content = self._extract_content(stage3_result)
        skeleton = self._extract_skeleton(stage2_5_result)

        if not content:
            result.error = "No content found in Stage3Result"
            return result

        if not skeleton:
            result.error = "No skeleton found in Stage2_5Result"
            return result

        # Serialize for prompt
        content_json = json.dumps(content.model_dump(), indent=2, default=str)
        skeleton_json = json.dumps(skeleton.model_dump(), indent=2, default=str)

        prompt_input = {
            "format_type": stage3_result.format_type,
            "skeleton": skeleton_json,
            "generated_content": content_json,
        }

        logger.debug(
            "[CREATION:S3.5] auditing format=%s trace_id=%s",
            stage3_result.format_type,
            stage3_result.trace_id,
        )

        try:
            audit_result: CoherenceAuditResult = await self.chain.ainvoke(prompt_input)
            result.audit_result = audit_result

            logger.debug(
                "[CREATION:S3.5] audit complete score=%d pass=%s trace_id=%s",
                audit_result.sequence_integrity_score,
                audit_result.coherence_pass,
                stage3_result.trace_id,
            )

            if not audit_result.coherence_pass:
                logger.info(
                    "[CREATION:S3.5] coherence_failed score=%d rewrite=%s trace_id=%s",
                    audit_result.sequence_integrity_score,
                    audit_result.rewrite_required,
                    stage3_result.trace_id,
                )

        except Exception as e:
            result.error = str(e)
            logger.error(
                "[CREATION:S3.5] failed trace_id=%s error=%s",
                stage3_result.trace_id,
                str(e)[:100],
            )

        return result

    def needs_rewrite(self, result: Stage3_5Result) -> bool:
        """Check if content needs to return to Stage 3 for rewrite."""
        if result.error:
            return False  # Can't rewrite if audit failed
        if result.audit_result:
            return result.audit_result.rewrite_required
        return False

    def get_rewrite_instruction(self, result: Stage3_5Result) -> Optional[str]:
        """Get the specific rewrite instruction for Stage 3."""
        if result.audit_result and result.audit_result.rewrite_instruction:
            return result.audit_result.rewrite_instruction
        return None
