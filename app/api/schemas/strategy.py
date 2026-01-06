"""
Strategy API Schemas.

Request and response schemas for Phase 4 strategy endpoints.
"""

import uuid
from datetime import date, time
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Request Schemas
# ============================================================================


class GenerateScheduleRequest(BaseModel):
    """Request schema for generating a weekly schedule."""

    start_date: date = Field(
        ...,
        description="Monday of the target week (YYYY-MM-DD format)",
    )
    force: bool = Field(
        default=False,
        description="If True, regenerate schedule even if one exists",
    )


# ============================================================================
# Response Schemas
# ============================================================================


class SlotFillResultItem(BaseModel):
    """Result of filling a single slot."""

    slot_number: int
    success: bool
    atom_id: Optional[uuid.UUID] = None
    angle_id: Optional[str] = None
    score: float = 0.0
    fallback_used: bool = False
    error_message: Optional[str] = None


class ScheduleGenerationResponse(BaseModel):
    """Response schema for schedule generation."""

    request_id: str
    trace_id: uuid.UUID
    week_year: int
    week_number: int
    start_date: date
    total_slots: int
    filled_slots: int
    failed_slots: int
    fallback_slots: int
    diversity_score: float
    slot_results: list[SlotFillResultItem]


class ContentScheduleItem(BaseModel):
    """Response schema for a single ContentSchedule."""

    id: uuid.UUID
    trace_id: uuid.UUID
    week_year: int
    week_number: int
    slot_number: int
    scheduled_date: date
    scheduled_time: Optional[time] = None
    day_of_week: str
    required_pillar: str
    required_format: str
    atom_id: Optional[uuid.UUID] = None
    angle_id: Optional[str] = None
    status: str
    brief: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class WeekScheduleResponse(BaseModel):
    """Response schema for getting a week's schedule."""

    request_id: str
    week_year: int
    week_number: int
    total_slots: int
    filled_slots: int
    schedules: list[ContentScheduleItem]


class ScheduleExistsResponse(BaseModel):
    """Response schema for checking if schedule exists."""

    request_id: str
    week_year: int
    week_number: int
    exists: bool
    slot_count: int = 0
