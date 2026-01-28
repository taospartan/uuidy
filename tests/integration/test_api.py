"""Integration tests for the UUID classification API endpoints.

These tests verify the full request/response cycle of the API,
including endpoint routing, validation, and orchestration flow.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from uuid_classifier import __version__
from uuid_classifier.api.dependencies import (
    get_cache_service,
    get_classifier_service,
    get_search_service,
)
from uuid_classifier.main import app
from uuid_classifier.schemas.classification import (
    ClassificationCreate,
    ClassificationResponse,
    ClassificationType,
    ConfidenceLevel,
    SearchResult,
    SourceInfo,
)
from uuid_classifier.services.cache_service import CacheService
from uuid_classifier.services.classifier_service import ClassifierService
from uuid_classifier.services.search_service import SearchService


@pytest.fixture
def sample_classification_response() -> ClassificationResponse:
    """Sample classification response for testing."""
    return ClassificationResponse(
        uuid="0000180d-0000-1000-8000-00805f9b34fb",
        name="Heart Rate",
        type=ClassificationType.STANDARD_BLE_SERVICE,
        description="Bluetooth SIG standardized Heart Rate Service for heart rate monitors",
        sources=[
            SourceInfo(
                title="Bluetooth GATT Services",
                url="https://www.bluetooth.com/specifications/gatt/services/",
                snippet="Heart Rate Service UUID: 0x180D",
            )
        ],
        confidence=ConfidenceLevel.HIGH,
        cached=True,
        searched_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_classification_create() -> ClassificationCreate:
    """Sample classification create model for testing."""
    return ClassificationCreate(
        uuid="0000180d-0000-1000-8000-00805f9b34fb",
        name="Heart Rate",
        type=ClassificationType.STANDARD_BLE_SERVICE,
        description="Bluetooth SIG standardized Heart Rate Service for heart rate monitors",
        sources=[
            SourceInfo(
                title="Bluetooth GATT Services",
                url="https://www.bluetooth.com/specifications/gatt/services/",
                snippet="Heart Rate Service UUID: 0x180D",
            )
        ],
        confidence=ConfidenceLevel.HIGH,
        searched_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_search_results() -> list[SearchResult]:
    """Sample search results for testing."""
    return [
        SearchResult(
            title="Heart Rate Service - Bluetooth SIG",
            url="https://www.bluetooth.com/specifications/gatt/services/",
            snippet="The Heart Rate Service exposes heart rate and other data...",
            position=1,
        ),
        SearchResult(
            title="BLE Heart Rate Monitor Tutorial",
            url="https://example.com/ble-tutorial",
            snippet="Heart Rate Service UUID 0x180D is used for...",
            position=2,
        ),
    ]


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    async def test_health_endpoint_returns_ok(self) -> None:
        """Test that health endpoint returns status ok and version."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == __version__


class TestClassifyGetEndpoint:
    """Tests for GET /classify/{uuid} endpoint."""

    async def test_classify_valid_uuid_cache_hit(
        self,
        sample_classification_response: ClassificationResponse,
    ) -> None:
        """Test classification returns cached result when available."""
        # Create mock services
        mock_cache_service = AsyncMock(spec=CacheService)
        mock_cache_service.get_classification = AsyncMock(
            return_value=sample_classification_response
        )

        async def override_cache_service() -> AsyncGenerator[CacheService, None]:
            yield mock_cache_service

        # Override dependencies
        app.dependency_overrides[get_cache_service] = override_cache_service

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/classify/0000180d-0000-1000-8000-00805f9b34fb"
                )

            assert response.status_code == 200
            data = response.json()
            assert data["uuid"] == "0000180d-0000-1000-8000-00805f9b34fb"
            assert data["cached"] is True
            mock_cache_service.get_classification.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_classify_valid_uuid_cache_miss(
        self,
        sample_classification_create: ClassificationCreate,
        sample_search_results: list[SearchResult],
    ) -> None:
        """Test classification triggers search and returns new result on cache miss."""
        # Create response with cached=False
        new_response = ClassificationResponse(
            uuid=sample_classification_create.uuid,
            name=sample_classification_create.name,
            type=sample_classification_create.type,
            description=sample_classification_create.description,
            sources=sample_classification_create.sources,
            confidence=sample_classification_create.confidence,
            cached=False,
            searched_at=sample_classification_create.searched_at,
        )

        # Create mock services
        mock_cache_service = AsyncMock(spec=CacheService)
        mock_cache_service.get_classification = AsyncMock(return_value=None)
        mock_cache_service.save_classification = AsyncMock(return_value=new_response)

        mock_search_service = AsyncMock(spec=SearchService)
        mock_search_service.search_uuid = AsyncMock(return_value=sample_search_results)

        mock_classifier_service = AsyncMock(spec=ClassifierService)
        mock_classifier_service.classify = AsyncMock(
            return_value=sample_classification_create
        )

        async def override_cache() -> AsyncGenerator[CacheService, None]:
            yield mock_cache_service

        async def override_search() -> AsyncGenerator[SearchService, None]:
            yield mock_search_service

        async def override_classifier() -> AsyncGenerator[ClassifierService, None]:
            yield mock_classifier_service

        # Override dependencies
        app.dependency_overrides[get_cache_service] = override_cache
        app.dependency_overrides[get_search_service] = override_search
        app.dependency_overrides[get_classifier_service] = override_classifier

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/classify/0000180d-0000-1000-8000-00805f9b34fb"
                )

            assert response.status_code == 200
            data = response.json()
            assert data["uuid"] == "0000180d-0000-1000-8000-00805f9b34fb"
            assert data["cached"] is False

            # Verify orchestration flow
            mock_cache_service.get_classification.assert_called_once()
            mock_search_service.search_uuid.assert_called_once()
            mock_classifier_service.classify.assert_called_once()
            mock_cache_service.save_classification.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_classify_invalid_uuid_returns_400(self) -> None:
        """Test that invalid UUID returns 400 error."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/classify/invalid-uuid")

        assert response.status_code == 400
        data = response.json()
        assert "Invalid UUID format" in data["detail"]

    async def test_classify_uuid_without_hyphens(
        self,
        sample_classification_response: ClassificationResponse,
    ) -> None:
        """Test that UUID without hyphens is accepted and normalized."""
        mock_cache_service = AsyncMock(spec=CacheService)
        mock_cache_service.get_classification = AsyncMock(
            return_value=sample_classification_response
        )

        async def override_cache() -> AsyncGenerator[CacheService, None]:
            yield mock_cache_service

        app.dependency_overrides[get_cache_service] = override_cache

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                # UUID without hyphens
                response = await client.get(
                    "/classify/0000180d00001000800000805f9b34fb"
                )

            assert response.status_code == 200
            data = response.json()
            # Response should have normalized UUID with hyphens
            assert data["uuid"] == "0000180d-0000-1000-8000-00805f9b34fb"
        finally:
            app.dependency_overrides.clear()

    async def test_classify_uuid_uppercase_normalized(
        self,
        sample_classification_response: ClassificationResponse,
    ) -> None:
        """Test that uppercase UUID is normalized to lowercase."""
        mock_cache_service = AsyncMock(spec=CacheService)
        mock_cache_service.get_classification = AsyncMock(
            return_value=sample_classification_response
        )

        async def override_cache() -> AsyncGenerator[CacheService, None]:
            yield mock_cache_service

        app.dependency_overrides[get_cache_service] = override_cache

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                # Uppercase UUID
                response = await client.get(
                    "/classify/0000180D-0000-1000-8000-00805F9B34FB"
                )

            assert response.status_code == 200
            data = response.json()
            # Response should have normalized lowercase UUID
            assert data["uuid"] == "0000180d-0000-1000-8000-00805f9b34fb"
        finally:
            app.dependency_overrides.clear()


class TestClassifyPostEndpoint:
    """Tests for POST /classify endpoint."""

    async def test_classify_post_valid_uuid(
        self,
        sample_classification_response: ClassificationResponse,
    ) -> None:
        """Test POST endpoint with valid UUID in body."""
        mock_cache_service = AsyncMock(spec=CacheService)
        mock_cache_service.get_classification = AsyncMock(
            return_value=sample_classification_response
        )

        async def override_cache() -> AsyncGenerator[CacheService, None]:
            yield mock_cache_service

        app.dependency_overrides[get_cache_service] = override_cache

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/classify",
                    json={"uuid": "0000180d-0000-1000-8000-00805f9b34fb"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["uuid"] == "0000180d-0000-1000-8000-00805f9b34fb"
            assert data["cached"] is True
        finally:
            app.dependency_overrides.clear()

    async def test_classify_post_invalid_uuid_returns_422(self) -> None:
        """Test POST endpoint returns 422 for invalid UUID in body."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/classify",
                json={"uuid": "not-a-valid-uuid"},
            )

        # Pydantic validation returns 422 for body validation errors
        assert response.status_code == 422

    async def test_classify_post_missing_uuid_returns_422(self) -> None:
        """Test POST endpoint returns 422 when UUID is missing."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/classify",
                json={},
            )

        assert response.status_code == 422


class TestSearchFailureHandling:
    """Tests for handling search service failures."""

    async def test_search_failure_returns_partial_result(self) -> None:
        """Test that search failure still returns a classification (Unknown)."""
        # Create an Unknown classification response
        unknown_response = ClassificationResponse(
            uuid="12345678-1234-1234-1234-123456789abc",
            name="Unknown",
            type=ClassificationType.UNKNOWN,
            description="Unable to identify this UUID",
            sources=[],
            confidence=ConfidenceLevel.LOW,
            cached=False,
            searched_at=datetime.now(UTC),
        )

        unknown_create = ClassificationCreate(
            uuid="12345678-1234-1234-1234-123456789abc",
            name="Unknown",
            type=ClassificationType.UNKNOWN,
            description="Unable to identify this UUID",
            sources=[],
            confidence=ConfidenceLevel.LOW,
            searched_at=datetime.now(UTC),
        )

        # Create mock services
        mock_cache_service = AsyncMock(spec=CacheService)
        mock_cache_service.get_classification = AsyncMock(return_value=None)
        mock_cache_service.save_classification = AsyncMock(return_value=unknown_response)

        mock_search_service = AsyncMock(spec=SearchService)
        mock_search_service.search_uuid = AsyncMock(return_value=[])

        mock_classifier_service = AsyncMock(spec=ClassifierService)
        mock_classifier_service.classify = AsyncMock(return_value=unknown_create)

        async def override_cache() -> AsyncGenerator[CacheService, None]:
            yield mock_cache_service

        async def override_search() -> AsyncGenerator[SearchService, None]:
            yield mock_search_service

        async def override_classifier() -> AsyncGenerator[ClassifierService, None]:
            yield mock_classifier_service

        app.dependency_overrides[get_cache_service] = override_cache
        app.dependency_overrides[get_search_service] = override_search
        app.dependency_overrides[get_classifier_service] = override_classifier

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/classify/12345678-1234-1234-1234-123456789abc"
                )

            assert response.status_code == 200
            data = response.json()
            assert data["type"] == "Unknown"
            assert data["confidence"] == "low"
        finally:
            app.dependency_overrides.clear()


class TestRootEndpoint:
    """Tests for the root endpoint."""

    async def test_root_returns_info(self) -> None:
        """Test root endpoint returns API info."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "UUID Classifier" in data["message"]
        assert data["version"] == __version__
        assert data["docs"] == "/docs"
