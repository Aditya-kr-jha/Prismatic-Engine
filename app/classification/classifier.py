"""
Content Classifier using LangChain + OpenAI.

Uses structured output for deterministic JSON responses.
"""

import logging
from typing import Optional

from langchain_openai import ChatOpenAI

from app.classification.prompts import CLASSIFICATION_PROMPT
from app.classification.schemas import ClassificationOutput
from app.config import settings

logger = logging.getLogger(__name__)


class ContentClassifier:
    """
    LLM-based content classifier using OpenAI with structured output.

    Uses `with_structured_output(schema, method="json_schema")` for
    deterministic, schema-validated responses.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0,
    ):
        """
        Initialize the classifier.

        Args:
            model: OpenAI model name
            temperature: LLM temperature (0 for deterministic)
        """
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=settings.OPENAI_API_KEY,
        )
        self.structured_llm = self.llm.with_structured_output(
            ClassificationOutput,
            method="json_schema",
        )
        self.chain = CLASSIFICATION_PROMPT | self.structured_llm

    async def classify(
        self,
        content: str,
        source_type: str = "UNKNOWN",
        title: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> ClassificationOutput:
        """
        Classify content and extract atomic components.

        Args:
            content: Raw content text to classify
            source_type: Type of source (REDDIT, BOOK, BLOG, etc.)
            title: Optional content title
            source_url: Optional source URL

        Returns:
            ClassificationOutput with atomic components and classification

        Raises:
            Exception: If LLM call fails or output validation fails
        """
        logger.debug(
            "Classifying content: source_type=%s, title=%s, len=%d",
            source_type,
            title,
            len(content),
        )

        result = await self.chain.ainvoke({
            "content": content,
            "source_type": source_type,
            "title": title or "Untitled",
            "source_url": source_url or "N/A",
        })

        logger.debug(
            "Classification complete: pillar=%s, virality=%.1f, confidence=%.2f",
            result.classification.primary_pillar.value,
            result.virality_estimate,
            result.confidence,
        )

        return result
