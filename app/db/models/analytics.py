# import uuid
# from datetime import datetime, timezone
# from typing import Optional, Any, Dict, List
#
# from sqlalchemy import (
#     Column,
#     TIMESTAMP,
#     Index,
#     CheckConstraint,
#     UniqueConstraint,
#     func,
#     text,
#     Text,
# )
# from sqlalchemy.dialects.postgresql import JSONB, ARRAY
# from sqlmodel import SQLModel, Field, Relationship
#
# from app.db.enums import (
#     SystemEventType,
#     SystemPhase,
#     ContentPillar,
#     Format,
#     VerificationStatus,
# )
#
#
# # =========================================================
# # DIVERSITY METRICS
# # =========================================================
#
#
# class DiversityMetrics(SQLModel, table=True):
#     __tablename__ = "diversity_metrics"
#
#     __table_args__ = (
#         CheckConstraint(
#             "week_number BETWEEN 1 AND 53",
#             name="ck_diversity_week_number",
#         ),
#         UniqueConstraint(
#             "week_year",
#             "week_number",
#             name="uq_diversity_week",
#         ),
#         Index(
#             "ix_diversity_week_desc",
#             text("week_year DESC"),
#             text("week_number DESC"),
#         ),
#     )
#
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     week_year: int = Field(nullable=False)
#     week_number: int = Field(nullable=False)
#
#     distributions: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(JSONB, nullable=False),
#     )
#
#     metrics: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(JSONB, nullable=False),
#     )
#
#     calculated_at: datetime = Field(
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
# # SYSTEM HEALTH
# # =========================================================
#
#
# class SystemHealth(SQLModel, table=True):
#     __tablename__ = "system_health"
#
#     __table_args__ = (
#         Index(
#             "ix_health_unresolved",
#             "phase",
#             "event_type",
#             text("created_at DESC"),
#             postgresql_where=text("resolved = false"),
#         ),
#         Index(
#             "ix_health_recent",
#             text("created_at DESC"),
#         ),
#     )
#
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#
#     event_type: SystemEventType = Field(nullable=False)
#     phase: SystemPhase = Field(nullable=False)
#
#     message: str = Field(nullable=False)
#
#     details: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(
#             JSONB,
#             nullable=False,
#             server_default=text("'{}'::jsonb"),
#         ),
#     )
#
#     resolved: bool = Field(default=False)
#
#     resolved_at: Optional[datetime] = Field(
#         default=None,
#         sa_column=Column(TIMESTAMP(timezone=True)),
#     )
#
#     resolution_notes: Optional[str] = Field(default=None)
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
# # CONTENT LINEAGE
# # =========================================================
#
#
# class ContentLineage(SQLModel, table=True):
#     __tablename__ = "content_lineage"
#
#     __table_args__ = (
#         Index("ix_lineage_trace", "trace_id"),
#         Index("ix_lineage_atom", "atom_id"),
#         Index(
#             "ix_lineage_unverified",
#             "verification_status",
#             postgresql_where=text("verification_status != 'verified'"),
#         ),
#     )
#
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     trace_id: uuid.UUID = Field(nullable=False)
#
#     atom_id: Optional[uuid.UUID] = Field(
#         default=None,
#         foreign_key="content_atoms.id",
#         ondelete="CASCADE",
#     )
#
#     usage_id: Optional[uuid.UUID] = Field(
#         default=None,
#         foreign_key="usage_history.id",
#         ondelete="CASCADE",
#     )
#
#     # ---------- CLAIM ----------
#     claim_text: str = Field(nullable=False)
#     source_url: Optional[str] = Field(default=None)
#     source_excerpt: Optional[str] = Field(default=None)
#
#     # ---------- VERIFICATION ----------
#     verification_status: VerificationStatus = Field(
#         default=VerificationStatus.UNVERIFIED
#     )
#
#     verified_at: Optional[datetime] = Field(
#         default=None,
#         sa_column=Column(TIMESTAMP(timezone=True)),
#     )
#
#     verifier_notes: Optional[str] = Field(default=None)
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
#     # ---------- RELATIONSHIPS ----------
#     atom: Optional["ContentAtom"] = Relationship(back_populates="content_lineages")
#
#     usage: Optional["UsageHistory"] = Relationship(back_populates="content_lineages")
#
#
# # =========================================================
# # ANGLE PERFORMANCE
# # =========================================================
#
#
# class AnglePerformance(SQLModel, table=True):
#     __tablename__ = "angle_performance"
#
#     __table_args__ = (
#         UniqueConstraint(
#             "angle_id",
#             "pillar",
#             "format",
#             name="uq_angle_performance",
#         ),
#         Index(
#             "ix_angle_performance_lookup",
#             "angle_id",
#             "pillar",
#             "format",
#         ),
#     )
#
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#
#     angle_id: str = Field(
#         nullable=False,
#         foreign_key="angle_matrix.id",
#         ondelete="CASCADE",
#     )
#
#     pillar: ContentPillar = Field(nullable=False)
#     format: Format = Field(nullable=False)
#
#     times_used: int = Field(default=0)
#
#     metrics: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(
#             JSONB,
#             nullable=False,
#             server_default=text("'{}'::jsonb"),
#         ),
#     )
#
#     last_updated: datetime = Field(
#         default_factory=lambda: datetime.now(timezone.utc),
#         sa_column=Column(
#             TIMESTAMP(timezone=True),
#             nullable=False,
#             server_default=func.now(),
#         ),
#     )
#
#     # ---------- RELATIONSHIP ----------
#     angle: "AngleMatrix" = Relationship(back_populates="performances")
#
#
# # =========================================================
# # HASHTAG PERFORMANCE
# # =========================================================
#
#
# class HashtagPerformance(SQLModel, table=True):
#     __tablename__ = "hashtag_performance"
#
#     __table_args__ = (
#         Index("ix_hashtag_perf_usage", "usage_id"),
#         Index(
#             "ix_hashtag_perf_tags_gin",
#             "hashtags",
#             postgresql_using="gin",
#         ),
#     )
#
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#
#     usage_id: uuid.UUID = Field(
#         nullable=False,
#         foreign_key="usage_history.id",
#         ondelete="CASCADE",
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
#     metrics: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(
#             JSONB,
#             nullable=False,
#             server_default=text("'{}'::jsonb"),
#         ),
#     )
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
#     # ---------- RELATIONSHIP ----------
#     usage: "UsageHistory" = Relationship(back_populates="hashtag_performances")
