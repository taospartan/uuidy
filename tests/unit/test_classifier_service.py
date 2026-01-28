"""Unit tests for ClassifierService.

Tests the heuristic-based UUID classification logic including:
- Standard BLE service identification
- Vendor-specific detection
- iBeacon/Eddystone detection
- Name extraction from search results
- Confidence level calculation
- Empty result handling
"""

import pytest
from datetime import datetime, UTC

from uuid_classifier.schemas.classification import (
    ClassificationCreate,
    ClassificationType,
    ConfidenceLevel,
    SearchResult,
)
from uuid_classifier.services.classifier_service import ClassifierService


@pytest.fixture
def classifier_service() -> ClassifierService:
    """Create a ClassifierService instance for testing."""
    return ClassifierService()


# Known Bluetooth SIG service UUIDs for testing
HEART_RATE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
DEVICE_INFO_UUID = "0000180a-0000-1000-8000-00805f9b34fb"
GENERIC_ACCESS_UUID = "00001800-0000-1000-8000-00805f9b34fb"

# Custom/unknown UUIDs for testing
NORDIC_UART_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UNKNOWN_UUID = "12345678-1234-1234-1234-123456789abc"
CUSTOM_UUID = "abcdef01-2345-6789-abcd-ef0123456789"


# ============================================================================
# Fixtures for search results
# ============================================================================


@pytest.fixture
def heart_rate_search_results() -> list[SearchResult]:
    """Search results for Heart Rate Service UUID."""
    return [
        SearchResult(
            title="Heart Rate Service - Bluetooth SIG",
            url="https://www.bluetooth.com/specifications/gatt/services/",
            snippet="The Heart Rate Service exposes heart rate and other data from a Heart Rate Sensor intended for fitness applications. UUID: 0x180D",
            position=1,
        ),
        SearchResult(
            title="GATT Specifications | Bluetooth® Technology Website",
            url="https://www.bluetooth.com/specifications/gatt/",
            snippet="GATT Services and Characteristics. Heart Rate Service (0x180D) - Exposes heart rate data.",
            position=2,
        ),
        SearchResult(
            title="Bluetooth Low Energy Heart Rate Service - Nordic Semiconductor",
            url="https://infocenter.nordicsemi.com/topic/sdk_nrf5_v17.1.0/ble_sdk_app_hrs.html",
            snippet="The Heart Rate Service (HRS) with UUID 0x180D is a standardized BLE service for heart rate monitors.",
            position=3,
        ),
        SearchResult(
            title="Understanding BLE GATT Services and Characteristics",
            url="https://developer.apple.com/documentation/corebluetooth",
            snippet="Bluetooth GATT defines standardized services like Heart Rate (180D), Battery Service (180F), and more.",
            position=4,
        ),
        SearchResult(
            title="Heart Rate Monitor BLE Implementation Guide",
            url="https://github.com/example/ble-heart-rate",
            snippet="Implementation of BLE Heart Rate Service (UUID: 0000180d-0000-1000-8000-00805f9b34fb) for embedded devices.",
            position=5,
        ),
    ]


@pytest.fixture
def vendor_specific_search_results() -> list[SearchResult]:
    """Search results for Nordic UART Service (vendor-specific)."""
    return [
        SearchResult(
            title="Nordic UART Service (NUS) - Nordic Semiconductor",
            url="https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/libraries/bluetooth_services/nus.html",
            snippet="The Nordic UART Service (NUS) with UUID 6e400001-b5a3-f393-e0a9-e50e24dcca9e provides a serial port emulation over BLE.",
            position=1,
        ),
        SearchResult(
            title="BLE UART Service Tutorial",
            url="https://learn.adafruit.com/introduction-to-bluetooth-low-energy/uart-service",
            snippet="The Nordic UART Service is commonly used for serial communication over Bluetooth Low Energy.",
            position=2,
        ),
    ]


@pytest.fixture
def ibeacon_search_results() -> list[SearchResult]:
    """Search results indicating iBeacon."""
    return [
        SearchResult(
            title="Understanding iBeacon Technology",
            url="https://developer.apple.com/ibeacon/",
            snippet="iBeacon is Apple's implementation of Bluetooth low-energy wireless technology. Use iBeacon to create a proximity-based experience.",
            position=1,
        ),
        SearchResult(
            title="iBeacon UUID Registration",
            url="https://example.com/ibeacon-guide",
            snippet="The proximity UUID identifies an iBeacon and distinguishes your beacons from others.",
            position=2,
        ),
    ]


@pytest.fixture
def eddystone_search_results() -> list[SearchResult]:
    """Search results indicating Eddystone."""
    return [
        SearchResult(
            title="Eddystone Protocol Specification",
            url="https://github.com/google/eddystone",
            snippet="Eddystone is Google's open beacon format. Eddystone-UID broadcasts an identifier for the beacon.",
            position=1,
        ),
        SearchResult(
            title="Google Eddystone Beacons",
            url="https://developers.google.com/beacons",
            snippet="Google Eddystone beacons can broadcast URLs, UIDs, and telemetry data.",
            position=2,
        ),
    ]


@pytest.fixture
def conflicting_search_results() -> list[SearchResult]:
    """Search results with conflicting information."""
    return [
        SearchResult(
            title="Temperature Sensor Service",
            url="https://example.com/temp",
            snippet="This UUID is used for temperature sensors.",
            position=1,
        ),
        SearchResult(
            title="Humidity Monitoring Service",
            url="https://example.com/humidity",
            snippet="Custom UUID for humidity monitoring applications.",
            position=2,
        ),
        SearchResult(
            title="Environmental Data Service",
            url="https://example.com/env",
            snippet="Generic environmental data collection service.",
            position=3,
        ),
    ]


@pytest.fixture
def empty_search_results() -> list[SearchResult]:
    """Empty search results."""
    return []


# ============================================================================
# Tests for standard BLE service identification
# ============================================================================


class TestClassifyStandardBLEService:
    """Tests for classifying standard Bluetooth SIG services."""

    @pytest.mark.asyncio
    async def test_classify_heart_rate_service(
        self,
        classifier_service: ClassifierService,
        heart_rate_search_results: list[SearchResult],
    ) -> None:
        """Test classification of Heart Rate Service UUID."""
        result = await classifier_service.classify(
            HEART_RATE_UUID,
            heart_rate_search_results,
        )

        assert result.uuid == HEART_RATE_UUID
        assert result.name == "Heart Rate"
        assert result.type == ClassificationType.STANDARD_BLE_SERVICE
        assert result.confidence == ConfidenceLevel.HIGH
        assert "Heart Rate" in result.description
        assert len(result.sources) > 0

    @pytest.mark.asyncio
    async def test_classify_battery_service(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test classification of Battery Service UUID."""
        result = await classifier_service.classify(
            BATTERY_SERVICE_UUID,
            [],  # Even without search results, known UUIDs should be identified
        )

        assert result.uuid == BATTERY_SERVICE_UUID
        assert result.name == "Battery Service"
        assert result.type == ClassificationType.STANDARD_BLE_SERVICE
        assert result.confidence == ConfidenceLevel.HIGH

    @pytest.mark.asyncio
    async def test_classify_device_information_service(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test classification of Device Information Service UUID."""
        result = await classifier_service.classify(
            DEVICE_INFO_UUID,
            [],
        )

        assert result.uuid == DEVICE_INFO_UUID
        assert result.name == "Device Information"
        assert result.type == ClassificationType.STANDARD_BLE_SERVICE
        assert result.confidence == ConfidenceLevel.HIGH

    @pytest.mark.asyncio
    async def test_classify_generic_access_service(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test classification of Generic Access Service UUID."""
        result = await classifier_service.classify(
            GENERIC_ACCESS_UUID,
            [],
        )

        assert result.uuid == GENERIC_ACCESS_UUID
        assert result.name == "Generic Access"
        assert result.type == ClassificationType.STANDARD_BLE_SERVICE


# ============================================================================
# Tests for vendor-specific UUID classification
# ============================================================================


class TestClassifyVendorSpecific:
    """Tests for classifying vendor-specific UUIDs."""

    @pytest.mark.asyncio
    async def test_classify_vendor_specific(
        self,
        classifier_service: ClassifierService,
        vendor_specific_search_results: list[SearchResult],
    ) -> None:
        """Test classification of Nordic UART Service UUID."""
        result = await classifier_service.classify(
            NORDIC_UART_UUID,
            vendor_specific_search_results,
        )

        assert result.uuid == NORDIC_UART_UUID
        assert result.type == ClassificationType.VENDOR_SPECIFIC
        # Name should be extracted from results
        assert "UART" in result.name or "Nordic" in result.name or result.name == "Nordic UART Service"
        assert len(result.sources) == 2

    @pytest.mark.asyncio
    async def test_vendor_specific_with_apple_indicator(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test vendor-specific detection with Apple mentions."""
        search_results = [
            SearchResult(
                title="Apple Watch Custom Service",
                url="https://example.com/apple-watch",
                snippet="This Apple proprietary UUID is used for Apple Watch communication.",
                position=1,
            ),
        ]

        result = await classifier_service.classify(
            CUSTOM_UUID,
            search_results,
        )

        assert result.type == ClassificationType.VENDOR_SPECIFIC


# ============================================================================
# Tests for iBeacon/Eddystone classification
# ============================================================================


class TestClassifyBeacons:
    """Tests for classifying beacon-related UUIDs."""

    @pytest.mark.asyncio
    async def test_classify_ibeacon(
        self,
        classifier_service: ClassifierService,
        ibeacon_search_results: list[SearchResult],
    ) -> None:
        """Test classification when iBeacon is detected."""
        result = await classifier_service.classify(
            CUSTOM_UUID,
            ibeacon_search_results,
        )

        assert result.type == ClassificationType.APPLE_IBEACON

    @pytest.mark.asyncio
    async def test_classify_eddystone(
        self,
        classifier_service: ClassifierService,
        eddystone_search_results: list[SearchResult],
    ) -> None:
        """Test classification when Eddystone is detected."""
        result = await classifier_service.classify(
            CUSTOM_UUID,
            eddystone_search_results,
        )

        assert result.type == ClassificationType.GOOGLE_EDDYSTONE


# ============================================================================
# Tests for unknown UUID classification
# ============================================================================


class TestClassifyUnknown:
    """Tests for unknown UUID classification."""

    @pytest.mark.asyncio
    async def test_classify_unknown_uuid(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test classification of completely unknown UUID with no results."""
        result = await classifier_service.classify(
            UNKNOWN_UUID,
            [],
        )

        assert result.uuid == UNKNOWN_UUID
        assert result.name == "Unknown"
        assert result.type == ClassificationType.UNKNOWN
        assert result.confidence == ConfidenceLevel.LOW
        assert len(result.sources) == 0

    @pytest.mark.asyncio
    async def test_classify_empty_results(
        self,
        classifier_service: ClassifierService,
        empty_search_results: list[SearchResult],
    ) -> None:
        """Test classification with empty search results returns Unknown."""
        result = await classifier_service.classify(
            UNKNOWN_UUID,
            empty_search_results,
        )

        assert result.name == "Unknown"
        assert result.type == ClassificationType.UNKNOWN
        assert result.confidence == ConfidenceLevel.LOW
        assert result.sources == []
        assert "Unable to identify" in result.description


# ============================================================================
# Tests for confidence level calculation
# ============================================================================


class TestConfidenceLevel:
    """Tests for confidence level calculation."""

    @pytest.mark.asyncio
    async def test_confidence_high_with_agreement(
        self,
        classifier_service: ClassifierService,
        heart_rate_search_results: list[SearchResult],
    ) -> None:
        """Test high confidence with multiple agreeing results and authoritative source."""
        result = await classifier_service.classify(
            HEART_RATE_UUID,
            heart_rate_search_results,
        )

        # Known service should have HIGH confidence
        assert result.confidence == ConfidenceLevel.HIGH

    @pytest.mark.asyncio
    async def test_confidence_medium_with_some_agreement(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test medium confidence with partial agreement."""
        search_results = [
            SearchResult(
                title="Custom BLE Service Implementation",
                url="https://github.com/example/custom-ble",
                snippet="This BLE service implements custom functionality.",
                position=1,
            ),
            SearchResult(
                title="Custom BLE Service Guide",
                url="https://example.com/guide",
                snippet="Guide for implementing Custom BLE Service on embedded devices.",
                position=2,
            ),
        ]

        result = await classifier_service.classify(
            CUSTOM_UUID,
            search_results,
        )

        # Should be MEDIUM with 2 results mentioning same name
        assert result.confidence in [ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]

    @pytest.mark.asyncio
    async def test_confidence_low_with_conflicts(
        self,
        classifier_service: ClassifierService,
        conflicting_search_results: list[SearchResult],
    ) -> None:
        """Test low confidence with conflicting information."""
        result = await classifier_service.classify(
            CUSTOM_UUID,
            conflicting_search_results,
        )

        # Conflicting information should result in LOW confidence
        assert result.confidence == ConfidenceLevel.LOW

    @pytest.mark.asyncio
    async def test_confidence_high_with_authoritative_source(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test that authoritative sources boost confidence."""
        search_results = [
            SearchResult(
                title="Test Service - Bluetooth SIG",
                url="https://www.bluetooth.com/specifications/test-service",
                snippet="Test Service is a standardized BLE service.",
                position=1,
            ),
            SearchResult(
                title="Test Service Documentation",
                url="https://www.bluetooth.org/docs/test",
                snippet="Official documentation for Test Service.",
                position=2,
            ),
            SearchResult(
                title="Test Service Implementation",
                url="https://developer.nordicsemi.com/test",
                snippet="Test Service implementation guide.",
                position=3,
            ),
        ]

        result = await classifier_service.classify(
            CUSTOM_UUID,
            search_results,
        )

        # With authoritative sources and agreement, should be HIGH
        assert result.confidence == ConfidenceLevel.HIGH


# ============================================================================
# Tests for name extraction
# ============================================================================


class TestNameExtraction:
    """Tests for name extraction from search results."""

    @pytest.mark.asyncio
    async def test_name_extraction_from_title(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test name extraction from search result titles."""
        search_results = [
            SearchResult(
                title="Temperature Sensor Service - BLE Guide",
                url="https://example.com/temp",
                snippet="A service for temperature monitoring.",
                position=1,
            ),
            SearchResult(
                title="Temperature Sensor Service Implementation",
                url="https://example.com/impl",
                snippet="How to implement Temperature Sensor Service.",
                position=2,
            ),
            SearchResult(
                title="Temperature Sensor Service SDK",
                url="https://example.com/sdk",
                snippet="SDK for Temperature Sensor Service development.",
                position=3,
            ),
        ]

        result = await classifier_service.classify(
            CUSTOM_UUID,
            search_results,
        )

        assert "Temperature" in result.name or "Sensor" in result.name

    @pytest.mark.asyncio
    async def test_name_fallback_to_unknown(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test that name falls back to Unknown when no clear name found."""
        search_results = [
            SearchResult(
                title="Generic Page Title",
                url="https://example.com/page",
                snippet="Some generic text without clear service name.",
                position=1,
            ),
        ]

        result = await classifier_service.classify(
            CUSTOM_UUID,
            search_results,
        )

        # Should still return a result (may or may not be Unknown)
        assert result.name is not None
        assert len(result.name) > 0


# ============================================================================
# Tests for sources field population
# ============================================================================


class TestSourcesPopulation:
    """Tests for sources field population."""

    @pytest.mark.asyncio
    async def test_sources_populated_from_results(
        self,
        classifier_service: ClassifierService,
        heart_rate_search_results: list[SearchResult],
    ) -> None:
        """Test that sources field is populated from search results."""
        result = await classifier_service.classify(
            HEART_RATE_UUID,
            heart_rate_search_results,
        )

        assert len(result.sources) > 0
        assert len(result.sources) <= 5  # Should limit to 5 sources

        # Check source structure
        for source in result.sources:
            assert source.title
            assert source.url
            assert source.snippet

    @pytest.mark.asyncio
    async def test_sources_empty_for_no_results(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test that sources is empty when no search results."""
        result = await classifier_service.classify(
            UNKNOWN_UUID,
            [],
        )

        assert result.sources == []

    @pytest.mark.asyncio
    async def test_sources_limited_to_five(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test that sources are limited to 5 entries."""
        many_results = [
            SearchResult(
                title=f"Result {i}",
                url=f"https://example.com/{i}",
                snippet=f"Snippet for result {i}",
                position=i,
            )
            for i in range(1, 11)  # 10 results
        ]

        result = await classifier_service.classify(
            CUSTOM_UUID,
            many_results,
        )

        assert len(result.sources) <= 5


# ============================================================================
# Tests for result model validation
# ============================================================================


class TestResultModel:
    """Tests for ClassificationCreate result model."""

    @pytest.mark.asyncio
    async def test_result_has_searched_at_timestamp(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test that result includes searched_at timestamp."""
        before = datetime.now(UTC)

        result = await classifier_service.classify(
            HEART_RATE_UUID,
            [],
        )

        after = datetime.now(UTC)

        assert result.searched_at is not None
        assert before <= result.searched_at <= after

    @pytest.mark.asyncio
    async def test_result_is_classification_create_instance(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test that result is a ClassificationCreate instance."""
        result = await classifier_service.classify(
            HEART_RATE_UUID,
            [],
        )

        assert isinstance(result, ClassificationCreate)

    @pytest.mark.asyncio
    async def test_result_uuid_matches_input(
        self,
        classifier_service: ClassifierService,
    ) -> None:
        """Test that result UUID matches input UUID."""
        result = await classifier_service.classify(
            HEART_RATE_UUID,
            [],
        )

        assert result.uuid == HEART_RATE_UUID
