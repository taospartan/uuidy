# Copilot Instructions for uuidy

## Project Overview
UUID classification API service for identifying unknown UUIDs (especially Bluetooth Low Energy service UUIDs). Built with FastAPI, PostgreSQL caching, and Google search integration.

## Architecture

### Layer Structure (Clean Architecture)
```
src/uuid_classifier/
├── api/router.py          # FastAPI routes, thin layer
├── core/config.py         # Pydantic Settings for env config
├── db/models.py           # SQLAlchemy 2.0 async models
├── db/database.py         # Connection/session management
├── schemas/classification.py  # Pydantic v2 request/response models
├── services/
│   ├── search_service.py     # Google/SerpAPI integration
│   ├── classifier_service.py # Heuristic parsing of search results
│   └── cache_service.py      # DB read/write for cached records
└── utils/helpers.py
```

### Data Flow
1. Request → `api/router.py` validates UUID format
2. Check cache via `cache_service` → return if hit
3. On miss: `search_service` queries Google → `classifier_service` compiles results
4. Store in PostgreSQL → return new classification record

## Development Commands
```bash
uv sync                    # Install dependencies from uv.lock
uv run fastapi dev         # Run dev server
uv run pytest              # Run all tests
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run mypy .              # Type check (strict mode)
```

## Code Patterns

### Dependency Injection
Use FastAPI's `Depends()` for services. Example:
```python
async def get_classification(uuid: str, cache: CacheService = Depends()):
```

### Test-Driven Development (TDD)
- Write failing tests FIRST in `tests/unit/` or `tests/integration/`
- Target >90% coverage
- Use `httpx.AsyncClient` for API tests
- Mock external services (SerpAPI) in unit tests

### Classification Schema
```python
{
    "uuid": str,
    "name": str,           # Extracted name or "Unknown"
    "type": str,           # "Standard BLE Service", "Vendor-Specific", etc.
    "description": str,
    "sources": [{"title": str, "url": str, "snippet": str}],
    "confidence": "high" | "medium" | "low",
    "cached": bool,
    "searched_at": datetime
}
```

## Key Conventions
- **Async everywhere**: Use `async def` for all I/O operations
- **Pydantic v2**: All schemas use Pydantic v2 syntax
- **SQLAlchemy 2.0**: Async session pattern with `async_sessionmaker`
- **UUID validation**: Reject invalid UUIDs with 400 status
- **Error handling**: Graceful fallback on search API failures

## External Dependencies
- **SerpAPI**: Requires `SERPAPI_KEY` env var for Google search
- **PostgreSQL**: Connection via `DATABASE_URL` env var
