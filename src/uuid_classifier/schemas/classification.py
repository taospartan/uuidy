"""Pydantic schemas for UUID classification request/response models."""

import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


class ConfidenceLevel(StrEnum):
    """Confidence level for classification results."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ClassificationType(StrEnum):
    """Types of UUID classifications."""

    STANDARD_BLE_SERVICE = "Standard BLE Service"
    VENDOR_SPECIFIC = "Vendor-Specific"
    APPLE_IBEACON = "Apple iBeacon"
    GOOGLE_EDDYSTONE = "Google Eddystone"
    CUSTOM_SERVICE = "Custom Service"
    UNKNOWN = "Unknown"


class SourceInfo(BaseModel):
    """Information about a source used for classification."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Bluetooth GATT Services",
                "url": "https://www.bluetooth.com/specifications/gatt/services/",
                "snippet": "Heart Rate Service UUID: 0x180D",
            }
        }
    )

    title: str = Field(
        ...,
        description="Title of the source page or document",
        min_length=1,
    )
    url: HttpUrl = Field(
        ...,
        description="URL of the source",
    )
    snippet: str = Field(
        ...,
        description="Relevant excerpt from the source",
        min_length=1,
    )


# UUID regex pattern - matches both hyphenated and non-hyphenated formats
UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}$"
)


def normalize_uuid(value: str) -> str:
    """Normalize UUID to lowercase with hyphens.

    Args:
        value: UUID string (with or without hyphens)

    Returns:
        Normalized UUID string (lowercase with hyphens)
    """
    # Remove any existing hyphens and convert to lowercase
    clean = value.replace("-", "").lower()
    # Insert hyphens at standard positions: 8-4-4-4-12
    return f"{clean[:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:]}"


class ClassificationResponse(BaseModel):
    """Response model for UUID classification results."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uuid": "0000180d-0000-1000-8000-00805f9b34fb",
                "name": "Heart Rate",
                "type": "Standard BLE Service",
                "description": "Bluetooth SIG standardized Heart Rate Service for heart rate monitors",
                "sources": [
                    {
                        "title": "Bluetooth GATT Services",
                        "url": "https://www.bluetooth.com/specifications/gatt/services/",
                        "snippet": "Heart Rate Service UUID: 0x180D",
                    }
                ],
                "confidence": "high",
                "cached": True,
                "searched_at": "2024-01-15T10:30:00Z",
            }
        }
    )

    uuid: str = Field(
        ...,
        description="The UUID being classified (normalized to lowercase with hyphens)",
    )
    name: str = Field(
        ...,
        description="Human-readable name for the UUID, or 'Unknown' if not identified",
    )
    type: ClassificationType = Field(
        ...,
        description="Classification type of the UUID",
    )
    description: str = Field(
        ...,
        description="Detailed description of what the UUID represents",
    )
    sources: list[SourceInfo] = Field(
        default_factory=list,
        description="List of sources used to identify this UUID",
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="Confidence level of the classification",
    )
    cached: bool = Field(
        ...,
        description="Whether this result was retrieved from cache",
    )
    searched_at: datetime = Field(
        ...,
        description="Timestamp when the classification was performed or retrieved",
    )

    @field_validator("uuid", mode="before")
    @classmethod
    def validate_and_normalize_uuid(cls, v: str) -> str:
        """Validate UUID format and normalize to lowercase with hyphens."""
        if not isinstance(v, str):
            raise ValueError("UUID must be a string")

        if not UUID_PATTERN.match(v):
            raise ValueError(
                "Invalid UUID format. Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx "
                "or xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            )

        return normalize_uuid(v)

    @model_validator(mode="after")
    def validate_unknown_has_low_confidence(self) -> Self:
        """Ensure Unknown classifications have low confidence."""
        if (
            self.type == ClassificationType.UNKNOWN
            and self.confidence != ConfidenceLevel.LOW
        ):
            # Auto-correct confidence for unknown types
            object.__setattr__(self, "confidence", ConfidenceLevel.LOW)
        return self


class ClassificationCreate(BaseModel):
    """Internal schema for creating classification records in the database."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uuid": "0000180d-0000-1000-8000-00805f9b34fb",
                "name": "Heart Rate",
                "type": "Standard BLE Service",
                "description": "Bluetooth SIG standardized Heart Rate Service",
                "sources": [],
                "confidence": "high",
                "searched_at": "2024-01-15T10:30:00Z",
            }
        }
    )

    uuid: str = Field(
        ...,
        description="The UUID being classified (normalized to lowercase with hyphens)",
    )
    name: str = Field(
        ...,
        description="Human-readable name for the UUID",
    )
    type: ClassificationType = Field(
        ...,
        description="Classification type of the UUID",
    )
    description: str = Field(
        ...,
        description="Detailed description of what the UUID represents",
    )
    sources: list[SourceInfo] = Field(
        default_factory=list,
        description="List of sources used to identify this UUID",
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="Confidence level of the classification",
    )
    searched_at: datetime = Field(
        ...,
        description="Timestamp when the classification was performed",
    )

    @field_validator("uuid", mode="before")
    @classmethod
    def validate_and_normalize_uuid(cls, v: str) -> str:
        """Validate UUID format and normalize to lowercase with hyphens."""
        if not isinstance(v, str):
            raise ValueError("UUID must be a string")

        if not UUID_PATTERN.match(v):
            raise ValueError(
                "Invalid UUID format. Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx "
                "or xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            )

        return normalize_uuid(v)

    def to_response(self, *, cached: bool) -> ClassificationResponse:
        """Convert to response model with cached flag.

        Args:
            cached: Whether this result was retrieved from cache

        Returns:
            ClassificationResponse with the cached flag set
        """
        return ClassificationResponse(
            uuid=self.uuid,
            name=self.name,
            type=self.type,
            description=self.description,
            sources=self.sources,
            confidence=self.confidence,
            cached=cached,
            searched_at=self.searched_at,
        )


class SearchResult(BaseModel):
    """Model representing a single search result from SerpAPI.

    This is used internally by the SearchService to pass results
    to the ClassifierService.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Heart Rate Service - Bluetooth SIG",
                "url": "https://www.bluetooth.com/specifications/gatt/services/",
                "snippet": "The Heart Rate Service exposes heart rate and other data...",
                "position": 1,
            }
        }
    )

    title: str = Field(
        ...,
        description="Title of the search result",
        min_length=1,
    )
    url: str = Field(
        ...,
        description="URL of the search result",
        min_length=1,
    )
    snippet: str = Field(
        default="",
        description="Snippet or description from the search result",
    )
    position: int = Field(
        ...,
        description="Position of the result in the search results (1-indexed)",
        ge=1,
    )


class UUIDRequest(BaseModel):
    """Request model for UUID classification."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uuid": "0000180d-0000-1000-8000-00805f9b34fb",
            }
        }
    )

    uuid: Annotated[
        str,
        Field(
            description="UUID to classify (accepts both hyphenated and non-hyphenated formats)",
        ),
    ]

    @field_validator("uuid", mode="before")
    @classmethod
    def validate_and_normalize_uuid(cls, v: str) -> str:
        """Validate UUID format and normalize to lowercase with hyphens."""
        if not isinstance(v, str):
            raise ValueError("UUID must be a string")

        if not UUID_PATTERN.match(v):
            raise ValueError(
                "Invalid UUID format. Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx "
                "or xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            )

        return normalize_uuid(v)
