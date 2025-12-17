# import uuid
# from datetime import datetime, date, time, timezone
# from typing import Optional, Any, Dict, List
#
# from sqlalchemy import (
#     Column,
#     TIMESTAMP,
#     Index,
#     BigInteger,
#     func,
#     text,
#     Text,
# )
# from sqlalchemy.dialects.postgresql import JSONB, ARRAY
# from sqlmodel import SQLModel, Field, Relationship
#
# from app.db.enums import (
#     Format,
#     AssetType,
#     ProductionStatus,
#     PostingStatus,
#     ContentPillar,
#     EmergencyStatus,
# )
#
#
# # =========================================================
# # PRODUCTION ASSET
# # =========================================================
#
#
# class ProductionAsset(SQLModel, table=True):
#     __tablename__ = "production_assets"
#
#     __table_args__ = (
#         Index("ix_assets_schedule", "schedule_id"),
#         Index("ix_assets_trace", "trace_id"),
#         Index(
#             "ix_assets_status_active",
#             "status",
#             postgresql_where=text("status IN ('rendering', 'ready')"),
#         ),
#     )
#
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     trace_id: uuid.UUID = Field(nullable=False)
#
#     schedule_id: uuid.UUID = Field(
#         nullable=False,
#         foreign_key="content_schedule.id",
#         ondelete="CASCADE",
#     )
#
#     draft_id: uuid.UUID = Field(
#         nullable=False,
#         foreign_key="content_drafts.id",
#         ondelete="CASCADE",
#     )
#
#     # ---------- ASSET INFO ----------
#     format: Format = Field(nullable=False)
#     asset_type: AssetType = Field(nullable=False)
#
#     # ---------- FILE ----------
#     file_path: str = Field(nullable=False)
#     file_url: Optional[str] = Field(default=None)
#
#     file_size_bytes: Optional[int] = Field(
#         default=None,
#         sa_column=Column(BigInteger),
#     )
#
#     file_hash: Optional[str] = Field(default=None)
#
#     # ---------- METADATA ----------
#     asset_metadata: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(
#             JSONB,
#             nullable=False,
#             server_default=text("'{}'::jsonb"),
#         ),
#     )
#
#     production_metadata: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(
#             JSONB,
#             nullable=False,
#             server_default=text("'{}'::jsonb"),
#         ),
#     )
#
#     # ---------- STATUS ----------
#     status: ProductionStatus = Field(default=ProductionStatus.RENDERING)
#
#     error_details: Optional[Dict[str, Any]] = Field(
#         default=None,
#         sa_column=Column(JSONB),
#     )
#
#     # ---------- TIMESTAMPS ----------
#     created_at: datetime = Field(
#         default_factory=lambda: datetime.now(timezone.utc),
#         sa_column=Column(
#             TIMESTAMP(timezone=True),
#             nullable=False,
#             server_default=func.now(),
#         ),
#     )
#
#     delivered_at: Optional[datetime] = Field(
#         default=None,
#         sa_column=Column(TIMESTAMP(timezone=True)),
#     )
#
#     # ---------- RELATIONSHIPS ----------
#     schedule: "ContentSchedule" = Relationship(back_populates="production_assets")
#
#     draft: "ContentDraft" = Relationship(back_populates="production_assets")
#
#     usage_histories: List["UsageHistory"] = Relationship(back_populates="asset")
#
#
# # =========================================================
# # USAGE HISTORY
# # =========================================================
#
#
# class UsageHistory(SQLModel, table=True):
#     __tablename__ = "usage_history"
#
#     __table_args__ = (
#         Index("ix_usage_trace", "trace_id"),
#         Index(
#             "ix_usage_scheduled_date_desc",
#             text("scheduled_date DESC"),
#         ),
#         Index(
#             "ix_usage_posted_at_desc",
#             text("actual_posted_at DESC"),
#             postgresql_where=text("actual_posted_at IS NOT NULL"),
#         ),
#         Index("ix_usage_status", "posting_status"),
#         Index("ix_usage_atom", "atom_id"),
#         Index("ix_usage_pillar_format", "pillar", "format"),
#         Index("ix_usage_week", "week_year", "week_number"),
#         Index(
#             "ix_usage_metrics_gin",
#             "metrics",
#             postgresql_using="gin",
#         ),
#     )
#
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     trace_id: uuid.UUID = Field(nullable=False)
#
#     # ---------- REFERENCES ----------
#     schedule_id: Optional[uuid.UUID] = Field(
#         default=None,
#         foreign_key="content_schedule.id",
#         ondelete="SET NULL",
#     )
#
#     draft_id: Optional[uuid.UUID] = Field(
#         default=None,
#         foreign_key="content_drafts.id",
#         ondelete="SET NULL",
#     )
#
#     asset_id: Optional[uuid.UUID] = Field(
#         default=None,
#         foreign_key="production_assets.id",
#         ondelete="SET NULL",
#     )
#
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
#     # ---------- CLASSIFICATION ----------
#     pillar: ContentPillar = Field(nullable=False)
#     format: Format = Field(nullable=False)
#
#     # ---------- SCHEDULE ----------
#     scheduled_date: date = Field(nullable=False)
#     scheduled_time: Optional[time] = Field(default=None)
#     day_of_week: Optional[str] = Field(default=None)
#
#     week_year: Optional[int] = Field(default=None)
#     week_number: Optional[int] = Field(default=None)
#
#     # ---------- POSTING ----------
#     posting_status: PostingStatus = Field(default=PostingStatus.GENERATED)
#
#     instagram_post_id: Optional[str] = Field(default=None)
#     instagram_post_url: Optional[str] = Field(default=None)
#
#     actual_posted_at: Optional[datetime] = Field(
#         default=None,
#         sa_column=Column(TIMESTAMP(timezone=True)),
#     )
#
#     # ---------- SNAPSHOT ----------
#     content_snapshot: Optional[Dict[str, Any]] = Field(
#         default=None,
#         sa_column=Column(JSONB),
#     )
#
#     # ---------- METRICS ----------
#     metrics: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(
#             JSONB,
#             nullable=False,
#             server_default=text("'{}'::jsonb"),
#         ),
#     )
#
#     sentiment_data: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(
#             JSONB,
#             nullable=False,
#             server_default=text("'{}'::jsonb"),
#         ),
#     )
#
#     content_fingerprint: Optional[str] = Field(default=None)
#
#     # ---------- TIMESTAMPS ----------
#     created_at: datetime = Field(
#         default_factory=lambda: datetime.now(timezone.utc),
#         sa_column=Column(
#             TIMESTAMP(timezone=True),
#             nullable=False,
#             server_default=func.now(),
#         ),
#     )
#
#     updated_at: datetime = Field(
#         default_factory=lambda: datetime.now(timezone.utc),
#         sa_column=Column(
#             TIMESTAMP(timezone=True),
#             nullable=False,
#             server_default=func.now(),
#             onupdate=func.now(),
#         ),
#     )
#
#     # ---------- RELATIONSHIPS ----------
#     schedule: Optional["ContentSchedule"] = Relationship(
#         back_populates="usage_histories"
#     )
#
#     draft: Optional["ContentDraft"] = Relationship(back_populates="usage_histories")
#
#     asset: Optional["ProductionAsset"] = Relationship(back_populates="usage_histories")
#
#     atom: Optional["ContentAtom"] = Relationship(back_populates="usage_histories")
#     content_lineages: Optional[List["ContentLineage"]] = Relationship(
#         back_populates="usage"
#     )
#
#     hashtag_performances: List["HashtagPerformance"] = Relationship(
#         back_populates="usage"
#     )
#
#     angle: Optional["AngleMatrix"] = Relationship(back_populates="usage_histories")
#
#
# # =========================================================
# # EMERGENCY CONTENT
# # =========================================================
#
#
# class EmergencyContent(SQLModel, table=True):
#     __tablename__ = "emergency_content"
#
#     __table_args__ = (
#         Index(
#             "ix_emergency_available",
#             "pillar",
#             "format",
#             postgresql_where=text("status = 'available'"),
#         ),
#     )
#
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#
#     # ---------- TARGET ----------
#     pillar: ContentPillar = Field(nullable=False)
#     format: Format = Field(nullable=False)
#
#     # ---------- CONTENT ----------
#     content: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(JSONB, nullable=False),
#     )
#
#     caption: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(JSONB, nullable=False),
#     )
#
#     hashtags: List[str] = Field(
#         default_factory=list,
#         sa_column=Column(
#             ARRAY(Text),
#             nullable=False,
#             server_default=text("'{}'"),
#         ),
#     )
#
#     # ---------- ASSETS ----------
#     asset_path: Optional[str] = Field(default=None)
#     asset_url: Optional[str] = Field(default=None)
#
#     # ---------- STATUS ----------
#     status: EmergencyStatus = Field(default=EmergencyStatus.AVAILABLE)
#
#     used_at: Optional[datetime] = Field(
#         default=None,
#         sa_column=Column(TIMESTAMP(timezone=True)),
#     )
#
#     used_for_schedule_id: Optional[uuid.UUID] = Field(
#         default=None,
#         foreign_key="content_schedule.id",
#         ondelete="SET NULL",
#     )
#
#     # ---------- META ----------
#     created_at: datetime = Field(
#         default_factory=lambda: datetime.now(timezone.utc),
#         sa_column=Column(
#             TIMESTAMP(timezone=True),
#             nullable=False,
#             server_default=func.now(),
#         ),
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
#     used_for_schedule: Optional["ContentSchedule"] = Relationship(
#         back_populates="emergency_content"
#     )
