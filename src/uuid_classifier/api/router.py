"""FastAPI routes for UUID classification API.

This module implements the main classification endpoint that orchestrates
cache lookup, search, and classification operations.
"""

import logging
import time
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from uuid_classifier import __version__
from uuid_classifier.api.dependencies import (
    CacheServiceDep,
    ClassifierServiceDep,
    SearchServiceDep,
)
from uuid_classifier.schemas.classification import (
    UUID_PATTERN,
    ClassificationResponse,
    UUIDRequest,
    normalize_uuid,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def validate_uuid_format(uuid: str) -> str:
    """Validate and normalize UUID format.

    Args:
        uuid: The UUID string to validate.

    Returns:
        Normalized UUID string (lowercase with hyphens).

    Raises:
        HTTPException: If the UUID format is invalid (400 status).
    """
    if not UUID_PATTERN.match(uuid):
        logger.warning("Invalid UUID format received: %s", uuid)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format. Expected format: "
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx or xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        )
    return normalize_uuid(uuid)


async def classify_uuid_handler(
    uuid: str,
    cache_service: CacheServiceDep,
    search_service: SearchServiceDep,
    classifier_service: ClassifierServiceDep,
) -> ClassificationResponse:
    """Core handler for UUID classification.

    This implements the orchestration flow:
    1. Validate UUID format (return 400 if invalid)
    2. Normalize UUID (lowercase, with hyphens)
    3. Check cache via CacheService
    4. If cached: return with cached=true
    5. If not cached: call SearchService
    6. Pass results to ClassifierService
    7. Save to cache via CacheService
    8. Return with cached=false

    Args:
        uuid: The UUID to classify (already validated and normalized).
        cache_service: Service for cache operations.
        search_service: Service for web searches.
        classifier_service: Service for classification logic.

    Returns:
        ClassificationResponse with classification data.

    Raises:
        HTTPException: On internal errors (500 status).
    """
    start_time = time.monotonic()
    normalized_uuid = validate_uuid_format(uuid)

    logger.info("Processing classification request for UUID: %s", normalized_uuid)

    try:
        # Step 1: Check cache
        logger.debug("Checking cache for UUID: %s", normalized_uuid)
        cached_result = await cache_service.get_classification(normalized_uuid)

        if cached_result is not None:
            elapsed = time.monotonic() - start_time
            logger.info(
                "Cache hit for UUID: %s (%.3fs)", normalized_uuid, elapsed
            )
            return cached_result

        # Step 2: Cache miss - perform search
        logger.info("Cache miss for UUID: %s - initiating search", normalized_uuid)
        search_results = await search_service.search_uuid(normalized_uuid)
        logger.debug("Search returned %d results", len(search_results))

        # Step 3: Classify based on search results
        classification = await classifier_service.classify(
            normalized_uuid, search_results
        )

        # Step 4: Save to cache
        logger.debug("Saving classification to cache")
        response = await cache_service.save_classification(classification)

        elapsed = time.monotonic() - start_time
        logger.info(
            "Classification complete for UUID: %s (%.3fs, cached=%s)",
            normalized_uuid,
            elapsed,
            response.cached,
        )

        return response

    except Exception as e:
        elapsed = time.monotonic() - start_time
        logger.exception(
            "Error classifying UUID %s after %.3fs: %s",
            normalized_uuid,
            elapsed,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during classification",
        ) from e


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Dictionary with status and version information.
    """
    return {"status": "ok", "version": __version__}


@router.get(
    "/classify/{uuid}",
    response_model=ClassificationResponse,
    summary="Classify UUID (path parameter)",
    description="Classify a UUID provided as a path parameter. Returns cached result if available.",
    responses={
        200: {"description": "Successfully classified UUID"},
        400: {"description": "Invalid UUID format"},
        500: {"description": "Internal server error"},
    },
)
async def classify_uuid_get(
    uuid: Annotated[
        str,
        Path(
            description="UUID to classify (accepts both hyphenated and non-hyphenated formats)",
            examples=["0000180d-0000-1000-8000-00805f9b34fb", "0000180d00001000800000805f9b34fb"],
        ),
    ],
    cache_service: CacheServiceDep,
    search_service: SearchServiceDep,
    classifier_service: ClassifierServiceDep,
) -> ClassificationResponse:
    """Classify a UUID via GET request.

    Args:
        uuid: UUID to classify (path parameter).
        cache_service: Injected cache service.
        search_service: Injected search service.
        classifier_service: Injected classifier service.

    Returns:
        ClassificationResponse with the classification result.
    """
    return await classify_uuid_handler(
        uuid, cache_service, search_service, classifier_service
    )


@router.post(
    "/classify",
    response_model=ClassificationResponse,
    summary="Classify UUID (request body)",
    description="Classify a UUID provided in the request body. Returns cached result if available.",
    responses={
        200: {"description": "Successfully classified UUID"},
        400: {"description": "Invalid UUID format"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def classify_uuid_post(
    request: UUIDRequest,
    cache_service: CacheServiceDep,
    search_service: SearchServiceDep,
    classifier_service: ClassifierServiceDep,
) -> ClassificationResponse:
    """Classify a UUID via POST request.

    Args:
        request: Request body containing the UUID.
        cache_service: Injected cache service.
        search_service: Injected search service.
        classifier_service: Injected classifier service.

    Returns:
        ClassificationResponse with the classification result.
    """
    return await classify_uuid_handler(
        request.uuid, cache_service, search_service, classifier_service
    )
