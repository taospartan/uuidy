"""Unit tests for database models."""

import pytest

from uuid_classifier.db.models import UUIDClassification, normalize_uuid


class TestNormalizeUUID:
    """Tests for UUID normalization function."""

    def test_normalize_uuid_with_hyphens(self) -> None:
        """Test normalizing a UUID that already has hyphens."""
        uuid = "550E8400-E29B-41D4-A716-446655440000"
        result = normalize_uuid(uuid)
        assert result == "550e8400-e29b-41d4-a716-446655440000"

    def test_normalize_uuid_without_hyphens(self) -> None:
        """Test normalizing a UUID without hyphens."""
        uuid = "550E8400E29B41D4A716446655440000"
        result = normalize_uuid(uuid)
        assert result == "550e8400-e29b-41d4-a716-446655440000"

    def test_normalize_uuid_lowercase(self) -> None:
        """Test that normalization converts to lowercase."""
        uuid = "ABCDEF00-1234-5678-9ABC-DEF012345678"
        result = normalize_uuid(uuid)
        assert result == "abcdef00-1234-5678-9abc-def012345678"

    def test_normalize_uuid_already_normalized(self) -> None:
        """Test normalizing an already normalized UUID."""
        uuid = "00001800-0000-1000-8000-00805f9b34fb"
        result = normalize_uuid(uuid)
        assert result == "00001800-0000-1000-8000-00805f9b34fb"

    def test_normalize_uuid_invalid_characters(self) -> None:
        """Test that invalid characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            normalize_uuid("ZZZZZZZZ-ZZZZ-ZZZZ-ZZZZ-ZZZZZZZZZZZZ")

    def test_normalize_uuid_wrong_length(self) -> None:
        """Test that wrong length UUIDs raise ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            normalize_uuid("550e8400-e29b-41d4")

    def test_normalize_uuid_empty_string(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            normalize_uuid("")


class TestUUIDClassificationModel:
    """Tests for UUIDClassification SQLAlchemy model."""

    def test_create_model_with_valid_uuid(self) -> None:
        """Test creating a model with a valid UUID."""
        classification = UUIDClassification(
            uuid="00001800-0000-1000-8000-00805f9b34fb",
            name="Generic Access",
            type="Standard BLE Service",
            description="Bluetooth SIG standard service",
            confidence="high",
        )
        assert classification.uuid == "00001800-0000-1000-8000-00805f9b34fb"
        assert classification.name == "Generic Access"
        assert classification.type == "Standard BLE Service"
        assert classification.confidence == "high"

    def test_create_model_with_uppercase_uuid(self) -> None:
        """Test that uppercase UUIDs are normalized to lowercase."""
        classification = UUIDClassification(
            uuid="00001800-0000-1000-8000-00805F9B34FB",
        )
        assert classification.uuid == "00001800-0000-1000-8000-00805f9b34fb"

    def test_create_model_with_uuid_without_hyphens(self) -> None:
        """Test that UUIDs without hyphens are normalized."""
        classification = UUIDClassification(
            uuid="0000180000001000800000805f9b34fb",
        )
        assert classification.uuid == "00001800-0000-1000-8000-00805f9b34fb"

    def test_create_model_with_invalid_uuid_raises_error(self) -> None:
        """Test that invalid UUIDs raise ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            UUIDClassification(uuid="invalid-uuid")

    def test_model_default_values(self) -> None:
        """Test that model has correct default values."""
        classification = UUIDClassification(
            uuid="00001800-0000-1000-8000-00805f9b34fb",
        )
        assert classification.name == "Unknown"
        assert classification.type == "Unknown"
        assert classification.description is None
        assert classification.sources == []
        assert classification.confidence == "low"

    def test_model_with_sources(self) -> None:
        """Test creating model with sources JSON array."""
        sources = [
            {
                "title": "Bluetooth SIG",
                "url": "https://bluetooth.com",
                "snippet": "Standard service",
            },
            {
                "title": "Developer Docs",
                "url": "https://example.com",
                "snippet": "Implementation guide",
            },
        ]
        classification = UUIDClassification(
            uuid="00001800-0000-1000-8000-00805f9b34fb",
            sources=sources,
        )
        assert classification.sources == sources
        assert len(classification.sources) == 2
        assert classification.sources[0]["title"] == "Bluetooth SIG"

    def test_model_repr(self) -> None:
        """Test __repr__ returns useful debug string."""
        classification = UUIDClassification(
            uuid="00001800-0000-1000-8000-00805f9b34fb",
            name="Generic Access",
            type="Standard BLE Service",
            confidence="high",
        )
        repr_str = repr(classification)
        assert "UUIDClassification" in repr_str
        assert "00001800-0000-1000-8000-00805f9b34fb" in repr_str
        assert "Generic Access" in repr_str
        assert "Standard BLE Service" in repr_str
        assert "high" in repr_str

    def test_model_confidence_values(self) -> None:
        """Test that all confidence levels can be set."""
        for confidence in ["high", "medium", "low"]:
            classification = UUIDClassification(
                uuid="00001800-0000-1000-8000-00805f9b34fb",
                confidence=confidence,
            )
            assert classification.confidence == confidence
