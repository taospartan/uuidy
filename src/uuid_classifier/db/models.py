"""SQLAlchemy 2.0 async models for UUID classification records."""

import re
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# UUID format regex (standard UUID with hyphens or without)
UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}$"
)


def normalize_uuid(uuid_str: str) -> str:
    """Normalize UUID to standard format with hyphens and lowercase.

    Args:
        uuid_str: UUID string in any valid format.

    Returns:
        Normalized UUID string (lowercase with hyphens).

    Raises:
        ValueError: If the UUID format is invalid.
    """
    if not UUID_PATTERN.match(uuid_str):
        raise ValueError(f"Invalid UUID format: {uuid_str}")

    # Remove hyphens, lowercase, then reinsert hyphens
    clean = uuid_str.replace("-", "").lower()
    return f"{clean[:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:]}"


class UUIDClassification(Base):
    """Model for storing UUID classification records.

    Attributes:
        uuid: The UUID being classified (primary key).
        name: Human-readable name for the UUID (e.g., "Heart Rate Service").
        type: Classification type (e.g., "Standard BLE Service", "Vendor-Specific").
        description: Detailed description of the UUID's purpose.
        sources: JSON array of source references with title, url, and snippet.
        confidence: Confidence level of the classification (high/medium/low).
        searched_at: When the search was performed.
        created_at: When the record was created.
        updated_at: When the record was last updated.
    """

    __tablename__ = "uuid_classifications"

    uuid: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Unknown",
    )
    type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Unknown",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    sources: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    confidence: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="low",
    )
    searched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Add index on searched_at for TTL queries
    __table_args__ = (Index("ix_uuid_classifications_searched_at", "searched_at"),)

    def __init__(
        self,
        uuid: str,
        name: str = "Unknown",
        type: str = "Unknown",  # noqa: A002
        description: str | None = None,
        sources: list[dict[str, Any]] | None = None,
        confidence: str = "low",
        **kwargs: Any,
    ) -> None:
        """Initialize UUIDClassification with UUID validation.

        Args:
            uuid: The UUID to classify (will be normalized).
            name: Human-readable name for the UUID.
            type: Classification type.
            description: Detailed description.
            sources: List of source references.
            confidence: Confidence level (high/medium/low).
            **kwargs: Additional fields for the model.

        Raises:
            ValueError: If the UUID format is invalid.
        """
        # Validate and normalize UUID at application level
        normalized_uuid = normalize_uuid(uuid)
        # Handle mutable default for sources
        if sources is None:
            sources = []
        super().__init__(
            uuid=normalized_uuid,
            name=name,
            type=type,
            description=description,
            sources=sources,
            confidence=confidence,
            **kwargs,
        )

    def __repr__(self) -> str:
        """Return a string representation for debugging."""
        return (
            f"UUIDClassification("
            f"uuid={self.uuid!r}, "
            f"name={self.name!r}, "
            f"type={self.type!r}, "
            f"confidence={self.confidence!r})"
        )
