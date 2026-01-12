import uuid
from datetime import datetime, timezone, date, time
from typing import Optional, Any, Dict, List, TYPE_CHECKING

from sqlalchemy import (
    Column,
    TIMESTAMP,
    Index,
    CheckConstraint,
    Text,
    func,
    text,
    UniqueConstraint,
    Date,
    Time,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlmodel import SQLModel, Field, Relationship

from app.db.enums import ContentPillar, Format, ScheduleStatus, PostingStatus

if TYPE_CHECKING:
    from app.db.db_models.classification import ContentAtom
    from app.db.db_models.creation import GeneratedContent


# ═══════════════════════════════════════════════════════════════════════════════
# ANGLE MATRIX
# ═══════════════════════════════════════════════════════════════════════════════


class AngleMatrix(SQLModel, table=True):
    __tablename__ = "angle_matrix"

    __table_args__ = (
        CheckConstraint(
            "virality_multiplier >= 0",
            name="ck_angle_matrix_virality_multiplier",
        ),
        Index(
            "ix_angle_matrix_active",
            "is_active",
            postgresql_where=text("is_active = true"),
        ),
        Index(
            "ix_angle_matrix_pillars_gin",
            "best_for_pillars",
            postgresql_using="gin",
        ),
        Index(
            "ix_angle_matrix_formats_gin",
            "best_for_formats",
            postgresql_using="gin",
        ),
    )

    # ---------- PRIMARY ----------
    id: str = Field(primary_key=True)  # e.g. "contrarian"

    # ---------- META ----------
    name: str = Field(nullable=False)
    template: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)

    # ---------- COMPATIBILITY ----------
    best_for_pillars: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False, server_default=text("'{}'")),
    )

    avoid_for_pillars: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False, server_default=text("'{}'")),
    )

    best_for_formats: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False, server_default=text("'{}'")),
    )

    avoid_for_formats: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False, server_default=text("'{}'")),
    )

    constraints: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )

    # ---------- PERFORMANCE ----------
    virality_multiplier: float = Field(default=1.0)
    performance_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )

    # ---------- STATUS ----------
    is_active: bool = Field(default=True)

    # ---------- DOCS ----------
    example_content: Optional[str] = Field(default=None)
    internal_notes: Optional[str] = Field(default=None)

    # ---------- TIMESTAMPS ----------
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )

    # ---------- RELATIONSHIPS ----------
    schedules: List["ContentSchedule"] = Relationship(back_populates="angle")
    usage_histories: List["UsageHistory"] = Relationship(back_populates="angle")


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT SCHEDULE
# ═══════════════════════════════════════════════════════════════════════════════


class ContentSchedule(SQLModel, table=True):
    __tablename__ = "content_schedule"

    __table_args__ = (
        # ---------- CONSTRAINTS ----------
        CheckConstraint(
            "week_number BETWEEN 1 AND 53",
            name="ck_schedule_week_number",
        ),
        CheckConstraint(
            "slot_number BETWEEN 1 AND 21",
            name="ck_schedule_slot_number",
        ),
        UniqueConstraint(
            "week_year",
            "week_number",
            "slot_number",
            name="uq_schedule_slot",
        ),
        # ---------- INDEXES ----------
        Index("ix_schedule_week", "week_year", "week_number"),
        Index("ix_schedule_date", "scheduled_date"),
        Index(
            "ix_schedule_status_active",
            "status",
            postgresql_where=text("status NOT IN ('PUBLISHED', 'SKIPPED')"),
        ),
        Index("ix_schedule_trace", "trace_id"),
        Index(
            "ix_schedule_atom",
            "atom_id",
            postgresql_where=text("atom_id IS NOT NULL"),
        ),
    )

    # ---------- PRIMARY ----------
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    trace_id: uuid.UUID = Field(default_factory=uuid.uuid4, nullable=False)

    # ---------- SLOT (21 posts/week grid) ----------
    week_year: int = Field(nullable=False)
    week_number: int = Field(nullable=False)
    slot_number: int = Field(nullable=False)

    scheduled_date: date = Field(
        sa_column=Column(Date, nullable=False),
    )
    scheduled_time: Optional[time] = Field(
        default=None,
        sa_column=Column(Time),
    )
    day_of_week: str = Field(nullable=False)

    # ---------- ASSIGNMENT (Phase 3 models) ----------
    atom_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="content_atoms.id",
        ondelete="SET NULL",
    )

    angle_id: Optional[str] = Field(
        default=None,
        foreign_key="angle_matrix.id",
        ondelete="SET NULL",
    )

    # ---------- REQUIREMENTS ----------
    required_pillar: ContentPillar = Field(nullable=False)
    required_format: Format = Field(nullable=False)

    # ---------- BRIEF ----------
    brief: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )

    # ---------- STATE ----------
    status: ScheduleStatus = Field(default=ScheduleStatus.SCHEDULED)

    # ---------- TIMESTAMPS ----------
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )

    # ---------- RELATIONSHIPS (Phase 3 only) ----------
    atom: Optional["ContentAtom"] = Relationship(back_populates="content_schedules")
    angle: Optional["AngleMatrix"] = Relationship(back_populates="schedules")
    usage_histories: List["UsageHistory"] = Relationship(back_populates="schedule")
    generated_content: Optional["GeneratedContent"] = Relationship(back_populates="schedule")


# ═══════════════════════════════════════════════════════════════════════════════
# USAGE HISTORY (Phase 4 Version)
# Tracks what content was scheduled/used and its performance
# ═══════════════════════════════════════════════════════════════════════════════


class UsageHistory(SQLModel, table=True):
    __tablename__ = "usage_history"

    __table_args__ = (
        # ---------- INDEXES ----------
        # Lineage tracking
        Index("ix_usage_trace", "trace_id"),
        # Anti-repetition queries (Phase 4 critical)
        Index("ix_usage_atom_date", "atom_id", text("scheduled_date DESC")),
        Index("ix_usage_atom_angle", "atom_id", "angle_id"),
        # Schedule lookup
        Index("ix_usage_scheduled_date", text("scheduled_date DESC")),
        Index("ix_usage_week", "week_year", "week_number"),
        # Status filtering
        Index("ix_usage_status", "posting_status"),
        # Analytics queries
        Index("ix_usage_pillar_format", "pillar", "format"),
        Index(
            "ix_usage_posted_at",
            text("actual_posted_at DESC"),
            postgresql_where=text("actual_posted_at IS NOT NULL"),
        ),
        # Performance analysis (for learning loop)
        Index(
            "ix_usage_metrics",
            "metrics",
            postgresql_using="gin",
        ),
        # Partial index for engagement analysis
        Index(
            "ix_usage_performance",
            "pillar",
            "format",
            postgresql_where=text(
                "posting_status = 'POSTED' AND metrics->>'engagement_rate' IS NOT NULL"
            ),
        ),
    )

    # ---------- PRIMARY ----------
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    trace_id: uuid.UUID = Field(nullable=False)  # Full lineage back to raw_ingest

    # ---------- CONTENT REFERENCES (Phase 4 scope) ----------
    schedule_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="content_schedule.id",
        ondelete="SET NULL",
    )

    atom_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="content_atoms.id",
        ondelete="SET NULL",
    )

    angle_id: Optional[str] = Field(
        default=None,
        foreign_key="angle_matrix.id",
        ondelete="SET NULL",
    )

    # Future Phase references (no FK constraint yet)
    draft_id: Optional[uuid.UUID] = Field(default=None)  # Phase 5: content_drafts
    asset_id: Optional[uuid.UUID] = Field(default=None)  # Phase 7: production_assets

    # ---------- CONTENT CLASSIFICATION (Denormalized for fast analytics) ----------
    pillar: str = Field(nullable=False)  # e.g., 'PRODUCTIVITY'
    format: str = Field(nullable=False)  # e.g., 'REEL'

    # ---------- SCHEDULE INFO (Denormalized from content_schedule) ----------
    scheduled_date: date = Field(
        sa_column=Column(Date, nullable=False),
    )
    scheduled_time: Optional[time] = Field(
        default=None,
        sa_column=Column(Time),
    )
    day_of_week: Optional[str] = Field(default=None)
    week_year: int = Field(nullable=False)
    week_number: int = Field(nullable=False)

    # ---------- POSTING STATUS ----------
    posting_status: PostingStatus = Field(default=PostingStatus.GENERATED)

    # ---------- INSTAGRAM DATA (Populated after posting) ----------
    instagram_post_id: Optional[str] = Field(default=None)
    instagram_post_url: Optional[str] = Field(default=None)
    actual_posted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True)),
    )

    # ---------- CONTENT SNAPSHOT (What was actually posted) ----------
    content_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )

    # ---------- PERFORMANCE METRICS (Updated by learning loop) ----------
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )

    # ---------- SENTIMENT ANALYSIS (Future enhancement) ----------
    sentiment_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )

    # ---------- CONTENT FINGERPRINT (For similarity/anti-repetition) ----------
    content_fingerprint: Optional[str] = Field(default=None)

    # ---------- TIMESTAMPS ----------
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            TIMESTAMP(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )

    # ---------- RELATIONSHIPS (Phase 3/4 only) ----------
    schedule: Optional["ContentSchedule"] = Relationship(back_populates="usage_histories")
    atom: Optional["ContentAtom"] = Relationship(back_populates="usage_histories")
    angle: Optional["AngleMatrix"] = Relationship(back_populates="usage_histories")
