"""
Ingestion API Schemas.

Request/response schemas for Phase 1 ingestion endpoints.
These are STABLE API contracts - do NOT import SQLModel database models.
"""

import uuid
from datetime import datetime
from typing import Optional, Any, Dict, List, Literal

from pydantic import BaseModel, Field

from app.db.enums import SourceType, IngestStatus


class RawIngestItem(BaseModel):
    """Schema for a single raw ingest record."""

    id: uuid.UUID = Field(description="Unique identifier for the ingest record")
    trace_id: uuid.UUID = Field(description="Trace ID for debugging")
    source_type: SourceType = Field(description="Type of content source")
    source_url: Optional[str] = Field(description="URL where content was sourced from")
    source_identifier: Optional[str] = Field(
        description="Unique identifier from source platform"
    )
    raw_content: str = Field(description="Raw content text")
    raw_title: Optional[str] = Field(description="Title of the content if available")
    raw_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata from source"
    )
    status: IngestStatus = Field(description="Current processing status")
    batch_id: Optional[uuid.UUID] = Field(
        description="Batch ID from harvester if applicable"
    )
    ingested_at: datetime = Field(description="Timestamp when content was ingested")
    processed_at: Optional[datetime] = Field(
        description="Timestamp when content was processed"
    )
    content_hash: Optional[str] = Field(description="MD5 hash for deduplication")

    class Config:
        from_attributes = True


class PendingIngestResponse(BaseModel):
    """API response for pending/processing ingest records."""

    request_id: str = Field(description="Unique request identifier for tracing")
    total_count: int = Field(ge=0, description="Total number of records returned")
    records: List[RawIngestItem] = Field(
        default_factory=list, description="List of pending/processing ingest records"
    )


class HarvestResponse(BaseModel):
    """API response for harvest operations."""

    batch_id: str = Field(description="Unique identifier for this harvest batch")
    posts_fetched: int = Field(ge=0, description="Total posts retrieved from source")
    posts_stored: int = Field(ge=0, description="Posts successfully stored in database")
    posts_skipped: int = Field(ge=0, description="Posts filtered or deduplicated")
    errors: List[str] = Field(default_factory=list, description="Error messages if any")
    duration_seconds: float = Field(ge=0, description="Total operation time in seconds")
    status: Literal["success", "partial", "failed"] = Field(
        description="Overall operation status"
    )

    @classmethod
    def from_result(
        cls,
        posts_fetched: int,
        posts_stored: int,
        posts_skipped: int,
        errors: List[str],
        duration_seconds: float,
        batch_id: str,
    ) -> "HarvestResponse":
        """Create HarvestResponse from individual result metrics."""
        # Determine status based on results
        if errors and posts_stored == 0:
            status = "failed"
        elif errors:
            status = "partial"
        else:
            status = "success"

        return cls(
            batch_id=batch_id,
            posts_fetched=posts_fetched,
            posts_stored=posts_stored,
            posts_skipped=posts_skipped,
            errors=errors,
            duration_seconds=round(duration_seconds, 2),
            status=status,
        )
