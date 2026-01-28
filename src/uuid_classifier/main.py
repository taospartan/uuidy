"""FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from uuid_classifier import __version__
from uuid_classifier.api.router import router as api_router
from uuid_classifier.db.database import create_tables, get_db_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown tasks."""
    # Startup: create database tables
    logger.info("Starting UUID Classifier API v%s", __version__)
    await create_tables()
    logger.info("Database tables created/verified")
    yield
    # Shutdown: cleanup if needed
    logger.info("Shutting down UUID Classifier API")


app = FastAPI(
    title="UUID Classifier",
    description="API service for identifying unknown UUIDs, especially Bluetooth Low Energy service UUIDs",
    version=__version__,
    lifespan=lifespan,
)

# Include the API router
app.include_router(api_router)

# Type alias for database session dependency
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with basic info."""
    return {"message": "UUID Classifier API", "version": __version__, "docs": "/docs"}


@app.get("/db-check")
async def db_check(session: DbSession) -> dict[str, str]:
    """Database connection check endpoint."""
    # Simple query to verify connection works
    await session.execute(__import__("sqlalchemy").text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
