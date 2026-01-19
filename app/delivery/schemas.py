"""
Delivery phase schemas.

Pydantic models for transforming GeneratedContent into delivery briefs.
"""

from datetime import date, time, datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field


class DeliveryStatus(str, Enum):
    """Status of delivery for a content item."""

    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class QualityScoreSummary(BaseModel):
    """
    Condensed quality scores for display.

    7 criteria (synced with creation module's CritiqueScores):
    1. Scroll-stop power
    2. AI voice risk (expanded with uniformity detection)
    3. Share impulse
    4. Emotional precision (arc-based)
    5. Mode progression (replaces mode fidelity)
    6. Pacing & breath
    7. Format execution (revised for psychological flow)
    """

    scroll_stop_power: int = Field(..., ge=1, le=10)
    ai_voice_risk: int = Field(..., ge=1, le=10)
    share_impulse: int = Field(..., ge=1, le=10)
    emotional_precision: int = Field(..., ge=1, le=10)
    mode_progression: int = Field(..., ge=1, le=10)
    pacing_breath: int = Field(..., ge=1, le=10)
    format_execution: int = Field(..., ge=1, le=10)

    @property
    def average(self) -> float:
        """Calculate average score."""
        scores = [
            self.scroll_stop_power,
            self.ai_voice_risk,
            self.share_impulse,
            self.emotional_precision,
            self.mode_progression,
            self.pacing_breath,
            self.format_execution,
        ]
        return sum(scores) / len(scores)

    @property
    def passed_all(self) -> bool:
        """Check if all thresholds passed."""
        return (
            self.scroll_stop_power >= 6
            and self.ai_voice_risk >= 7  # Higher threshold
            and self.share_impulse >= 6
            and self.emotional_precision >= 6
            and self.mode_progression >= 6
            and self.pacing_breath >= 6
            and self.format_execution >= 6
        )


class EmotionalJourneySummary(BaseModel):
    """Three-state emotional journey. DEPRECATED: Use EmotionalArcSummary instead."""

    state_1: str = Field(..., description="Starting emotional state")
    state_2: str = Field(..., description="Middle transformation")
    state_3: str = Field(..., description="Final emotional state")


class EmotionalArcSummary(BaseModel):
    """
    5-stage continuous emotional arc with pacing notes.
    
    Replaces EmotionalJourneySummary for Reels and Carousels.
    Shows destabilization, resistance, and earned breakthrough.
    """

    entry_state: str = Field(..., description="Where they are before")
    destabilization_trigger: str = Field(..., description="Moment of recognition")
    resistance_point: str = Field(..., description="Where they want to dismiss this")
    breakthrough_moment: str = Field(..., description="The reframe they can't unsee")
    landing_state: str = Field(..., description="Implication, not resolution")
    pacing_note: str = Field(default="", description="Timing guidance")


class DeliveryBrief(BaseModel):
    """
    Unified delivery brief for any content format.

    This is the core data structure that transformers produce.
    """

    # === IDENTIFIERS ===
    generated_content_id: str
    schedule_id: str
    trace_id: str

    # === SLOT INFO ===
    slot_number: int = Field(..., ge=1, le=21)
    scheduled_date: date
    scheduled_time: Optional[time]
    day_of_week: str

    # === CONTENT METADATA ===
    format_type: str  # REEL, CAROUSEL, QUOTE
    pillar: str
    resolved_mode: str

    # === QUALITY ===
    quality_scores: QualityScoreSummary
    emotional_arc: Optional[EmotionalArcSummary] = Field(
        default=None,
        description="5-stage emotional arc (for Reels/Carousels)"
    )
    emotional_journey: Optional[EmotionalJourneySummary] = Field(
        default=None,
        description="DEPRECATED: Use emotional_arc instead"
    )
    generation_attempts: int

    # === FORMAT-SPECIFIC CONTENT ===
    content_markdown: str = Field(..., description="The main markdown content")

    # === SOURCE METADATA ===
    atom_id: Optional[str] = None
    angle_id: Optional[str] = None
    angle_name: Optional[str] = None
    generated_at: datetime

    @property
    def filename(self) -> str:
        """Generate filename for this brief."""
        day_abbrev = self.day_of_week[:3].upper()
        time_str = (
            self.scheduled_time.strftime("%I%p").lstrip("0")
            if self.scheduled_time
            else "TBD"
        )
        return f"{self.slot_number:02d}_{day_abbrev}_{self.format_type}_{time_str}.md"


class WeekPackage(BaseModel):
    """Complete delivery package for a week."""

    week_year: int
    week_number: int
    start_date: date
    end_date: date

    briefs: List[DeliveryBrief] = Field(default_factory=list)

    # Stats
    total_items: int = 0
    reels_count: int = 0
    carousels_count: int = 0
    quotes_count: int = 0

    # Quality summary
    avg_quality_score: float = 0.0
    items_needing_attention: int = 0  # ai_voice_risk < 7

    # Delivery tracking
    delivered_count: int = 0
    failed_count: int = 0


class DeliveryResult(BaseModel):
    """Result of running the delivery pipeline."""

    week_year: int
    week_number: int

    # File export
    output_directory: str
    files_created: List[str] = Field(default_factory=list)

    # Telegram delivery
    telegram_enabled: bool = False
    telegram_messages_sent: int = 0
    telegram_errors: List[str] = Field(default_factory=list)

    # Status
    total_processed: int = 0
    successful: int = 0
    failed: int = 0

    # Timing
    duration_seconds: float = 0.0
