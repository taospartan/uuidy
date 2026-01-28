# uuidy

A FastAPI-based web service for identifying and classifying unknown UUIDs, with special emphasis on Bluetooth Low Energy (BLE) service UUIDs.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

**uuidy** automates the discovery and classification of unknown UUIDs by:

1. Checking a PostgreSQL cache for previously classified UUIDs
2. If not cached, performing a Google web search to gather information
3. Compiling search results into a structured classification record
4. Caching the result for future queries
5. Returning a structured JSON response with classification details

### Use Cases

- Identifying Bluetooth SIG standardized services (Heart Rate, Battery, etc.)
- Classifying vendor-specific BLE UUIDs
- Recognizing iBeacon, Eddystone, and other beacon formats
- General UUID lookup and documentation

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL (or use Docker)
- [uv](https://github.com/astral-sh/uv) package manager
- SerpAPI key (optional, for web searches)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/taospartan/uuidy.git
   cd uuidy
   ```

2. **Install dependencies with uv**
   ```bash
   uv sync
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Start PostgreSQL** (using Docker)
   ```bash
   docker-compose up -d
   ```

5. **Run the server**
   ```bash
   uv run fastapi dev
   ```

6. **Make your first request**
   ```bash
   curl http://localhost:8000/classify/0000180d-0000-1000-8000-00805f9b34fb
   ```

The API is now running at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API info and version |
| `GET` | `/health` | Health check |
| `GET` | `/db-check` | Database connection check |
| `GET` | `/classify/{uuid}` | Classify UUID (path parameter) |
| `POST` | `/classify` | Classify UUID (request body) |
| `GET` | `/docs` | OpenAPI interactive documentation |
| `GET` | `/redoc` | ReDoc API documentation |

### Example Requests

#### Classify a Standard BLE Service UUID (GET)

```bash
curl http://localhost:8000/classify/0000180d-0000-1000-8000-00805f9b34fb
```

#### Classify UUID with POST Request

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"uuid": "0000180d-0000-1000-8000-00805f9b34fb"}'
```

#### Using httpie

```bash
# GET request
http :8000/classify/0000180d-0000-1000-8000-00805f9b34fb

# POST request
http POST :8000/classify uuid=0000180d-0000-1000-8000-00805f9b34fb
```

#### Non-hyphenated UUID Format

Both formats are accepted and normalized:

```bash
curl http://localhost:8000/classify/0000180d00001000800000805f9b34fb
```

### Response Format

```json
{
  "uuid": "0000180d-0000-1000-8000-00805f9b34fb",
  "name": "Heart Rate",
  "type": "Standard BLE Service",
  "description": "Bluetooth SIG standardized Heart Rate Service for heart rate monitors",
  "sources": [
    {
      "title": "Bluetooth GATT Services",
      "url": "https://www.bluetooth.com/specifications/gatt/services/",
      "snippet": "Heart Rate Service UUID: 0x180D"
    }
  ],
  "confidence": "high",
  "cached": true,
  "searched_at": "2026-01-28T12:00:00Z"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `uuid` | string | Normalized UUID (lowercase, hyphenated) |
| `name` | string | Identified name or "Unknown" |
| `type` | string | Classification type (see below) |
| `description` | string | Summary description |
| `sources` | array | List of sources with title, url, snippet |
| `confidence` | string | `high`, `medium`, or `low` |
| `cached` | boolean | Whether result was from cache |
| `searched_at` | string | ISO 8601 timestamp of classification |

#### Classification Types

- `Standard BLE Service` - Bluetooth SIG standardized service
- `Vendor-Specific` - Manufacturer-specific UUID
- `Apple iBeacon` - Apple iBeacon format
- `Google Eddystone` - Google Eddystone beacon
- `Custom Service` - Custom/proprietary service
- `Unknown` - Could not be classified

### Error Responses

#### Invalid UUID Format (400)

```json
{
  "detail": "Invalid UUID format. Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx or xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

#### Internal Server Error (500)

```json
{
  "detail": "Internal server error during classification"
}
```

## Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env` and customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://uuidy:uuidy@localhost:5432/uuidy` | PostgreSQL connection string |
| `SERPAPI_KEY` | `None` | SerpAPI key for Google searches (optional) |
| `CACHE_TTL_DAYS` | `30` | Days to keep cached classifications |

### Database URL Format

```
postgresql+asyncpg://<user>:<password>@<host>:<port>/<database>
```

### SerpAPI Key

Get your API key at [serpapi.com](https://serpapi.com/). Without a key, searches will fail gracefully and return "Unknown" classifications.

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
uv sync

# Start PostgreSQL
docker-compose up -d
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/uuid_classifier --cov-report=term-missing

# Run only unit tests
uv run pytest tests/unit/ -v

# Run only integration tests
uv run pytest tests/integration/ -v
```

### Linting and Type Checking

```bash
# Lint code
uv run ruff check .

# Auto-fix lint issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Type check
uv run mypy .
```

### Development Server

```bash
# Run with auto-reload
uv run fastapi dev

# Run production server
uv run uvicorn uuid_classifier.main:app --host 0.0.0.0 --port 8000
```

## Architecture

The project follows clean architecture principles with clear layer separation:

```
src/uuid_classifier/
├── main.py              # FastAPI application entry point
├── api/
│   ├── router.py        # API routes (thin layer)
│   └── dependencies.py  # FastAPI dependency injection
├── core/
│   └── config.py        # Pydantic Settings configuration
├── db/
│   ├── models.py        # SQLAlchemy 2.0 async models
│   └── database.py      # Connection/session management
├── schemas/
│   └── classification.py # Pydantic v2 request/response models
├── services/
│   ├── cache_service.py      # Database read/write operations
│   ├── search_service.py     # Google/SerpAPI integration
│   └── classifier_service.py # Heuristic classification logic
└── utils/
    └── ble_patterns.py  # BLE UUID pattern matching
```

### Data Flow

1. **Request received** → `api/router.py` validates UUID format
2. **Cache check** → `cache_service` queries PostgreSQL
3. **Cache hit** → Return cached classification
4. **Cache miss** → `search_service` queries Google via SerpAPI
5. **Classification** → `classifier_service` compiles results using heuristics
6. **Store** → `cache_service` saves to PostgreSQL
7. **Response** → Return new classification record

## Docker

### Using Docker Compose (Development)

```bash
# Start PostgreSQL only
docker-compose up -d

# View logs
docker-compose logs -f postgres

# Stop services
docker-compose down

# Remove volumes (reset database)
docker-compose down -v
```

### Building the Application Image

```bash
# Build the image
docker build -t uuidy:latest .

# Run the container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://uuidy:uuidy@host.docker.internal:5432/uuidy \
  -e SERPAPI_KEY=your_key_here \
  uuidy:latest
```

## Common BLE Service UUIDs

Here are some commonly queried UUIDs for testing:

| UUID | Name |
|------|------|
| `0000180d-0000-1000-8000-00805f9b34fb` | Heart Rate |
| `0000180f-0000-1000-8000-00805f9b34fb` | Battery Service |
| `00001800-0000-1000-8000-00805f9b34fb` | Generic Access |
| `00001801-0000-1000-8000-00805f9b34fb` | Generic Attribute |
| `0000181a-0000-1000-8000-00805f9b34fb` | Environmental Sensing |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests (TDD approach)
4. Ensure all tests pass and linting is clean
5. Submit a pull request

---

Built with ❤️ using FastAPI, SQLAlchemy, and Python 3.12
