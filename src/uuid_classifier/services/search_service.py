"""Search service for Google/SerpAPI UUID information lookup.

This service handles web searches via SerpAPI to find information about
unknown UUIDs, particularly for Bluetooth Low Energy services.
"""

import asyncio
import logging
from typing import Any

from serpapi import GoogleSearch

from uuid_classifier.core.config import Settings
from uuid_classifier.core.config import settings as default_settings
from uuid_classifier.schemas.classification import SearchResult

logger = logging.getLogger(__name__)


class SearchServiceError(Exception):
    """Exception raised for search service errors."""

    pass


class SearchService:
    """Service for searching Google via SerpAPI for UUID information.

    This service queries Google for information about UUIDs, with emphasis
    on Bluetooth Low Energy service identification. Results are parsed
    into structured SearchResult objects.

    Attributes:
        api_key: SerpAPI API key for authentication.
        max_results: Maximum number of search results to return.
        timeout: Timeout in seconds for search requests.
    """

    # Default search query template
    SEARCH_QUERY_TEMPLATE = '"{uuid}" bluetooth OR BLE OR service OR GATT OR beacon'

    def __init__(
        self,
        settings: Settings | None = None,
        max_results: int = 10,
        timeout: int = 10,
    ) -> None:
        """Initialize the search service.

        Args:
            settings: Application settings containing SERPAPI_KEY.
                     Uses default settings if not provided.
            max_results: Maximum number of results to return (default: 10).
            timeout: Request timeout in seconds (default: 10).
        """
        config = settings or default_settings
        self.api_key = config.serpapi_key
        self.max_results = max_results
        self.timeout = timeout

        if self.api_key:
            logger.info("SearchService initialized with API key")
        else:
            logger.warning(
                "SearchService initialized without API key - searches will be disabled"
            )

    async def search_uuid(self, uuid: str) -> list[SearchResult]:
        """Search Google for information about a UUID.

        Args:
            uuid: The UUID to search for.

        Returns:
            List of SearchResult objects from the search.
            Returns empty list on errors or when no API key is configured.
        """
        if not self.api_key:
            logger.warning("Cannot search: SERPAPI_KEY not configured")
            return []

        query = self.build_search_query(uuid)
        logger.info("Searching for UUID: %s", uuid)
        logger.debug("Search query: %s", query)

        try:
            response = await self._execute_search(query)
            results = self._parse_results(response)

            # Limit results to max_results
            limited_results = results[: self.max_results]

            logger.info(
                "Search completed: %d results found, returning %d",
                len(results),
                len(limited_results),
            )
            return limited_results

        except SearchServiceError as e:
            logger.error("Search service error: %s", e)
            return []
        except TimeoutError:
            logger.error("Search timed out after %d seconds", self.timeout)
            return []
        except Exception as e:
            logger.exception("Unexpected error during search: %s", e)
            return []

    def build_search_query(self, uuid: str) -> str:
        """Build a search query for the given UUID.

        Args:
            uuid: The UUID to include in the search query.

        Returns:
            Formatted search query string.
        """
        return self.SEARCH_QUERY_TEMPLATE.format(uuid=uuid)

    async def _execute_search(self, query: str) -> dict[str, Any]:
        """Execute the search via SerpAPI.

        This runs the synchronous SerpAPI client in a thread pool to avoid
        blocking the async event loop.

        Args:
            query: The search query string.

        Returns:
            Dictionary containing the SerpAPI response.

        Raises:
            SearchServiceError: If the API call fails.
        """
        params = {
            "engine": "google",
            "q": query,
            "api_key": self.api_key,
            "num": self.max_results,  # Request slightly more to account for filtering
        }

        def _sync_search() -> dict[str, Any]:
            """Synchronous search function to run in thread pool."""
            search = GoogleSearch(params)
            result: dict[str, Any] = search.get_dict()
            return result

        try:
            # Run sync SerpAPI client in thread pool with timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(_sync_search),
                timeout=self.timeout,
            )
            return result
        except TimeoutError:
            raise
        except Exception as e:
            raise SearchServiceError(f"SerpAPI request failed: {e}") from e

    def _parse_results(self, response: dict[str, Any]) -> list[SearchResult]:
        """Parse SerpAPI response into SearchResult objects.

        Only organic search results are parsed - ads and other result types
        are filtered out.

        Args:
            response: Raw SerpAPI response dictionary.

        Returns:
            List of SearchResult objects parsed from organic results.
        """
        organic_results = response.get("organic_results", [])

        results: list[SearchResult] = []
        for item in organic_results:
            try:
                result = SearchResult(
                    title=item["title"],
                    url=item["link"],
                    snippet=item.get("snippet", ""),
                    position=item["position"],
                )
                results.append(result)
            except (KeyError, ValueError) as e:
                logger.warning("Failed to parse search result: %s - %s", item, e)
                continue

        return results


# Dependency injection helper for FastAPI
def get_search_service() -> SearchService:
    """Get a SearchService instance for dependency injection.

    Returns:
        SearchService instance configured with default settings.
    """
    return SearchService()


async def search_service_dependency() -> SearchService:
    """Async dependency provider for SearchService.

    This is an async function that can be used with FastAPI's Depends().

    Returns:
        SearchService instance.
    """
    return SearchService()
