import uuid
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List, TYPE_CHECKING

from sqlalchemy import (
    Column,
    TIMESTAMP,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlmodel import SQLModel, Field, Relationship

from app.db.enums import Format, GeneratedContentStatus

if TYPE_CHECKING:
    from app.db.db_models.strategy import ContentSchedule


class GeneratedContent(SQLModel, table=True):
    __tablename__ = "generated_content"

    __table_args__ = (
        Index("ix_generated_content_schedule", "schedule_id"),
        Index("ix_generated_content_trace", "trace_id"),
        Index(
            "ix_generated_content_status",
            "status",
            postgresql_where=text("status = 'FLAGGED_FOR_REVIEW'"),
        ),
        Index(
            "ix_generated_content_critique_gin",
            "critique_scores",
            postgresql_using="gin",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    trace_id: uuid.UUID = Field(nullable=False)

    schedule_id: uuid.UUID = Field(
        nullable=False,
        foreign_key="content_schedule.id",
        ondelete="CASCADE",
    )

    format_type: Format = Field(nullable=False)

    content_json: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
        description="The full ReelContent/CarouselContent/QuoteContent JSON",
    )

    generation_context: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
        description="Full GenerationContext for debugging",
    )

    resolved_mode: str = Field(nullable=False)

    emotional_journey: Dict[str, str] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
        description="Three-state emotional journey (state_1, state_2, state_3)",
    )

    critique_scores: Dict[str, int] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
        description="CritiqueScores from Stage 4 evaluation",
    )

    generation_attempts: int = Field(default=1)

    status: GeneratedContentStatus = Field(
        default=GeneratedContentStatus.APPROVED,
        nullable=False,
    )

    flag_reasons: List[str] = Field(
        default_factory=list,
        sa_column=Column(
            ARRAY(Text),
            nullable=False,
            server_default=text("'{}'"),
        ),
    )

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
        ),
    )

    approved_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True)),
    )

    schedule: "ContentSchedule" = Relationship(back_populates="generated_content")
