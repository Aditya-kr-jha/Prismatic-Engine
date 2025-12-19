"""
Error Schemas.

Structured API error responses for consistent error handling.
"""

from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Standardized error codes for API responses."""

    # Client errors (4xx)
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"

    # Server errors (5xx)
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATABASE_ERROR = "database_error"
    EXTERNAL_API_ERROR = "external_api_error"

    # Ingestion-specific errors
    HARVEST_FAILED = "harvest_failed"
    INGESTION_ERROR = "ingestion_error"


class APIError(BaseModel):
    """Detailed error information."""

    code: ErrorCode = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error context",
    )


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""

    error: str = Field(description="Error code string for backwards compatibility")
    message: str = Field(description="Human-readable error message")
    request_id: str = Field(description="Request ID for tracing")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error context",
    )

    @classmethod
    def from_api_error(
        cls,
        api_error: APIError,
        request_id: str,
    ) -> "ErrorResponse":
        """Create ErrorResponse from an APIError."""
        return cls(
            error=api_error.code.value,
            message=api_error.message,
            request_id=request_id,
            details=api_error.details,
        )
