"""Unit tests for CacheService.

Tests follow TDD pattern - written before implementation.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from uuid_classifier.db.models import Base, UUIDClassification
from uuid_classifier.schemas.classification import (
    ClassificationCreate,
    ClassificationType,
    ConfidenceLevel,
    SourceInfo,
)
from uuid_classifier.services.cache_service import CacheService

# Test database URL - use SQLite for unit tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def async_session(test_engine) -> AsyncSession:
    """Create an async session for testing."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def cache_service(async_session: AsyncSession) -> CacheService:
    """Create a CacheService instance for testing."""
    return CacheService(async_session)


@pytest.fixture
def sample_classification_data() -> ClassificationCreate:
    """Create sample classification data for testing."""
    return ClassificationCreate(
        uuid="0000180d-0000-1000-8000-00805f9b34fb",
        name="Heart Rate",
        type=ClassificationType.STANDARD_BLE_SERVICE,
        description="Bluetooth SIG standardized Heart Rate Service",
        sources=[
            SourceInfo(
                title="Bluetooth GATT Services",
                url="https://www.bluetooth.com/specifications/gatt/services/",
                snippet="Heart Rate Service UUID: 0x180D",
            )
        ],
        confidence=ConfidenceLevel.HIGH,
        searched_at=datetime.now(UTC),
    )


@pytest.fixture
async def populated_db(
    async_session: AsyncSession,
    sample_classification_data: ClassificationCreate,
) -> UUIDClassification:
    """Populate the database with a sample classification record."""
    record = UUIDClassification(
        uuid=sample_classification_data.uuid,
        name=sample_classification_data.name,
        type=sample_classification_data.type.value,
        description=sample_classification_data.description,
        sources=[s.model_dump(mode="json") for s in sample_classification_data.sources],
        confidence=sample_classification_data.confidence.value,
        searched_at=sample_classification_data.searched_at,
    )
    async_session.add(record)
    await async_session.commit()
    await async_session.refresh(record)
    return record


class TestGetClassification:
    """Tests for CacheService.get_classification method."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(
        self, cache_service: CacheService
    ) -> None:
        """get_classification returns None for unknown UUID."""
        result = await cache_service.get_classification(
            "00000000-0000-0000-0000-000000000000"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_existing_returns_record(
        self,
        cache_service: CacheService,
        populated_db: UUIDClassification,
    ) -> None:
        """get_classification returns record for known UUID."""
        result = await cache_service.get_classification(populated_db.uuid)

        assert result is not None
        assert result.uuid == populated_db.uuid
        assert result.name == populated_db.name
        assert result.type.value == populated_db.type
        assert result.confidence.value == populated_db.confidence

    @pytest.mark.asyncio
    async def test_uuid_normalization_lowercase(
        self,
        cache_service: CacheService,
        populated_db: UUIDClassification,
    ) -> None:
        """get_classification normalizes UUID to lowercase."""
        # Query with uppercase UUID
        uppercase_uuid = populated_db.uuid.upper()
        result = await cache_service.get_classification(uppercase_uuid)

        assert result is not None
        assert result.uuid == populated_db.uuid.lower()

    @pytest.mark.asyncio
    async def test_uuid_normalization_no_hyphens(
        self,
        cache_service: CacheService,
        populated_db: UUIDClassification,
    ) -> None:
        """get_classification normalizes UUID without hyphens."""
        # Query with UUID without hyphens
        no_hyphen_uuid = populated_db.uuid.replace("-", "")
        result = await cache_service.get_classification(no_hyphen_uuid)

        assert result is not None
        assert result.uuid == populated_db.uuid


class TestSaveClassification:
    """Tests for CacheService.save_classification method."""

    @pytest.mark.asyncio
    async def test_save_creates_new_record(
        self,
        cache_service: CacheService,
        sample_classification_data: ClassificationCreate,
    ) -> None:
        """save_classification creates new record and returns it."""
        result = await cache_service.save_classification(sample_classification_data)

        assert result is not None
        assert result.uuid == sample_classification_data.uuid
        assert result.name == sample_classification_data.name
        assert result.type == sample_classification_data.type
        assert result.confidence == sample_classification_data.confidence

    @pytest.mark.asyncio
    async def test_save_and_retrieve(
        self,
        cache_service: CacheService,
        sample_classification_data: ClassificationCreate,
    ) -> None:
        """Saved record can be retrieved."""
        saved = await cache_service.save_classification(sample_classification_data)
        retrieved = await cache_service.get_classification(saved.uuid)

        assert retrieved is not None
        assert retrieved.uuid == saved.uuid
        assert retrieved.name == saved.name

    @pytest.mark.asyncio
    async def test_save_normalizes_uuid(
        self,
        cache_service: CacheService,
    ) -> None:
        """save_classification normalizes UUID before saving."""
        data = ClassificationCreate(
            uuid="0000180D-0000-1000-8000-00805F9B34FB",  # Uppercase
            name="Test Service",
            type=ClassificationType.UNKNOWN,
            description="Test description",
            sources=[],
            confidence=ConfidenceLevel.LOW,
            searched_at=datetime.now(UTC),
        )

        result = await cache_service.save_classification(data)

        # UUID should be normalized to lowercase
        assert result.uuid == "0000180d-0000-1000-8000-00805f9b34fb"

    @pytest.mark.asyncio
    async def test_save_duplicate_raises_or_updates(
        self,
        cache_service: CacheService,
        populated_db: UUIDClassification,
        sample_classification_data: ClassificationCreate,
    ) -> None:
        """save_classification handles duplicate UUID gracefully."""
        # Ensure populated_db is used - it pre-populates the database with a record
        assert populated_db.uuid == sample_classification_data.uuid

        # Modify the data but keep same UUID
        modified_data = ClassificationCreate(
            uuid=sample_classification_data.uuid,
            name="Updated Name",
            type=ClassificationType.VENDOR_SPECIFIC,
            description="Updated description",
            sources=[],
            confidence=ConfidenceLevel.MEDIUM,
            searched_at=datetime.now(UTC),
        )

        # Should either raise an error or perform upsert
        # Implementation can choose - test verifies graceful handling
        try:
            result = await cache_service.save_classification(modified_data)
            # If upsert, verify the record was updated
            assert result.uuid == modified_data.uuid
        except Exception as e:
            # If error, verify it's a controlled exception, not a crash
            assert "duplicate" in str(e).lower() or "exists" in str(e).lower()


class TestExists:
    """Tests for CacheService.exists method."""

    @pytest.mark.asyncio
    async def test_exists_false_when_absent(self, cache_service: CacheService) -> None:
        """exists returns False for unknown UUID."""
        result = await cache_service.exists("00000000-0000-0000-0000-000000000000")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true_when_present(
        self,
        cache_service: CacheService,
        populated_db: UUIDClassification,
    ) -> None:
        """exists returns True for known UUID."""
        result = await cache_service.exists(populated_db.uuid)
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_with_uuid_normalization(
        self,
        cache_service: CacheService,
        populated_db: UUIDClassification,
    ) -> None:
        """exists normalizes UUID before checking."""
        # Test with uppercase
        uppercase_uuid = populated_db.uuid.upper()
        result = await cache_service.exists(uppercase_uuid)
        assert result is True

        # Test without hyphens
        no_hyphen_uuid = populated_db.uuid.replace("-", "")
        result = await cache_service.exists(no_hyphen_uuid)
        assert result is True


class TestServiceIntegration:
    """Integration tests for CacheService."""

    @pytest.mark.asyncio
    async def test_full_workflow(
        self,
        cache_service: CacheService,
        sample_classification_data: ClassificationCreate,
    ) -> None:
        """Test complete workflow: check -> save -> retrieve."""
        uuid = sample_classification_data.uuid

        # Initially doesn't exist
        assert await cache_service.exists(uuid) is False
        assert await cache_service.get_classification(uuid) is None

        # Save the classification
        saved = await cache_service.save_classification(sample_classification_data)
        assert saved is not None

        # Now exists
        assert await cache_service.exists(uuid) is True

        # Can retrieve
        retrieved = await cache_service.get_classification(uuid)
        assert retrieved is not None
        assert retrieved.uuid == uuid
        assert retrieved.name == sample_classification_data.name

    @pytest.mark.asyncio
    async def test_sources_serialization(
        self,
        cache_service: CacheService,
        sample_classification_data: ClassificationCreate,
    ) -> None:
        """Test that sources are properly serialized and deserialized."""
        saved = await cache_service.save_classification(sample_classification_data)
        retrieved = await cache_service.get_classification(saved.uuid)

        assert retrieved is not None
        assert len(retrieved.sources) == len(sample_classification_data.sources)
        assert retrieved.sources[0].title == sample_classification_data.sources[0].title
        assert str(retrieved.sources[0].url) == str(
            sample_classification_data.sources[0].url
        )
