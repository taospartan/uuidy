"""Pytest configuration and shared fixtures.

Provides shared test fixtures used across unit and integration tests.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from uuid_classifier.main import app
from uuid_classifier.schemas.classification import (
    ClassificationCreate,
    ClassificationResponse,
    ClassificationType,
    ConfidenceLevel,
    SearchResult,
    SourceInfo,
)
from uuid_classifier.services.search_service import SearchService


# Pytest markers for distinguishing test types
def pytest_configure(config: Any) -> None:
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ============================================================================
# Standard Test UUIDs
# ============================================================================


@pytest.fixture
def heart_rate_uuid() -> str:
    """Heart Rate Service UUID (standard BLE)."""
    return "0000180d-0000-1000-8000-00805f9b34fb"


@pytest.fixture
def battery_service_uuid() -> str:
    """Battery Service UUID (standard BLE)."""
    return "0000180f-0000-1000-8000-00805f9b34fb"


@pytest.fixture
def nordic_uart_uuid() -> str:
    """Nordic UART Service UUID (vendor-specific)."""
    return "6e400001-b5a3-f393-e0a9-e50e24dcca9e"


@pytest.fixture
def unknown_test_uuid() -> str:
    """Unknown UUID for testing cache miss scenarios."""
    return "12345678-1234-1234-1234-123456789abc"


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_source_info() -> SourceInfo:
    """Sample source information."""
    return SourceInfo(
        title="Bluetooth GATT Services",
        url="https://www.bluetooth.com/specifications/gatt/services/",
        snippet="Heart Rate Service UUID: 0x180D",
    )


@pytest.fixture
def sample_search_result() -> SearchResult:
    """Sample search result."""
    return SearchResult(
        title="Heart Rate Service - Bluetooth SIG",
        url="https://www.bluetooth.com/specifications/gatt/services/",
        snippet="The Heart Rate Service exposes heart rate data. UUID: 0x180D",
        position=1,
    )


@pytest.fixture
def sample_search_results(sample_search_result: SearchResult) -> list[SearchResult]:
    """Sample list of search results."""
    return [
        sample_search_result,
        SearchResult(
            title="BLE Heart Rate Tutorial",
            url="https://example.com/ble-hrs",
            snippet="Heart Rate Service for fitness applications.",
            position=2,
        ),
        SearchResult(
            title="Bluetooth Heart Rate Monitor",
            url="https://developer.example.com/hrm",
            snippet="Standardized Heart Rate Service 0x180D.",
            position=3,
        ),
    ]


@pytest.fixture
def sample_classification_create(
    heart_rate_uuid: str,
    sample_source_info: SourceInfo,
) -> ClassificationCreate:
    """Sample classification create model."""
    return ClassificationCreate(
        uuid=heart_rate_uuid,
        name="Heart Rate",
        type=ClassificationType.STANDARD_BLE_SERVICE,
        description="Bluetooth SIG standardized Heart Rate Service",
        sources=[sample_source_info],
        confidence=ConfidenceLevel.HIGH,
        searched_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_classification_response(
    heart_rate_uuid: str,
    sample_source_info: SourceInfo,
) -> ClassificationResponse:
    """Sample classification response model."""
    return ClassificationResponse(
        uuid=heart_rate_uuid,
        name="Heart Rate",
        type=ClassificationType.STANDARD_BLE_SERVICE,
        description="Bluetooth SIG standardized Heart Rate Service",
        sources=[sample_source_info],
        confidence=ConfidenceLevel.HIGH,
        cached=True,
        searched_at=datetime.now(UTC),
    )


# ============================================================================
# Mock Service Fixtures
# ============================================================================


@pytest.fixture
def mock_search_service_fixture(
    sample_search_results: list[SearchResult],
) -> AsyncMock:
    """Auto-used mock for SearchService (prevents real API calls)."""
    mock = AsyncMock(spec=SearchService)
    mock.search_uuid = AsyncMock(return_value=sample_search_results)
    return mock


@pytest.fixture
def mock_search_service_empty() -> AsyncMock:
    """Mock SearchService returning empty results."""
    mock = AsyncMock(spec=SearchService)
    mock.search_uuid = AsyncMock(return_value=[])
    return mock
