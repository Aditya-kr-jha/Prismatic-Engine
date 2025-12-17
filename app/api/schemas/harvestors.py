from typing import Literal

from pydantic import BaseModel, Field

from app.services.schemas import HarvestResult


class HarvestResponse(BaseModel):
    """API response for harvest operations."""

    batch_id: str = Field(description="Unique identifier for this harvest batch")
    posts_fetched: int = Field(ge=0, description="Total posts retrieved from source")
    posts_stored: int = Field(ge=0, description="Posts successfully stored in database")
    posts_skipped: int = Field(ge=0, description="Posts filtered or deduplicated")
    errors: list[str] = Field(default_factory=list, description="Error messages if any")
    duration_seconds: float = Field(ge=0, description="Total operation time in seconds")
    status: Literal["success", "partial", "failed"] = Field(
        description="Overall operation status"
    )

    @classmethod
    def from_result(cls, result: HarvestResult, batch_id: str) -> "HarvestResponse":
        """Convert internal HarvestResult to API response."""
        # Determine status based on results
        if result.errors and result.posts_stored == 0:
            status = "failed"
        elif result.errors:
            status = "partial"
        else:
            status = "success"

        return cls(
            batch_id=str(batch_id),
            posts_fetched=result.posts_fetched,
            posts_stored=result.posts_stored,
            posts_skipped=result.posts_skipped,
            errors=result.errors,
            duration_seconds=round(result.duration_seconds, 2),
            status=status,
        )
