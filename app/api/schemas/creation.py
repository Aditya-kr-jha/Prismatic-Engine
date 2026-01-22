"""
Creation API Schemas.

Request and response schemas for Phase 5 creation endpoints.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Request Schemas
# ============================================================================


class RunPipelineRequest(BaseModel):
    """Request schema for running the creation pipeline."""

    week_year: int = Field(
        ...,
        description="Target year (e.g., 2026)",
        ge=2020,
        le=2100,
    )
    week_number: int = Field(
        ...,
        description="ISO week number (1-53)",
        ge=1,
        le=53,
    )
    limit: int = Field(
        default=21,
        description="Maximum items to process (default 21 = full week)",
        ge=1,
        le=100,
    )
    dry_run: bool = Field(
        default=False,
        description="If True, run pipeline without persisting changes",
    )


# ============================================================================
# Response Item Schemas
# ============================================================================


class EmotionalJourneyItem(BaseModel):
    """Serialized emotional journey for API response."""

    state_1: str
    state_2: str
    state_3: str


class CritiqueScoresItem(BaseModel):
    """Serialized critique scores for API response."""

    scroll_stop_power: int
    ai_voice_risk: int
    share_impulse: int
    emotional_precision: int
    mode_fidelity: int
    format_execution: int


class GeneratedContentItem(BaseModel):
    """Response schema for a single GeneratedContent record."""

    id: uuid.UUID
    schedule_id: uuid.UUID
    trace_id: uuid.UUID
    format_type: str
    content_json: Dict[str, Any]
    resolved_mode: str
    emotional_journey: Dict[str, str]
    critique_scores: Dict[str, int]
    generation_attempts: int
    status: str
    flag_reasons: List[str]
    generated_at: datetime

    class Config:
        from_attributes = True


class SingleItemResultItem(BaseModel):
    """Response schema for a single pipeline item result."""

    schedule_id: str
    trace_id: str
    format_type: Optional[str] = None
    stage1_success: bool = False
    stage2_success: bool = False
    stage3_success: bool = False
    stage4_success: bool = False
    stage5_success: bool = False
    is_unsuitable: bool = False
    unsuitable_reason: Optional[str] = None
    error: Optional[str] = None
    error_stage: Optional[str] = None
    generated_content_id: Optional[str] = None


# ============================================================================
# Response Schemas
# ============================================================================


class PipelineResultResponse(BaseModel):
    """Response schema for pipeline execution."""

    request_id: str
    week_year: int
    week_number: int
    total_processed: int
    successful: int
    unsuitable: int
    errors: int
    duration_seconds: float
    generated_content: List[GeneratedContentItem]


class GeneratedContentListResponse(BaseModel):
    """Response schema for listing generated content."""

    request_id: str
    week_year: int
    week_number: int
    total_count: int
    content: List[GeneratedContentItem]


class GeneratedContentDetailResponse(BaseModel):
    """Response schema for a single generated content detail."""

    request_id: str
    content: GeneratedContentItem


class PendingScheduleCountResponse(BaseModel):
    """Response schema for pending schedule count."""

    request_id: str
    week_year: int
    week_number: int
    pending_count: int


class ContentScheduleBriefResponse(BaseModel):
    """Response schema for ContentSchedule brief lookup."""

    request_id: str
    generated_content_id: uuid.UUID
    schedule_id: uuid.UUID
    trace_id: uuid.UUID
    required_pillar: str
    required_format: str
    brief: Dict[str, Any]


class DeleteGeneratedContentResponse(BaseModel):
    """Response schema for deleting generated content."""

    request_id: str
    content_id: uuid.UUID
    deleted: bool
    message: str
