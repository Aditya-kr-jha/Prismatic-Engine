"""
Stage 1: Extract & Analyze.

Parses content briefs, extracts psychological cores, and judges Instagram readiness.
Uses LangChain with structured output for deterministic JSON responses.
"""

import json
import logging
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI

from app.config import settings
from app.creation.prompts.stage_1 import STAGE1_PROMPT
from app.creation.schemas import Stage1Analysis
from app.creation.temperature_config import creation_temperatures

logger = logging.getLogger(__name__)


class Stage1Analyzer:
    """
    LLM-based content analyzer for Stage 1.

    Uses `with_structured_output(schema, method="json_schema")` for
    deterministic, schema-validated responses.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the Stage 1 analyzer.

        Args:
            model: LLM model name (defaults to settings.CREATION_LLM_MODEL)
            temperature: LLM temperature (defaults to creation_temperatures.stage_1_analyze)
        """
        self.model = model or settings.CREATION_LLM_MODEL
        self.temperature = (
            temperature
            if temperature is not None
            else creation_temperatures.stage_1_analyze
        )

        self.llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=settings.OPENAI_API_KEY,
        )

        # Use structured output with JSON schema method for deterministic parsing
        self.structured_llm = self.llm.with_structured_output(
            Stage1Analysis,
            method="json_schema",
        )

        # Build the chain: prompt -> structured LLM
        self.chain = STAGE1_PROMPT | self.structured_llm

    async def analyze(
        self,
        brief: Dict[str, Any],
        required_pillar: str,
        required_format: str,
    ) -> Stage1Analysis:
        """
        Analyze a content brief and extract psychological core.

        Args:
            brief: The content brief JSON from ContentSchedule
            required_pillar: Content pillar (e.g., "PRODUCTIVITY")
            required_format: Content format (e.g., "REEL")

        Returns:
            Stage1Analysis with extracted core, emotional analysis, and readiness

        Raises:
            Exception: If LLM call fails or output validation fails
        """
        # Convert brief dict to formatted JSON string for the prompt
        brief_json = json.dumps(brief, indent=2, default=str)

        logger.debug(
            "Stage1 analyzing: pillar=%s, format=%s, brief_len=%d",
            required_pillar,
            required_format,
            len(brief_json),
        )

        # Invoke the chain with structured output
        result: Stage1Analysis = await self.chain.ainvoke(
            {
                "brief": brief_json,
                "required_pillar": required_pillar,
                "required_format": required_format,
            }
        )

        logger.debug(
            "Stage1 complete: readiness=%s, quality=%d, reframe=%s",
            result.instagram_readiness,
            result.brief_quality_score,
            result.requires_heavy_reframe,
        )

        return result
