"""Unit tests for Pydantic schemas."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from uuid_classifier.schemas import (
    ClassificationCreate,
    ClassificationResponse,
    ClassificationType,
    ConfidenceLevel,
    SourceInfo,
    UUIDRequest,
)


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_values(self) -> None:
        """Test that all expected values exist."""
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.LOW == "low"

    def test_string_enum(self) -> None:
        """Test that ConfidenceLevel is a string enum."""
        assert isinstance(ConfidenceLevel.HIGH, str)
        assert ConfidenceLevel.HIGH == "high"


class TestClassificationType:
    """Tests for ClassificationType enum."""

    def test_all_values_exist(self) -> None:
        """Test that all expected classification types exist."""
        expected = [
            "Standard BLE Service",
            "Vendor-Specific",
            "Apple iBeacon",
            "Google Eddystone",
            "Custom Service",
            "Unknown",
        ]
        actual = [t.value for t in ClassificationType]
        assert sorted(actual) == sorted(expected)

    def test_string_enum(self) -> None:
        """Test that ClassificationType is a string enum."""
        assert isinstance(ClassificationType.STANDARD_BLE_SERVICE, str)
        assert ClassificationType.STANDARD_BLE_SERVICE == "Standard BLE Service"


class TestSourceInfo:
    """Tests for SourceInfo schema."""

    def test_valid_source(self) -> None:
        """Test creating a valid SourceInfo."""
        source = SourceInfo(
            title="Bluetooth GATT Services",
            url="https://www.bluetooth.com/specifications/gatt/services/",
            snippet="Heart Rate Service UUID: 0x180D",
        )
        assert source.title == "Bluetooth GATT Services"
        assert (
            str(source.url) == "https://www.bluetooth.com/specifications/gatt/services/"
        )
        assert source.snippet == "Heart Rate Service UUID: 0x180D"

    def test_invalid_url(self) -> None:
        """Test that invalid URLs raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SourceInfo(
                title="Test",
                url="not-a-valid-url",
                snippet="Test snippet",
            )
        assert "url" in str(exc_info.value).lower()

    def test_empty_title_rejected(self) -> None:
        """Test that empty title is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SourceInfo(
                title="",
                url="https://example.com",
                snippet="Test snippet",
            )
        assert "title" in str(exc_info.value).lower()

    def test_empty_snippet_rejected(self) -> None:
        """Test that empty snippet is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SourceInfo(
                title="Test",
                url="https://example.com",
                snippet="",
            )
        assert "snippet" in str(exc_info.value).lower()

    def test_has_example_in_schema(self) -> None:
        """Test that model has example values configured."""
        schema = SourceInfo.model_json_schema()
        assert "example" in schema or "examples" in schema


class TestUUIDValidation:
    """Tests for UUID validation across schemas."""

    # Valid UUIDs from task spec
    VALID_UUIDS = [
        "550e8400-e29b-41d4-a716-446655440000",
        "550E8400E29B41D4A716446655440000",
        "0000180d-0000-1000-8000-00805f9b34fb",
    ]

    # Invalid UUIDs from task spec
    INVALID_UUIDS = [
        "not-a-uuid",
        "550e8400-e29b-41d4-a716",
        "550e8400-e29b-41d4-a716-44665544000g",
    ]

    @pytest.mark.parametrize("uuid", VALID_UUIDS)
    def test_valid_uuids_pass_validation(self, uuid: str) -> None:
        """Test that valid UUID strings pass validation."""
        request = UUIDRequest(uuid=uuid)
        # Should normalize to lowercase with hyphens
        assert "-" in request.uuid
        assert request.uuid == request.uuid.lower()

    @pytest.mark.parametrize("uuid", INVALID_UUIDS)
    def test_invalid_uuids_raise_validation_error(self, uuid: str) -> None:
        """Test that invalid UUIDs raise ValidationError."""
        with pytest.raises(ValidationError):
            UUIDRequest(uuid=uuid)

    def test_uuid_normalization_lowercase(self) -> None:
        """Test that UUIDs are normalized to lowercase."""
        request = UUIDRequest(uuid="550E8400-E29B-41D4-A716-446655440000")
        assert request.uuid == "550e8400-e29b-41d4-a716-446655440000"

    def test_uuid_normalization_adds_hyphens(self) -> None:
        """Test that non-hyphenated UUIDs get hyphens added."""
        request = UUIDRequest(uuid="550E8400E29B41D4A716446655440000")
        assert request.uuid == "550e8400-e29b-41d4-a716-446655440000"

    def test_uuid_must_be_string(self) -> None:
        """Test that UUID must be a string type."""
        with pytest.raises(ValidationError):
            UUIDRequest(uuid=12345)  # type: ignore[arg-type]


class TestClassificationResponse:
    """Tests for ClassificationResponse schema."""

    @pytest.fixture
    def valid_response_data(self) -> dict:
        """Provide valid response data for tests."""
        return {
            "uuid": "0000180d-0000-1000-8000-00805f9b34fb",
            "name": "Heart Rate",
            "type": ClassificationType.STANDARD_BLE_SERVICE,
            "description": "Heart Rate Service for BLE devices",
            "sources": [
                SourceInfo(
                    title="Bluetooth GATT",
                    url="https://www.bluetooth.com/",
                    snippet="Heart Rate Service",
                )
            ],
            "confidence": ConfidenceLevel.HIGH,
            "cached": True,
            "searched_at": datetime.now(UTC),
        }

    def test_valid_response(self, valid_response_data: dict) -> None:
        """Test creating a valid ClassificationResponse."""
        response = ClassificationResponse(**valid_response_data)
        assert response.uuid == "0000180d-0000-1000-8000-00805f9b34fb"
        assert response.name == "Heart Rate"
        assert response.type == ClassificationType.STANDARD_BLE_SERVICE
        assert response.cached is True

    def test_datetime_serializes_to_iso_format(self, valid_response_data: dict) -> None:
        """Test that datetime serializes to ISO format."""
        response = ClassificationResponse(**valid_response_data)
        json_data = response.model_dump_json()
        # ISO format includes T separator and timezone info
        assert "T" in json_data
        assert "searched_at" in json_data

    def test_sources_accepts_list_of_source_info(
        self, valid_response_data: dict
    ) -> None:
        """Test that sources field accepts list of SourceInfo objects."""
        response = ClassificationResponse(**valid_response_data)
        assert len(response.sources) == 1
        assert isinstance(response.sources[0], SourceInfo)

    def test_sources_accepts_empty_list(self, valid_response_data: dict) -> None:
        """Test that sources field accepts empty list."""
        valid_response_data["sources"] = []
        response = ClassificationResponse(**valid_response_data)
        assert response.sources == []

    def test_sources_accepts_dict_list(self, valid_response_data: dict) -> None:
        """Test that sources field accepts list of dicts."""
        valid_response_data["sources"] = [
            {
                "title": "Test Source",
                "url": "https://example.com",
                "snippet": "Test snippet content",
            }
        ]
        response = ClassificationResponse(**valid_response_data)
        assert len(response.sources) == 1
        assert response.sources[0].title == "Test Source"

    def test_uuid_validation_in_response(self) -> None:
        """Test that UUID validation works in response schema."""
        with pytest.raises(ValidationError):
            ClassificationResponse(
                uuid="invalid-uuid",
                name="Test",
                type=ClassificationType.UNKNOWN,
                description="Test",
                sources=[],
                confidence=ConfidenceLevel.LOW,
                cached=False,
                searched_at=datetime.now(UTC),
            )

    def test_uuid_normalization_in_response(self) -> None:
        """Test that UUID is normalized in response."""
        response = ClassificationResponse(
            uuid="550E8400E29B41D4A716446655440000",
            name="Test",
            type=ClassificationType.UNKNOWN,
            description="Test",
            sources=[],
            confidence=ConfidenceLevel.LOW,
            cached=False,
            searched_at=datetime.now(UTC),
        )
        assert response.uuid == "550e8400-e29b-41d4-a716-446655440000"

    def test_unknown_type_has_low_confidence(self) -> None:
        """Test that Unknown classifications auto-correct to low confidence."""
        response = ClassificationResponse(
            uuid="0000180d-0000-1000-8000-00805f9b34fb",
            name="Unknown Service",
            type=ClassificationType.UNKNOWN,
            description="Could not identify this UUID",
            sources=[],
            confidence=ConfidenceLevel.HIGH,  # This should be corrected
            cached=False,
            searched_at=datetime.now(UTC),
        )
        assert response.confidence == ConfidenceLevel.LOW

    def test_has_example_in_schema(self) -> None:
        """Test that model has example values configured."""
        schema = ClassificationResponse.model_json_schema()
        assert "example" in schema or "examples" in schema


class TestClassificationCreate:
    """Tests for ClassificationCreate schema."""

    @pytest.fixture
    def valid_create_data(self) -> dict:
        """Provide valid create data for tests."""
        return {
            "uuid": "0000180d-0000-1000-8000-00805f9b34fb",
            "name": "Heart Rate",
            "type": ClassificationType.STANDARD_BLE_SERVICE,
            "description": "Heart Rate Service for BLE devices",
            "sources": [],
            "confidence": ConfidenceLevel.HIGH,
            "searched_at": datetime.now(UTC),
        }

    def test_valid_create(self, valid_create_data: dict) -> None:
        """Test creating a valid ClassificationCreate."""
        create = ClassificationCreate(**valid_create_data)
        assert create.uuid == "0000180d-0000-1000-8000-00805f9b34fb"
        assert create.name == "Heart Rate"

    def test_no_cached_field(self, valid_create_data: dict) -> None:
        """Test that ClassificationCreate does not have cached field."""
        create = ClassificationCreate(**valid_create_data)
        assert not hasattr(create, "cached") or "cached" not in create.model_fields

    def test_to_response_method(self, valid_create_data: dict) -> None:
        """Test conversion to response with cached flag."""
        create = ClassificationCreate(**valid_create_data)

        response_cached = create.to_response(cached=True)
        assert response_cached.cached is True
        assert isinstance(response_cached, ClassificationResponse)

        response_fresh = create.to_response(cached=False)
        assert response_fresh.cached is False

    def test_uuid_validation_in_create(self) -> None:
        """Test that UUID validation works in create schema."""
        with pytest.raises(ValidationError):
            ClassificationCreate(
                uuid="not-valid",
                name="Test",
                type=ClassificationType.UNKNOWN,
                description="Test",
                sources=[],
                confidence=ConfidenceLevel.LOW,
                searched_at=datetime.now(UTC),
            )

    def test_has_example_in_schema(self) -> None:
        """Test that model has example values configured."""
        schema = ClassificationCreate.model_json_schema()
        assert "example" in schema or "examples" in schema


class TestUUIDRequest:
    """Tests for UUIDRequest schema."""

    def test_valid_request(self) -> None:
        """Test creating a valid UUIDRequest."""
        request = UUIDRequest(uuid="0000180d-0000-1000-8000-00805f9b34fb")
        assert request.uuid == "0000180d-0000-1000-8000-00805f9b34fb"

    def test_has_example_in_schema(self) -> None:
        """Test that model has example values configured."""
        schema = UUIDRequest.model_json_schema()
        assert "example" in schema or "examples" in schema
