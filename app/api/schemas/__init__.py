"""
API Schemas.

Pydantic schemas for API request/response contracts.
These are STABLE contracts and must NOT import SQLModel database models directly.
"""

from app.api.schemas.common import BaseResponse, RequestMetadata
from app.api.schemas.creation import (
    ContentScheduleBriefResponse,
    GeneratedContentDetailResponse,
    GeneratedContentItem,
    GeneratedContentListResponse,
    PendingScheduleCountResponse,
    PipelineResultResponse,
    RunPipelineRequest,
    SingleItemResultItem,
)
from app.api.schemas.errors import APIError, ErrorCode, ErrorResponse
from app.api.schemas.ingestion import (
    HarvestResponse,
    PendingIngestResponse,
    RawIngestItem,
)

__all__ = [
    # Common
    "BaseResponse",
    "RequestMetadata",
    # Errors
    "APIError",
    "ErrorCode",
    "ErrorResponse",
    # Ingestion
    "HarvestResponse",
    "PendingIngestResponse",
    "RawIngestItem",
    # Creation
    "ContentScheduleBriefResponse",
    "GeneratedContentDetailResponse",
    "GeneratedContentItem",
    "GeneratedContentListResponse",
    "PendingScheduleCountResponse",
    "PipelineResultResponse",
    "RunPipelineRequest",
    "SingleItemResultItem",
]

