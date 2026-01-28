"""Cache service for UUID classification database operations.

This service provides CRUD operations for cached UUID classification records.
"""

import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from uuid_classifier.db.models import UUIDClassification, normalize_uuid
from uuid_classifier.schemas.classification import (
    ClassificationCreate,
    ClassificationResponse,
    ClassificationType,
    ConfidenceLevel,
    SourceInfo,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching UUID classification records in the database.

    This service handles all database operations for classification records,
    including retrieval, storage, and existence checks.

    Attributes:
        session: The async SQLAlchemy session for database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the cache service with a database session.

        Args:
            session: An async SQLAlchemy session.
        """
        self._session = session

    async def get_classification(self, uuid: str) -> ClassificationResponse | None:
        """Fetch a cached classification record by UUID.

        Args:
            uuid: The UUID to look up (will be normalized).

        Returns:
            ClassificationResponse if found, None otherwise.
        """
        try:
            normalized = normalize_uuid(uuid)
        except ValueError:
            logger.warning("Invalid UUID format: %s", uuid)
            return None

        logger.debug("Looking up classification for UUID: %s", normalized)

        stmt = select(UUIDClassification).where(UUIDClassification.uuid == normalized)
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            logger.debug("Cache miss for UUID: %s", normalized)
            return None

        logger.debug("Cache hit for UUID: %s", normalized)
        return self._to_response(record, cached=True)

    async def save_classification(
        self, data: ClassificationCreate
    ) -> ClassificationResponse:
        """Save a new classification record to the database.

        Args:
            data: The classification data to save.

        Returns:
            ClassificationResponse representing the saved record.

        Raises:
            ValueError: If a record with this UUID already exists.
        """
        # UUID is already normalized by the Pydantic validator,
        # but we normalize again for safety
        normalized_uuid = normalize_uuid(data.uuid)

        logger.info("Saving classification for UUID: %s", normalized_uuid)

        # Serialize sources to JSON-compatible format
        sources_json = [s.model_dump(mode="json") for s in data.sources]

        record = UUIDClassification(
            uuid=normalized_uuid,
            name=data.name,
            type=data.type.value,
            description=data.description,
            sources=sources_json,
            confidence=data.confidence.value,
            searched_at=data.searched_at,
        )

        try:
            self._session.add(record)
            await self._session.flush()
            await self._session.refresh(record)
            logger.info(
                "Successfully saved classification for UUID: %s", normalized_uuid
            )
            return self._to_response(record, cached=False)
        except IntegrityError as e:
            await self._session.rollback()
            logger.warning(
                "Duplicate UUID detected: %s. Error: %s", normalized_uuid, str(e)
            )
            raise ValueError(
                f"Classification for UUID {normalized_uuid} already exists"
            ) from e

    async def exists(self, uuid: str) -> bool:
        """Check if a UUID exists in the cache.

        This is a quick existence check without loading the full record.

        Args:
            uuid: The UUID to check (will be normalized).

        Returns:
            True if the UUID exists in cache, False otherwise.
        """
        try:
            normalized = normalize_uuid(uuid)
        except ValueError:
            logger.warning("Invalid UUID format for exists check: %s", uuid)
            return False

        stmt = select(UUIDClassification.uuid).where(
            UUIDClassification.uuid == normalized
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _to_response(
        self, record: UUIDClassification, *, cached: bool
    ) -> ClassificationResponse:
        """Convert a database record to a response model.

        Args:
            record: The database record to convert.
            cached: Whether this result was retrieved from cache.

        Returns:
            ClassificationResponse representing the record.
        """
        # Parse sources from JSON
        sources = [
            SourceInfo(
                title=s["title"],
                url=s["url"],
                snippet=s["snippet"],
            )
            for s in record.sources
        ]

        return ClassificationResponse(
            uuid=record.uuid,
            name=record.name,
            type=ClassificationType(record.type),
            description=record.description or "",
            sources=sources,
            confidence=ConfidenceLevel(record.confidence),
            cached=cached,
            searched_at=record.searched_at,
        )


async def get_cache_service(
    session: AsyncSession,
) -> AsyncGenerator[CacheService, None]:
    """FastAPI dependency that provides a CacheService instance.

    This dependency should be used with Depends() in FastAPI routes.
    The session parameter will be injected by FastAPI when used with
    Depends(get_db_session).

    Args:
        session: The database session (injected by FastAPI).

    Yields:
        CacheService instance configured with the session.

    Example:
        @app.get("/classify/{uuid}")
        async def classify(
            uuid: str,
            cache: CacheService = Depends(get_cache_service),
        ):
            return await cache.get_classification(uuid)
    """
    yield CacheService(session)


def cache_service_dependency(
    session: AsyncSession,
) -> CacheService:
    """FastAPI dependency that provides a CacheService instance.

    Use with: Depends(cache_service_dependency)
    Combined with session dependency via sub-dependency.

    Args:
        session: The database session from get_db_session dependency.

    Returns:
        CacheService instance configured with the session.

    Example:
        from fastapi import Depends
        from uuid_classifier.db.database import get_db_session
        from uuid_classifier.services.cache_service import cache_service_dependency

        @app.get("/classify/{uuid}")
        async def classify(
            uuid: str,
            session: AsyncSession = Depends(get_db_session),
            cache: CacheService = Depends(cache_service_dependency),
        ):
            return await cache.get_classification(uuid)
    """
    return CacheService(session)
