"""Unit tests for SearchService - Google/SerpAPI integration."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from uuid_classifier.core.config import Settings
from uuid_classifier.schemas.classification import SearchResult
from uuid_classifier.services.search_service import (
    SearchService,
    SearchServiceError,
)


@pytest.fixture
def search_fixtures() -> dict[str, Any]:
    """Load search response fixtures."""
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "search_responses.json"
    with open(fixtures_path) as f:
        data: dict[str, Any] = json.load(f)
        return data


@pytest.fixture
def mock_settings_with_key() -> Settings:
    """Create settings with a mock SerpAPI key."""
    return Settings(serpapi_key="test-api-key-12345")


@pytest.fixture
def mock_settings_without_key() -> Settings:
    """Create settings without a SerpAPI key."""
    return Settings(serpapi_key=None)


@pytest.fixture
def search_service(mock_settings_with_key: Settings) -> SearchService:
    """Create a SearchService with mocked settings."""
    return SearchService(settings=mock_settings_with_key)


class TestSearchServiceInit:
    """Tests for SearchService initialization."""

    def test_init_with_api_key(self, mock_settings_with_key: Settings) -> None:
        """Service initializes with SERPAPI_KEY from settings."""
        service = SearchService(settings=mock_settings_with_key)
        assert service.api_key == "test-api-key-12345"
        assert service.max_results == 10
        assert service.timeout == 10

    def test_init_without_api_key(self, mock_settings_without_key: Settings) -> None:
        """Service initializes without API key - should handle gracefully."""
        service = SearchService(settings=mock_settings_without_key)
        assert service.api_key is None

    def test_init_with_custom_config(self, mock_settings_with_key: Settings) -> None:
        """Service accepts custom max_results and timeout."""
        service = SearchService(
            settings=mock_settings_with_key,
            max_results=5,
            timeout=20,
        )
        assert service.max_results == 5
        assert service.timeout == 20


class TestSearchUUID:
    """Tests for search_uuid method."""

    @pytest.mark.asyncio
    async def test_search_returns_results(
        self,
        search_service: SearchService,
        search_fixtures: dict[str, Any],
    ) -> None:
        """search_uuid returns list of SearchResult objects."""
        mock_response = search_fixtures["heart_rate_service_response"]

        with patch.object(
            search_service, "_execute_search", return_value=mock_response
        ):
            results = await search_service.search_uuid(
                "0000180d-0000-1000-8000-00805f9b34fb"
            )

        assert len(results) == 5
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].title == "Heart Rate Service - Bluetooth SIG"
        assert (
            results[0].url == "https://www.bluetooth.com/specifications/gatt/services/"
        )
        assert "Heart Rate Service" in results[0].snippet
        assert results[0].position == 1

    @pytest.mark.asyncio
    async def test_search_handles_empty_results(
        self,
        search_service: SearchService,
        search_fixtures: dict[str, Any],
    ) -> None:
        """search_uuid returns empty list when no results found."""
        mock_response = search_fixtures["empty_results_response"]

        with patch.object(
            search_service, "_execute_search", return_value=mock_response
        ):
            results = await search_service.search_uuid(
                "12345678-1234-1234-1234-123456789abc"
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_handles_api_error(
        self,
        search_service: SearchService,
    ) -> None:
        """search_uuid handles API errors gracefully (returns empty list + logs)."""
        with patch.object(
            search_service,
            "_execute_search",
            side_effect=SearchServiceError("API Error"),
        ):
            results = await search_service.search_uuid(
                "0000180d-0000-1000-8000-00805f9b34fb"
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_search_handles_missing_key(
        self,
        mock_settings_without_key: Settings,
    ) -> None:
        """search_uuid handles missing API key gracefully."""
        service = SearchService(settings=mock_settings_without_key)
        results = await service.search_uuid("0000180d-0000-1000-8000-00805f9b34fb")

        # Should return empty list when no API key configured
        assert results == []

    @pytest.mark.asyncio
    async def test_search_respects_max_results(
        self,
        mock_settings_with_key: Settings,
        search_fixtures: dict[str, Any],
    ) -> None:
        """search_uuid respects configured max_results limit."""
        service = SearchService(settings=mock_settings_with_key, max_results=5)
        mock_response = search_fixtures["many_results_response"]

        with patch.object(service, "_execute_search", return_value=mock_response):
            results = await service.search_uuid("0000180d-0000-1000-8000-00805f9b34fb")

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_filters_out_ads(
        self,
        search_service: SearchService,
        search_fixtures: dict[str, Any],
    ) -> None:
        """search_uuid filters out ad results if present."""
        mock_response = search_fixtures["response_with_ads"]

        with patch.object(
            search_service, "_execute_search", return_value=mock_response
        ):
            results = await search_service.search_uuid(
                "0000180d-0000-1000-8000-00805f9b34fb"
            )

        # Should only have organic result, not ads
        assert len(results) == 1
        assert "Shop Now" not in results[0].title

    @pytest.mark.asyncio
    async def test_search_handles_timeout(
        self,
        search_service: SearchService,
    ) -> None:
        """search_uuid handles timeout gracefully."""
        with patch.object(
            search_service,
            "_execute_search",
            side_effect=TimeoutError(),
        ):
            results = await search_service.search_uuid(
                "0000180d-0000-1000-8000-00805f9b34fb"
            )

        assert results == []


class TestSearchQueryBuilding:
    """Tests for search query construction."""

    def test_build_search_query(self, search_service: SearchService) -> None:
        """Verify search query format includes UUID and BLE context."""
        uuid = "0000180d-0000-1000-8000-00805f9b34fb"
        query = search_service.build_search_query(uuid)

        assert uuid in query
        assert "bluetooth" in query.lower() or "BLE" in query
        assert "GATT" in query or "service" in query.lower()


class TestExecuteSearch:
    """Tests for the internal _execute_search method."""

    @pytest.mark.asyncio
    async def test_execute_search_calls_serpapi(
        self,
        search_service: SearchService,
    ) -> None:
        """_execute_search calls SerpAPI with correct parameters."""
        mock_search_instance = MagicMock()
        mock_search_instance.get_dict.return_value = {"organic_results": []}

        with patch(
            "uuid_classifier.services.search_service.GoogleSearch",
            return_value=mock_search_instance,
        ):
            await search_service._execute_search("test query")

        # Verify GoogleSearch was called with correct params
        mock_search_instance.get_dict.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_search_runs_in_thread_pool(
        self,
        search_service: SearchService,
    ) -> None:
        """_execute_search runs SerpAPI in thread pool (since it's sync)."""
        mock_search_instance = MagicMock()
        mock_search_instance.get_dict.return_value = {"organic_results": []}

        with (
            patch(
                "uuid_classifier.services.search_service.GoogleSearch",
                return_value=mock_search_instance,
            ),
            patch("asyncio.to_thread") as mock_to_thread,
        ):
            mock_to_thread.return_value = {"organic_results": []}
            await search_service._execute_search("test query")

            mock_to_thread.assert_called_once()


class TestSearchResultParsing:
    """Tests for parsing SerpAPI responses into SearchResult objects."""

    def test_parse_organic_results(
        self,
        search_service: SearchService,
        search_fixtures: dict[str, Any],
    ) -> None:
        """Parse organic results from SerpAPI response."""
        response = search_fixtures["heart_rate_service_response"]
        results = search_service._parse_results(response)

        assert len(results) == 5
        first = results[0]
        assert first.title == "Heart Rate Service - Bluetooth SIG"
        assert first.url == "https://www.bluetooth.com/specifications/gatt/services/"
        assert first.position == 1

    def test_parse_results_handles_missing_snippet(
        self,
        search_service: SearchService,
    ) -> None:
        """Parse results when snippet is missing."""
        response: dict[str, Any] = {
            "organic_results": [
                {
                    "position": 1,
                    "title": "Test Title",
                    "link": "https://example.com",
                    # No snippet field
                }
            ]
        }
        results = search_service._parse_results(response)

        assert len(results) == 1
        assert results[0].snippet == ""

    def test_parse_results_handles_empty_organic_results(
        self,
        search_service: SearchService,
    ) -> None:
        """Parse results when organic_results is empty."""
        response: dict[str, Any] = {"organic_results": []}
        results = search_service._parse_results(response)

        assert results == []

    def test_parse_results_handles_missing_organic_results_key(
        self,
        search_service: SearchService,
    ) -> None:
        """Parse results when organic_results key is missing."""
        response: dict[str, Any] = {"some_other_key": []}
        results = search_service._parse_results(response)

        assert results == []
