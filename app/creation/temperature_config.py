# ============================================================================
# PHASE 5 TEMPERATURE CONFIGURATION
# ============================================================================
from pydantic import BaseModel, Field


class Stage3Temperatures(BaseModel):
    """
    Format-specific temperatures for Stage 3 generation.

    Higher temperatures for more creative/punchy output.
    """

    REEL: float = Field(
        default=0.85,
        description="Highest creativity. Needs punch, rhythm, unexpected phrasing.",
    )
    CAROUSEL: float = Field(
        default=0.7,
        description="Structured but needs sharp headlines. Moderate creativity.",
    )
    QUOTE: float = Field(
        default=0.8,
        description="Compression requires creative leaps. One line must carry everything.",
    )

    def get(self, format_type: str) -> float:
        """Get temperature for a format type."""
        return getattr(self, format_type.upper(), 0.75)


class CreationTemperatures(BaseModel):
    """
    LLM Temperature settings for Phase 5 Creation stages.

    Temperature tradeoff:
    - Low (0.2-0.4): Consistent, predictable, analytical (Stages 1, 4)
    - High (0.7-0.9): Variable, surprising, creative (Stage 3)
    """

    # Stage 1: Analyze - Analytical judgment, low variance
    stage_1_analyze: float = Field(
        default=0.3,
        description="Analytical judgment. Consistency in scoring and classification.",
    )

    # Stage 2: Target - Some creativity, but grounded in analysis
    stage_2_target: float = Field(
        default=0.4,
        description="Emotional targeting requires some creativity, but stays grounded.",
    )

    # Stage 3: Generate - Format-specific creative output
    stage_3_generate: Stage3Temperatures = Field(
        default_factory=Stage3Temperatures,
        description="Format-specific temperatures for content generation.",
    )

    # Stage 4: Critique - Evaluation must be consistent and harsh
    stage_4_critique: float = Field(
        default=0.2,
        description="Evaluation must be consistent. Same content = same scores.",
    )

    # Rewrite increment - Added per retry attempt in Stage 3
    rewrite_increment: float = Field(
        default=0.05,
        description="Temperature increase per retry to escape local minimum.",
    )

    def get_stage3_temperature(self, format_type: str, attempt: int = 1) -> float:
        """
        Get Stage 3 temperature for a format with retry adjustment.

        Args:
            format_type: REEL, CAROUSEL, or QUOTE
            attempt: Retry attempt number (1, 2, or 3)

        Returns:
            Adjusted temperature (base + increment per attempt)
        """
        base_temp = self.stage_3_generate.get(format_type)
        increment = (attempt - 1) * self.rewrite_increment
        return min(base_temp + increment, 1.0)  # Cap at 1.0


# Global temperature config instance
creation_temperatures = CreationTemperatures()
