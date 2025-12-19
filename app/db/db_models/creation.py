# import uuid
# from datetime import datetime, timezone
# from typing import Optional, Any, Dict, List
#
# from sqlalchemy import (
#     Column,
#     TIMESTAMP,
#     Index,
#     UniqueConstraint,
#     func,
#     text,
#     Text,
# )
# from sqlalchemy.dialects.postgresql import JSONB, ARRAY
# from sqlmodel import SQLModel, Field, Relationship
#
# from app.db.enums import (
#     ContentPillar,
#     Format,
#     QAStatus,
#     Tone,
#     SizeCategory,
#     HashtagStatus,
# )
#
#
# # =========================================================
# # CONTENT DRAFT
# # =========================================================
#
#
# class ContentDraft(SQLModel, table=True):
#     __tablename__ = "content_drafts"
#
#     __table_args__ = (
#         Index("ix_drafts_schedule", "schedule_id"),
#         Index("ix_drafts_trace", "trace_id"),
#         Index(
#             "ix_drafts_current",
#             "schedule_id",
#             "is_current",
#             postgresql_where=text("is_current = true"),
#         ),
#         Index(
#             "ix_drafts_qa_status_active",
#             "qa_status",
#             postgresql_where=text("qa_status IN ('pending', 'in_progress')"),
#         ),
#         Index(
#             "ix_drafts_content_gin",
#             "content",
#             postgresql_using="gin",
#         ),
#         Index(
#             "ix_drafts_qa_results_gin",
#             "qa_results",
#             postgresql_using="gin",
#         ),
#     )
#
#     # ---------- PRIMARY ----------
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     trace_id: uuid.UUID = Field(nullable=False)
#
#     schedule_id: uuid.UUID = Field(
#         nullable=False,
#         foreign_key="content_schedule.id",
#         ondelete="CASCADE",
#     )
#
#     # ---------- VERSIONING ----------
#     version: int = Field(default=1, nullable=False)
#     is_current: bool = Field(default=True)
#
#     parent_draft_id: Optional[uuid.UUID] = Field(
#         default=None,
#         foreign_key="content_drafts.id",
#     )
#
#     # ---------- FORMAT ----------
#     format: Format = Field(nullable=False)
#
#     # ---------- CONTENT ----------
#     content: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(JSONB, nullable=False),
#     )
#
#     caption: Optional[Dict[str, Any]] = Field(
#         default=None,
#         sa_column=Column(JSONB),
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
#     generation_metadata: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(
#             JSONB,
#             nullable=False,
#             server_default=text("'{}'::jsonb"),
#         ),
#     )
#
#     # ---------- QA ----------
#     qa_status: QAStatus = Field(default=QAStatus.PENDING)
#
#     qa_results: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(
#             JSONB,
#             nullable=False,
#             server_default=text("'{}'::jsonb"),
#         ),
#     )
#
#     qa_completed_at: Optional[datetime] = Field(
#         default=None,
#         sa_column=Column(TIMESTAMP(timezone=True)),
#     )
#
#     # ---------- REVISION ----------
#     revision_count: int = Field(default=0)
#     revision_feedback: Optional[str] = Field(default=None)
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
#     # ---------- RELATIONSHIPS ----------
#     schedule: "ContentSchedule" = Relationship(back_populates="drafts")
#
#     parent: Optional["ContentDraft"] = Relationship(
#         back_populates="children",
#         sa_relationship_kwargs=dict(remote_side="ContentDraft.id"),
#     )
#
#     children: List["ContentDraft"] = Relationship(back_populates="parent")
#
#     production_assets: List["ProductionAsset"] = Relationship(back_populates="draft")
#
#     usage_histories: List["UsageHistory"] = Relationship(back_populates="draft")
#
#
# # =========================================================
# # CAPTION TEMPLATE
# # =========================================================
#
#
# class CaptionTemplate(SQLModel, table=True):
#     __tablename__ = "caption_templates"
#
#     __table_args__ = (
#         Index(
#             "ix_caption_templates_lookup",
#             "pillar",
#             "format",
#             "tone",
#             postgresql_where=text("is_active = true"),
#         ),
#     )
#
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#
#     # ---------- TARGETING ----------
#     pillar: Optional[ContentPillar] = Field(default=None)
#     format: Optional[Format] = Field(default=None)
#     tone: Optional[Tone] = Field(default=None)
#
#     # ---------- TEMPLATE ----------
#     template_structure: str = Field(nullable=False)
#     example: Optional[str] = Field(default=None)
#
#     # ---------- PERFORMANCE ----------
#     usage_count: int = Field(default=0)
#
#     performance_data: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(
#             JSONB,
#             nullable=False,
#             server_default=text("'{}'::jsonb"),
#         ),
#     )
#
#     # ---------- STATUS ----------
#     is_active: bool = Field(default=True)
#
#     created_at: datetime = Field(
#         default_factory=lambda: datetime.now(timezone.utc),
#         sa_column=Column(
#             TIMESTAMP(timezone=True),
#             nullable=False,
#             server_default=func.now(),
#         ),
#     )
#
#
# # =========================================================
# # HASHTAG POOL
# # =========================================================
#
#
# class HashtagPool(SQLModel, table=True):
#     __tablename__ = "hashtag_pool"
#
#     __table_args__ = (
#         UniqueConstraint(
#             "hashtag",
#             name="uq_hashtag_pool_hashtag",
#         ),
#         Index(
#             "ix_hashtag_lookup",
#             "pillar",
#             "status",
#             "size_category",
#             postgresql_where=text("status IN ('active', 'testing')"),
#         ),
#         Index(
#             "ix_hashtag_last_used_active",
#             "last_used_at",
#             postgresql_where=text("status = 'active'"),
#         ),
#     )
#
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#
#     hashtag: str = Field(nullable=False)
#
#     # ---------- TARGETING ----------
#     pillar: Optional[ContentPillar] = Field(default=None)
#
#     # ---------- CATEGORIZATION ----------
#     size_category: Optional[SizeCategory] = Field(default=None)
#     estimated_post_count: Optional[int] = Field(default=None)
#
#     # ---------- PERFORMANCE ----------
#     avg_reach_boost: float = Field(default=1.0)
#     times_used: int = Field(default=0)
#
#     last_used_at: Optional[datetime] = Field(
#         default=None,
#         sa_column=Column(TIMESTAMP(timezone=True)),
#     )
#
#     performance_data: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(
#             JSONB,
#             nullable=False,
#             server_default=text("'{}'::jsonb"),
#         ),
#     )
#
#     # ---------- STATUS ----------
#     status: HashtagStatus = Field(default=HashtagStatus.ACTIVE)
#     banned_reason: Optional[str] = Field(default=None)
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
