"""Integration test fixtures.

Provides database setup, async sessions, and test client configuration
for integration tests that interact with a real database.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from uuid_classifier.api.dependencies import (
    get_cache_service,
    get_search_service,
)
from uuid_classifier.db.models import Base
from uuid_classifier.main import app
from uuid_classifier.schemas.classification import SearchResult
from uuid_classifier.services.cache_service import CacheService
from uuid_classifier.services.search_service import SearchService

# Use SQLite for integration tests (no separate PostgreSQL needed)
# In production-like environment, use:
# TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/uuidy_test"
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Return the default event loop policy for the session."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a test database engine.

    Creates an in-memory SQLite database for testing.
    Tables are created before tests and dropped after.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session_factory(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create session factory bound to test engine."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
async def async_session(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Create an async session for testing.

    Each test gets its own session that is rolled back after the test.
    This ensures test isolation without needing to recreate tables.
    """
    async with test_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_search_results() -> list[SearchResult]:
    """Standard mock search results for testing."""
    return [
        SearchResult(
            title="Heart Rate Service - Bluetooth SIG",
            url="https://www.bluetooth.com/specifications/gatt/services/",
            snippet="The Heart Rate Service exposes heart rate data. UUID: 0x180D",
            position=1,
        ),
        SearchResult(
            title="BLE Heart Rate Service Tutorial",
            url="https://learn.example.com/ble-hrs",
            snippet="The Heart Rate Service (0x180D) is a standardized BLE service.",
            position=2,
        ),
        SearchResult(
            title="Bluetooth GATT Services Reference",
            url="https://developer.bluetooth.org/gatt",
            snippet="Heart Rate Service UUID: 0000180d-0000-1000-8000-00805f9b34fb",
            position=3,
        ),
    ]


@pytest.fixture
def mock_search_service(mock_search_results: list[SearchResult]) -> AsyncMock:
    """Create a mock SearchService that returns predefined results."""
    mock = AsyncMock(spec=SearchService)
    mock.search_uuid = AsyncMock(return_value=mock_search_results)
    return mock


@pytest.fixture
def mock_search_service_empty() -> AsyncMock:
    """Create a mock SearchService that returns no results."""
    mock = AsyncMock(spec=SearchService)
    mock.search_uuid = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_search_service_error() -> AsyncMock:
    """Create a mock SearchService that raises an exception."""
    mock = AsyncMock(spec=SearchService)
    mock.search_uuid = AsyncMock(side_effect=Exception("Search API error"))
    return mock


@pytest.fixture
async def test_cache_service(async_session: AsyncSession) -> CacheService:
    """Create a CacheService instance for testing."""
    return CacheService(async_session)


@pytest.fixture
async def integration_client(
    async_session: AsyncSession,
    mock_search_service: AsyncMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an HTTP client for integration testing.

    This client:
    - Uses a real database session (in-memory SQLite)
    - Mocks the search service to avoid real API calls
    - Uses the real classifier service
    """
    # Create cache service with test session
    cache_service = CacheService(async_session)

    async def override_cache() -> AsyncGenerator[CacheService, None]:
        yield cache_service

    async def override_search() -> AsyncGenerator[SearchService, None]:
        yield mock_search_service

    # Override FastAPI dependencies
    app.dependency_overrides[get_cache_service] = override_cache
    app.dependency_overrides[get_search_service] = override_search

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
async def integration_client_no_results(
    async_session: AsyncSession,
    mock_search_service_empty: AsyncMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Create client for testing with empty search results."""
    cache_service = CacheService(async_session)

    async def override_cache() -> AsyncGenerator[CacheService, None]:
        yield cache_service

    async def override_search() -> AsyncGenerator[SearchService, None]:
        yield mock_search_service_empty

    app.dependency_overrides[get_cache_service] = override_cache
    app.dependency_overrides[get_search_service] = override_search

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def sample_uuid() -> str:
    """Standard test UUID (Heart Rate Service)."""
    return "0000180d-0000-1000-8000-00805f9b34fb"


@pytest.fixture
def unknown_uuid() -> str:
    """UUID that will return no search results."""
    return "12345678-1234-1234-1234-123456789abc"


@pytest.fixture
def vendor_uuid() -> str:
    """Vendor-specific UUID (Nordic UART Service)."""
    return "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
