"""FastAPI dependencies for service injection."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from uuid_classifier.db.database import get_db_session
from uuid_classifier.services.cache_service import CacheService
from uuid_classifier.services.classifier_service import ClassifierService
from uuid_classifier.services.search_service import SearchService


async def get_cache_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AsyncGenerator[CacheService, None]:
    """Dependency that provides a CacheService instance.

    Args:
        session: Database session from the session dependency.

    Yields:
        CacheService: Configured cache service instance.
    """
    yield CacheService(session)


async def get_search_service() -> AsyncGenerator[SearchService, None]:
    """Dependency that provides a SearchService instance.

    Yields:
        SearchService: Configured search service instance.
    """
    yield SearchService()


async def get_classifier_service() -> AsyncGenerator[ClassifierService, None]:
    """Dependency that provides a ClassifierService instance.

    Yields:
        ClassifierService: Configured classifier service instance.
    """
    yield ClassifierService()


# Type aliases for use in route handlers
CacheServiceDep = Annotated[CacheService, Depends(get_cache_service)]
SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
ClassifierServiceDep = Annotated[ClassifierService, Depends(get_classifier_service)]
