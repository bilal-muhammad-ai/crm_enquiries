"""Test configuration."""

import os
from pathlib import Path

# CrewAI storage must be writable before any crewai import
_test_root = Path(__file__).resolve().parents[1]
_test_data = _test_root / "data" / "crewai_test"
_test_data.mkdir(parents=True, exist_ok=True)
os.environ["XDG_DATA_HOME"] = str(_test_data)
os.environ.setdefault("CREWAI_STORAGE_DIR", "crm_enquiries_test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("SUITECRM_MOCK", "true")
os.environ.setdefault("EMAIL_MOCK", "true")
os.environ.setdefault("CALENDAR_MOCK", "true")
os.environ.setdefault("FATHOM_MOCK", "true")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("CHROMA_PERSIST_DIR", str(_test_root / "data" / "chroma_test"))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from crm_enquiries.database import Base, get_db  # noqa: E402
from crm_enquiries.main import app  # noqa: E402


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def api_headers():
    return {"X-Api-Key": "test-api-key"}


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-jwt-secret"}
