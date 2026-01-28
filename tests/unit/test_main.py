"""Unit tests for the main FastAPI application."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient) -> None:
    """Test root endpoint returns API info."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "UUID Classifier" in data["message"]
    assert "version" in data
    assert data["docs"] == "/docs"


@pytest.mark.asyncio
async def test_db_check(async_client: AsyncClient) -> None:
    """Test database check endpoint returns connected status."""
    response = await async_client.get("/db-check")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
