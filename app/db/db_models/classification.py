import uuid
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    TIMESTAMP,
    Index,
    UniqueConstraint,
    CheckConstraint,
    func,
    text,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlmodel import SQLModel, Field, Relationship

from app.db.enums import (
    SourceType,
    SourceCredibility,
    ContentPillar,
    LifecycleState,
    VerificationStatus,
)


class ContentAtom(SQLModel, table=True):
    __tablename__ = "content_atoms"

    __table_args__ = (
        # ---------- DATA INTEGRITY ----------
        UniqueConstraint(
            "trace_id",
            name="uq_content_atoms_trace_id",
        ),
        CheckConstraint(
            "complexity_score BETWEEN 1 AND 5",
            name="ck_content_atoms_complexity_score",
        ),
        CheckConstraint(
            "virality_score BETWEEN 0 AND 10",
            name="ck_content_atoms_virality_score",
        ),
        # ---------- PARTIAL / PERFORMANCE INDEXES ----------
        Index(
            "ix_atoms_pillar_active",
            "primary_pillar",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_atoms_lifecycle_active",
            "lifecycle_state",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_atoms_virality_active_desc",
            text("virality_score DESC"),
            postgresql_where=text("lifecycle_state = 'ACTIVE' AND deleted_at IS NULL"),
        ),
        Index(
            "ix_atoms_last_used_active",
            "last_used_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_atoms_trace", "trace_id"),
        # ---------- JSONB / ARRAY INDEXES ----------
        Index(
            "ix_atoms_format_fit_gin",
            "format_fit",
            postgresql_using="gin",
        ),
        Index(
            "ix_atoms_secondary_pillars_gin",
            "secondary_pillars",
            postgresql_using="gin",
        ),
        Index(
            "ix_atoms_classification_gin",
            "classification",
            postgresql_using="gin",
        ),
        Index(
            "ix_atoms_atomic_components_gin",
            "atomic_components",
            postgresql_using="gin",
        ),
        # ---------- COMPOSITE HOT PATH ----------
        Index(
            "ix_atoms_active_pillar_virality",
            "primary_pillar",
            text("virality_score DESC"),
            postgresql_where=text("lifecycle_state = 'ACTIVE' AND deleted_at IS NULL"),
        ),
    )

    # ---------- PRIMARY ----------
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    trace_id: uuid.UUID = Field(nullable=False)

    raw_ingest_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="raw_ingest.id",
        ondelete="SET NULL",
    )

    # ---------- RAW SOURCE ----------
    raw_content: str = Field(nullable=False)
    source_url: Optional[str] = Field(default=None)

    source_type: Optional[SourceType] = Field(default=None)
    source_credibility: SourceCredibility = Field(default=SourceCredibility.MEDIUM)

    source_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(
            JSONB,
            nullable=False,
            server_default=text("'{}'::jsonb"),
        ),
    )

    # ---------- CLASSIFICATION ----------
    primary_pillar: ContentPillar = Field(nullable=False)

    secondary_pillars: List[str] = Field(
        default_factory=list,
        sa_column=Column(
            ARRAY(Text),
            nullable=False,
            server_default=text("'{}'"),
        ),
    )

    format_fit: List[str] = Field(
        default_factory=lambda: ["QUOTE"],
        sa_column=Column(
            ARRAY(Text),
            nullable=False,
            server_default=text("'{QUOTE}'"),
        ),
    )

    complexity_score: Optional[int] = Field(default=None)

    classification: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(
            JSONB,
            nullable=False,
            server_default=text("'{}'::jsonb"),
        ),
    )

    # ---------- ATOMIC STRUCTURE ----------
    atomic_components: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )

    # ---------- PERFORMANCE ----------
    virality_score: float = Field(default=5.0)

    performance_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(
            JSONB,
            nullable=False,
            server_default=text("'{}'::jsonb"),
        ),
    )

    times_used: int = Field(default=0)
    last_used_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True)),
    )

    # ---------- LIFECYCLE ----------
    lifecycle_state: LifecycleState = Field(default=LifecycleState.ACTIVE)

    lifecycle_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(
            JSONB,
            nullable=False,
            server_default=text("'{}'::jsonb"),
        ),
    )

    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True)),
    )

    # ---------- VERIFICATION ----------
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED
    )

    verification_notes: Optional[str] = Field(default=None)

    # ---------- TIMESTAMPS ----------
    extracted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True)),
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )

    # ---------- EMBEDDINGS ----------
    content_embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(Vector(1536)),
    )

    # ---------- LLM CLASSIFICATION METADATA ----------
    confidence_score: Optional[float] = Field(default=None)

    # ---------- RELATIONSHIPS ----------
    raw_ingest: Optional["RawIngest"] = Relationship(back_populates="content_atoms")
