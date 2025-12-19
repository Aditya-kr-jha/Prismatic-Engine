"""
Common API Schemas.

Base schemas for request metadata and response wrappers.
These schemas are used across all API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RequestMetadata(BaseModel):
    """Metadata injected into requests for tracing and debugging."""

    request_id: str = Field(description="Unique request identifier for tracing")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Request timestamp",
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Distributed trace ID if available",
    )


class BaseResponse(BaseModel):
    """Base response schema with common fields."""

    request_id: str = Field(description="Unique request identifier for tracing")
    success: bool = Field(
        default=True,
        description="Whether the request was successful",
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional human-readable message",
    )
