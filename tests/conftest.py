"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.main import app

# Test database URL (use SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
def test_client() -> Generator[TestClient, None, None]:
    """Create synchronous test client."""
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_smartlead_payload() -> dict[str, Any]:
    """Sample SmartLead webhook payload."""
    return {
        "event_type": "reply_received",
        "lead_id": "lead_123",
        "campaign_id": "campaign_456",
        "email": "john@example.com",
        "reply_text": "Hi, I'm interested in learning more about your service.",
        "subject": "Re: Your Solution",
        "received_at": "2024-01-15T10:30:00Z",
    }


@pytest.fixture
def sample_connectsafely_payload() -> dict[str, Any]:
    """Sample ConnectSafely webhook payload."""
    return {
        "event_type": "connection_accepted",
        "profile_url": "https://linkedin.com/in/johndoe",
        "email": "john@example.com",
        "connection_status": "accepted",
        "received_at": "2024-01-15T10:30:00Z",
    }


@pytest.fixture
def sample_contact_data() -> dict[str, Any]:
    """Sample contact data."""
    return {
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "company_name": "Example Corp",
        "company_domain": "example.com",
        "phone": "+1-555-1234",
    }
