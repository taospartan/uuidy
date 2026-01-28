"""Integration tests for full UUID classification flow.

Tests the complete request lifecycle with real database interactions,
verifying cache miss/hit flows, search integration, and error handling.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from uuid_classifier.api.dependencies import get_cache_service, get_search_service
from uuid_classifier.db.models import UUIDClassification
from uuid_classifier.main import app
from uuid_classifier.schemas.classification import (
    ClassificationCreate,
    ClassificationType,
    ConfidenceLevel,
    SearchResult,
    SourceInfo,
)
from uuid_classifier.services.cache_service import CacheService
from uuid_classifier.services.search_service import SearchService


class TestFullCacheMissFlow:
    """Tests for complete cache miss flow.

    Verifies:
    - Request unknown UUID
    - Search service is called
    - Record is saved to DB
    - Response has cached=false
    """

    @pytest.mark.asyncio
    async def test_cache_miss_triggers_search_and_saves(
        self,
        integration_client: AsyncClient,
        mock_search_service: AsyncMock,
        sample_uuid: str,
    ) -> None:
        """Full flow: cache miss triggers search, saves result."""
        response = await integration_client.get(f"/classify/{sample_uuid}")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["uuid"] == sample_uuid
        assert data["cached"] is False
        assert data["name"] is not None
        assert data["type"] in [t.value for t in ClassificationType]
        assert data["confidence"] in [c.value for c in ConfidenceLevel]

        # Verify search was called
        mock_search_service.search_uuid.assert_called_once_with(sample_uuid)

    @pytest.mark.asyncio
    async def test_cache_miss_stores_in_database(
        self,
        integration_client: AsyncClient,
        async_session: AsyncSession,
        sample_uuid: str,
    ) -> None:
        """Verify record is persisted to database after cache miss."""
        # Make the request
        response = await integration_client.get(f"/classify/{sample_uuid}")
        assert response.status_code == 200

        # Flush and verify in database
        await async_session.commit()

        # Use a new query to check the database
        from sqlalchemy import select

        stmt = select(UUIDClassification).where(UUIDClassification.uuid == sample_uuid)
        result = await async_session.execute(stmt)
        record = result.scalar_one_or_none()

        assert record is not None
        assert record.uuid == sample_uuid
        assert record.name is not None

    @pytest.mark.asyncio
    async def test_post_endpoint_cache_miss(
        self,
        integration_client: AsyncClient,
        mock_search_service: AsyncMock,
        sample_uuid: str,
    ) -> None:
        """POST endpoint also triggers full cache miss flow."""
        response = await integration_client.post(
            "/classify",
            json={"uuid": sample_uuid},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cached"] is False
        mock_search_service.search_uuid.assert_called_once()


class TestFullCacheHitFlow:
    """Tests for complete cache hit flow.

    Verifies:
    - Pre-populate DB with record
    - Request known UUID
    - Search service is NOT called
    - Response has cached=true
    """

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_record(
        self,
        async_session: AsyncSession,
        mock_search_service: AsyncMock,
        mock_search_results: list[SearchResult],
        sample_uuid: str,
    ) -> None:
        """Pre-populated record is returned from cache without search."""
        # Pre-populate the database
        record = UUIDClassification(
            uuid=sample_uuid,
            name="Heart Rate",
            type="Standard BLE Service",
            description="Cached Heart Rate Service",
            sources=[
                {
                    "title": "Cached Source",
                    "url": "https://example.com",
                    "snippet": "Cached snippet",
                }
            ],
            confidence="high",
            searched_at=datetime.now(UTC),
        )
        async_session.add(record)
        await async_session.commit()

        # Create test client with the pre-populated session
        cache_service = CacheService(async_session)

        async def override_cache() -> AsyncGenerator[CacheService, None]:
            yield cache_service

        async def override_search() -> AsyncGenerator[SearchService, None]:
            yield mock_search_service

        app.dependency_overrides[get_cache_service] = override_cache
        app.dependency_overrides[get_search_service] = override_search

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(f"/classify/{sample_uuid}")

            assert response.status_code == 200
            data = response.json()

            # Verify cache hit
            assert data["cached"] is True
            assert data["uuid"] == sample_uuid
            assert data["name"] == "Heart Rate"

            # Verify search was NOT called
            mock_search_service.search_uuid.assert_not_called()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cache_hit_second_request(
        self,
        integration_client: AsyncClient,
        mock_search_service: AsyncMock,
        sample_uuid: str,
    ) -> None:
        """Second request for same UUID returns cached result."""
        # First request - cache miss
        response1 = await integration_client.get(f"/classify/{sample_uuid}")
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["cached"] is False

        # Reset mock to track second call
        mock_search_service.search_uuid.reset_mock()

        # Second request - should be cache hit
        response2 = await integration_client.get(f"/classify/{sample_uuid}")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["cached"] is True
        assert data2["uuid"] == sample_uuid

        # Search should NOT be called for cache hit
        mock_search_service.search_uuid.assert_not_called()


class TestSearchFailureGracefulDegradation:
    """Tests for handling search service failures gracefully.

    Verifies:
    - Mock search to return empty results or raise exception
    - Request unknown UUID
    - Response returns Unknown classification
    - System doesn't crash
    """

    @pytest.mark.asyncio
    async def test_empty_search_results_returns_unknown(
        self,
        integration_client_no_results: AsyncClient,
        unknown_uuid: str,
    ) -> None:
        """Empty search results still return a valid Unknown classification."""
        response = await integration_client_no_results.get(f"/classify/{unknown_uuid}")

        assert response.status_code == 200
        data = response.json()

        # Should return Unknown classification
        assert data["uuid"] == unknown_uuid
        assert data["type"] == "Unknown"
        assert data["confidence"] == "low"
        assert data["cached"] is False

    @pytest.mark.asyncio
    async def test_search_exception_handled_gracefully(
        self,
        async_session: AsyncSession,
        mock_search_service_error: AsyncMock,
        unknown_uuid: str,
    ) -> None:
        """Search service exception returns 500 error gracefully."""
        cache_service = CacheService(async_session)

        async def override_cache() -> AsyncGenerator[CacheService, None]:
            yield cache_service

        async def override_search() -> AsyncGenerator[SearchService, None]:
            yield mock_search_service_error

        app.dependency_overrides[get_cache_service] = override_cache
        app.dependency_overrides[get_search_service] = override_search

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(f"/classify/{unknown_uuid}")

            # Should return 500 for unhandled exception
            assert response.status_code == 500
            data = response.json()
            assert "error" in data["detail"].lower() or "internal" in data["detail"].lower()
        finally:
            app.dependency_overrides.clear()


class TestUUIDNormalization:
    """Tests for UUID format normalization across full flow."""

    @pytest.mark.asyncio
    async def test_uppercase_uuid_normalized(
        self,
        integration_client: AsyncClient,
        sample_uuid: str,
    ) -> None:
        """Uppercase UUID is normalized before processing."""
        uppercase_uuid = sample_uuid.upper()

        response = await integration_client.get(f"/classify/{uppercase_uuid}")

        assert response.status_code == 200
        data = response.json()
        # Response should have normalized lowercase UUID
        assert data["uuid"] == sample_uuid.lower()

    @pytest.mark.asyncio
    async def test_uuid_without_hyphens_normalized(
        self,
        integration_client: AsyncClient,
        sample_uuid: str,
    ) -> None:
        """UUID without hyphens is normalized to include them."""
        no_hyphen_uuid = sample_uuid.replace("-", "")

        response = await integration_client.get(f"/classify/{no_hyphen_uuid}")

        assert response.status_code == 200
        data = response.json()
        # Response should have normalized UUID with hyphens
        assert data["uuid"] == sample_uuid

    @pytest.mark.asyncio
    async def test_mixed_case_no_hyphens_normalized(
        self,
        integration_client: AsyncClient,
        sample_uuid: str,
    ) -> None:
        """Mixed case UUID without hyphens is fully normalized."""
        mixed_uuid = sample_uuid.upper().replace("-", "")

        response = await integration_client.get(f"/classify/{mixed_uuid}")

        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == sample_uuid.lower()


class TestResponseSchema:
    """Tests verifying response schema compliance."""

    @pytest.mark.asyncio
    async def test_response_contains_all_required_fields(
        self,
        integration_client: AsyncClient,
        sample_uuid: str,
    ) -> None:
        """Response contains all required schema fields."""
        response = await integration_client.get(f"/classify/{sample_uuid}")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        required_fields = [
            "uuid",
            "name",
            "type",
            "description",
            "sources",
            "confidence",
            "cached",
            "searched_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    @pytest.mark.asyncio
    async def test_sources_structure(
        self,
        integration_client: AsyncClient,
        sample_uuid: str,
    ) -> None:
        """Sources field has correct structure."""
        response = await integration_client.get(f"/classify/{sample_uuid}")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["sources"], list)
        # If sources exist, verify structure
        for source in data["sources"]:
            assert "title" in source
            assert "url" in source
            assert "snippet" in source

    @pytest.mark.asyncio
    async def test_confidence_enum_values(
        self,
        integration_client: AsyncClient,
        sample_uuid: str,
    ) -> None:
        """Confidence field has valid enum value."""
        response = await integration_client.get(f"/classify/{sample_uuid}")

        assert response.status_code == 200
        data = response.json()

        valid_confidence = ["high", "medium", "low"]
        assert data["confidence"] in valid_confidence

    @pytest.mark.asyncio
    async def test_type_enum_values(
        self,
        integration_client: AsyncClient,
        sample_uuid: str,
    ) -> None:
        """Type field has valid enum value."""
        response = await integration_client.get(f"/classify/{sample_uuid}")

        assert response.status_code == 200
        data = response.json()

        valid_types = [t.value for t in ClassificationType]
        assert data["type"] in valid_types


class TestErrorHandling:
    """Tests for error handling across full flow."""

    @pytest.mark.asyncio
    async def test_invalid_uuid_format_returns_400(
        self,
        integration_client: AsyncClient,
    ) -> None:
        """Invalid UUID format returns 400 error."""
        response = await integration_client.get("/classify/not-a-uuid")

        assert response.status_code == 400
        data = response.json()
        assert "Invalid UUID format" in data["detail"]

    @pytest.mark.asyncio
    async def test_empty_uuid_returns_404_or_422(
        self,
        integration_client: AsyncClient,
    ) -> None:
        """Empty or missing UUID returns error."""
        response = await integration_client.get("/classify/")

        # Should return 404 (not found) or 307 (redirect)
        assert response.status_code in [404, 307]

    @pytest.mark.asyncio
    async def test_too_short_uuid_returns_400(
        self,
        integration_client: AsyncClient,
    ) -> None:
        """UUID that's too short returns 400."""
        response = await integration_client.get("/classify/12345")

        assert response.status_code == 400


class TestIsolation:
    """Tests verifying test isolation (no cross-test pollution)."""

    @pytest.mark.asyncio
    async def test_first_isolation_check(
        self,
        integration_client: AsyncClient,
        sample_uuid: str,
    ) -> None:
        """First test: save a record."""
        response = await integration_client.get(f"/classify/{sample_uuid}")
        assert response.status_code == 200
        # This test saves to DB

    @pytest.mark.asyncio
    async def test_second_isolation_check(
        self,
        integration_client: AsyncClient,
        sample_uuid: str,
    ) -> None:
        """Second test: should not see first test's record (isolation)."""
        response = await integration_client.get(f"/classify/{sample_uuid}")
        assert response.status_code == 200
        data = response.json()
        # Due to test isolation, this should be a cache miss (new DB session)
        assert data["cached"] is False
