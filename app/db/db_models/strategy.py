from datetime import datetime, timezone
from typing import Optional, Any, Dict, List

from sqlalchemy import (
    Column,
    TIMESTAMP,
    Index,
    CheckConstraint,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlmodel import SQLModel, Field


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


# NOTE: Relationships to ContentSchedule, FutureContentQueue, AnglePerformance,
# and UsageHistory are commented out until those models are implemented.
#
#
# class ContentSchedule(SQLModel, table=True):
#     __tablename__ = "content_schedule"
#
#     __table_args__ = (
#         CheckConstraint(
#             "week_number BETWEEN 1 AND 53",
#             name="ck_schedule_week_number",
#         ),
#         CheckConstraint(
#             "slot_number BETWEEN 1 AND 21",
#             name="ck_schedule_slot_number",
#         ),
#         UniqueConstraint(
#             "week_year",
#             "week_number",
#             "slot_number",
#             name="uq_schedule_slot",
#         ),
#         Index("ix_schedule_week", "week_year", "week_number"),
#         Index("ix_schedule_date", "scheduled_date"),
#         Index(
#             "ix_schedule_status_active",
#             "status",
#             postgresql_where=text("status NOT IN ('published', 'skipped')"),
#         ),
#         Index("ix_schedule_trace", "trace_id"),
#         Index(
#             "ix_schedule_atom",
#             "atom_id",
#             postgresql_where=text("atom_id IS NOT NULL"),
#         ),
#     )
#
#     # ---------- PRIMARY ----------
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     trace_id: uuid.UUID = Field(default_factory=uuid.uuid4, nullable=False)
#
#     # ---------- SLOT ----------
#     week_year: int = Field(nullable=False)
#     week_number: int = Field(nullable=False)
#     slot_number: int = Field(nullable=False)
#
#     scheduled_date: date = Field(nullable=False)
#     scheduled_time: Optional[time] = Field(default=None)
#     day_of_week: str = Field(nullable=False)
#
#     # ---------- ASSIGNMENT ----------
#     atom_id: Optional[uuid.UUID] = Field(
#         default=None,
#         foreign_key="content_atoms.id",
#         ondelete="SET NULL",
#     )
#
#     angle_id: Optional[str] = Field(
#         default=None,
#         foreign_key="angle_matrix.id",
#         ondelete="SET NULL",
#     )
#
#     # ---------- REQUIREMENTS ----------
#     required_pillar: ContentPillar = Field(nullable=False)
#     required_format: Format = Field(nullable=False)
#
#     # ---------- BRIEF ----------
#     brief: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(JSONB, nullable=False),
#     )
#
#     # ---------- STATE ----------
#     status: ScheduleStatus = Field(default=ScheduleStatus.SCHEDULED)
#
#     # ---------- TIMESTAMPS ----------
#     created_at: datetime = Field(
#         default_factory=lambda: datetime.now(timezone.utc),
#         sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
#     )
#
#     updated_at: datetime = Field(
#         default_factory=lambda: datetime.now(timezone.utc),
#         sa_column=Column(
#             TIMESTAMP(timezone=True),
#             server_default=func.now(),
#             onupdate=func.now(),
#         ),
#     )
#
#     # ---------- RELATIONSHIPS ----------
#     atom: Optional["ContentAtom"] = Relationship(back_populates="content_schedules")
#
#     angle: Optional["AngleMatrix"] = Relationship(back_populates="schedules")
#
#     future_queue_items: List["FutureContentQueue"] = Relationship(
#         back_populates="source_schedule"
#     )
#
#     drafts: List["ContentDraft"] = Relationship(back_populates="schedule")
#
#     production_assets: List["ProductionAsset"] = Relationship(back_populates="schedule")
#
#     usage_histories: List["UsageHistory"] = Relationship(back_populates="schedule")
#
#     emergency_content: List["EmergencyContent"] = Relationship(
#         back_populates="used_for_schedule"
#     )
#
#
# class ContentCalendar(SQLModel, table=True):
#     __tablename__ = "content_calendar"
#
#     __table_args__ = (
#         CheckConstraint(
#             "priority BETWEEN 1 AND 5",
#             name="ck_calendar_priority",
#         ),
#         Index("ix_calendar_date", "event_date"),
#         Index("ix_calendar_range", "event_date", "event_end_date"),
#         Index("ix_calendar_priority", "priority", "event_date"),
#         Index(
#             "ix_calendar_pillars_gin",
#             "relevant_pillars",
#             postgresql_using="gin",
#         ),
#     )
#
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#
#     event_name: str = Field(nullable=False)
#     event_date: date = Field(nullable=False)
#     event_end_date: Optional[date] = Field(default=None)
#
#     event_type: EventType = Field(nullable=False)
#     priority: int = Field(default=3)
#
#     relevant_pillars: List[str] = Field(
#         default_factory=list,
#         sa_column=Column(ARRAY(Text), nullable=False, server_default=text("'{}'")),
#     )
#
#     suggested_angles: List[str] = Field(
#         default_factory=list,
#         sa_column=Column(ARRAY(Text), nullable=False, server_default=text("'{}'")),
#     )
#
#     content_guidance: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
#     )
#
#     is_recurring: bool = Field(default=False)
#     recurrence_rule: Optional[str] = Field(default=None)
#
#     is_active: bool = Field(default=True)
#
#     created_at: datetime = Field(
#         default_factory=lambda: datetime.now(timezone.utc),
#         sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
#     )
#
#
# class FutureContentQueue(SQLModel, table=True):
#     __tablename__ = "future_content_queue"
#
#     __table_args__ = (
#         CheckConstraint(
#             "priority_score BETWEEN 0.0 AND 10.0",
#             name="ck_future_queue_priority_score",
#         ),
#         Index(
#             "ix_future_queue_status_priority",
#             "status",
#             text("priority_score DESC"),
#             postgresql_where=text("status = 'queued'"),
#         ),
#         Index(
#             "ix_future_queue_date",
#             "suggested_date",
#             postgresql_where=text("status = 'queued'"),
#         ),
#         Index("ix_future_queue_atom", "atom_id"),
#     )
#
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#
#     # ---------- LINKS ----------
#     atom_id: Optional[uuid.UUID] = Field(
#         default=None,
#         foreign_key="content_atoms.id",
#         ondelete="CASCADE",
#     )
#
#     suggested_angle_id: Optional[str] = Field(
#         default=None,
#         foreign_key="angle_matrix.id",
#         ondelete="SET NULL",
#     )
#
#     source_schedule_id: Optional[uuid.UUID] = Field(
#         default=None,
#         foreign_key="content_schedule.id",
#         ondelete="SET NULL",
#     )
#
#     # ---------- TARGET ----------
#     target_pillar: ContentPillar = Field(nullable=False)
#     target_format: Format = Field(nullable=False)
#
#     suggested_date: Optional[date] = Field(default=None)
#     earliest_date: Optional[date] = Field(default=None)
#
#     # ---------- REMIX ----------
#     remix_type: RemixType = Field(nullable=False)
#     remix_reasoning: Optional[str] = Field(default=None)
#
#     # ---------- PRIORITY ----------
#     priority_score: float = Field(default=5.0)
#
#     # ---------- STATUS ----------
#     status: QueueStatus = Field(default=QueueStatus.QUEUED)
#
#     # ---------- META ----------
#     created_at: datetime = Field(
#         default_factory=lambda: datetime.now(timezone.utc),
#         sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now()),
#     )
#
#     expires_at: Optional[datetime] = Field(
#         default=None,
#         sa_column=Column(TIMESTAMP(timezone=True)),
#     )
#
#     notes: Optional[str] = Field(default=None)
#
#     # ---------- RELATIONSHIPS ----------
#     atom: Optional["ContentAtom"] = Relationship(back_populates="future_queue_items")
#
#     suggested_angle: Optional["AngleMatrix"] = Relationship(
#         back_populates="queue_items"
#     )
#
#     source_schedule: Optional["ContentSchedule"] = Relationship(
#         back_populates="future_queue_items"
#     )
