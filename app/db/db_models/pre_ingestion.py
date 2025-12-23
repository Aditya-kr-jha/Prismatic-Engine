"""
Pre-Ingestion Models.

Database models for evergreen content sources (books, blogs, podcasts)
and the content reservoir for weekly feeding into raw_ingest.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    Column,
    TIMESTAMP,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlmodel import SQLModel, Field, Relationship

from app.db.enums import (
    EvergreenSourceType,
    FileType,
    EvergreenSourceStatus,
    ReservoirStatus,
)


class EvergreenSource(SQLModel, table=True):
    """
    Evergreen content sources like books, blogs, and podcasts.
    
    These are high-quality sources that are processed once and
    provide chunks for the content reservoir.
    """
    __tablename__ = "evergreen_sources"

    __table_args__ = (
        # Prevent duplicate sources
        UniqueConstraint(
            "source_type",
            "title",
            "author",
            name="uq_evergreen_sources_type_title_author",
        ),
        # Filter by status for processing pipeline
        Index(
            "ix_evergreen_sources_status",
            "status",
            postgresql_where=text("status IN ('PENDING', 'PROCESSING')"),
        ),
        # Source type filtering
        Index("ix_evergreen_sources_type", "source_type"),
    )

    # ---------- PRIMARY ----------
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # ---------- SOURCE INFO ----------
    source_type: EvergreenSourceType = Field(nullable=False)
    title: str = Field(nullable=False)
    author: str = Field(nullable=False)

    # ---------- FILE INFO ----------
    file_path: Optional[str] = Field(default=None)
    file_type: Optional[FileType] = Field(default=None)

    # ---------- PROCESSING STATE ----------
    status: EvergreenSourceStatus = Field(
        default=EvergreenSourceStatus.PENDING,
        nullable=False,
    )
    chunks_extracted: int = Field(default=0)
    error_message: Optional[str] = Field(default=None)

    # ---------- TIMESTAMPS ----------
    created_at: datetime = Field(
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

    # ---------- RELATIONSHIPS ----------
    chunks: List["ContentReservoir"] = Relationship(back_populates="source")


class ContentReservoir(SQLModel, table=True):
    """
    Content reservoir for storing extracted chunks from evergreen sources.
    
    These chunks are queued weekly for feeding into raw_ingest.
    Lifecycle: AVAILABLE -> QUEUED -> USED -> COOLDOWN -> AVAILABLE
    """
    __tablename__ = "content_reservoir"

    __table_args__ = (
        # Prevent duplicate chunks per source
        UniqueConstraint(
            "source_id",
            "chunk_index",
            name="uq_content_reservoir_source_chunk",
        ),
        # Find available content for queueing
        Index(
            "ix_content_reservoir_status_available",
            "status",
            postgresql_where=text("status = 'AVAILABLE'"),
        ),
        # Find content past cooldown
        Index(
            "ix_content_reservoir_cooldown",
            "cooldown_until",
            postgresql_where=text("cooldown_until IS NOT NULL"),
        ),
        # Filter by source type
        Index("ix_content_reservoir_source_type", "source_type"),
    )

    # ---------- PRIMARY ----------
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # ---------- SOURCE LINK ----------
    source_id: uuid.UUID = Field(
        foreign_key="evergreen_sources.id",
        nullable=False,
    )

    # ---------- CONTENT ----------
    raw_text: str = Field(nullable=False)
    raw_title: Optional[str] = Field(default=None)
    chunk_index: int = Field(nullable=False)

    # ---------- DENORMALIZED SOURCE METADATA ----------
    source_type: Optional[str] = Field(default=None)
    source_name: Optional[str] = Field(default=None)
    source_author: Optional[str] = Field(default=None)

    # ---------- LIFECYCLE ----------
    status: ReservoirStatus = Field(
        default=ReservoirStatus.AVAILABLE,
        nullable=False,
    )
    times_used: int = Field(default=0)
    last_used_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True)),
    )
    cooldown_until: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True)),
    )

    # ---------- TIMESTAMPS ----------
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    # ---------- RELATIONSHIPS ----------
    source: Optional["EvergreenSource"] = Relationship(back_populates="chunks")
