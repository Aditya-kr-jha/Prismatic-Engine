import uuid
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List

from sqlalchemy import (
    Column,
    String,
    TIMESTAMP,
    Index,
    UniqueConstraint,
    func,
    text,
    Computed,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field, Relationship

from app.db.enums import SourceType, IngestStatus, RejectionPhase


class RawIngest(SQLModel, table=True):
    __tablename__ = "raw_ingest"

    __table_args__ = (
        # ---------- UNIQUE CONSTRAINTS ----------
        UniqueConstraint(
            "source_type",
            "source_identifier",
            name="uq_raw_ingest_source_identifier",
        ),
        # Deduplication via hash (only when hash exists)
        Index(
            "uq_raw_ingest_content_hash",
            "content_hash",
            unique=True,
            postgresql_where=text("content_hash IS NOT NULL"),
        ),
        # ---------- PERFORMANCE INDEXES ----------
        Index(
            "ix_raw_ingest_status_active",
            "status",
            postgresql_where=text("status IN ('PENDING', 'PROCESSING')"),
        ),
        # Batch-based ingestion
        Index(
            "ix_raw_ingest_batch",
            "batch_id",
            postgresql_where=text("batch_id IS NOT NULL"),
        ),
        # Trace-based debugging
        Index("ix_raw_ingest_trace", "trace_id"),
        # Source + time ordering
        Index(
            "ix_raw_ingest_source_time",
            "source_type",
            "ingested_at",
        ),
        # Metadata search
        Index(
            "ix_raw_ingest_metadata_gin",
            "raw_metadata",
            postgresql_using="gin",
        ),
    )

    # ---------- PRIMARY ----------
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    trace_id: uuid.UUID = Field(default_factory=uuid.uuid4, nullable=False)

    # ---------- SOURCE ----------
    source_type: SourceType = Field(nullable=False)
    source_url: Optional[str] = Field(default=None)
    source_identifier: Optional[str] = Field(default=None)

    # ---------- RAW CONTENT ----------
    raw_content: str = Field(nullable=False)
    raw_title: Optional[str] = Field(default=None)

    raw_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(
            JSONB,
            nullable=False,
            server_default=text("'{}'::jsonb"),
        ),
    )

    # ---------- INGESTION STATE ----------
    status: IngestStatus = Field(
        default=IngestStatus.PENDING,
        nullable=False,
    )

    # ---------- HARVESTER ----------
    batch_id: Optional[uuid.UUID] = Field(default=None)

    # ---------- TIMESTAMPS ----------
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    processed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True)),
    )

    # ---------- DEDUPLICATION ----------
    content_hash: Optional[str] = Field(
        sa_column=Column(
            String,
            Computed("md5(raw_content)", persisted=True),
        )
    )

    # ---------- RELATIONSHIPS ----------
    rejected_contents: List["RejectedContent"] = Relationship(
        back_populates="raw_ingest"
    )

    # content_atoms: List["ContentAtom"] = Relationship(back_populates="raw_ingest")


class RejectedContent(SQLModel, table=True):
    __tablename__ = "rejected_content"

    __table_args__ = (
        # Trace-based inspection
        Index("ix_rejected_content_trace", "trace_id"),
        # Phase + time analysis
        Index(
            "ix_rejected_content_phase_time",
            "rejection_phase",
            "rejected_at",
        ),
        # JSONB reasons search
        Index(
            "ix_rejected_content_reasons_gin",
            "rejection_reasons",
            postgresql_using="gin",
        ),
    )

    # ---------- PRIMARY ----------
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # ---------- LINKING ----------
    trace_id: uuid.UUID = Field(nullable=False)

    raw_ingest_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="raw_ingest.id",
        ondelete="SET NULL",
    )

    # ---------- REJECTION ----------
    rejection_phase: RejectionPhase = Field(nullable=False)

    rejection_reasons: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )

    # Snapshot of content at rejection time
    content_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )

    # ---------- AUDIT ----------
    rejected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    rejected_by: Optional[str] = Field(default="system")

    # ---------- RELATIONSHIP ----------
    raw_ingest: Optional["RawIngest"] = Relationship(back_populates="rejected_contents")
