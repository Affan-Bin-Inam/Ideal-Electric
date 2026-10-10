import os
import subprocess
import sys
from pathlib import Path

# The environment must be set BEFORE any `api` import, because the settings and
# the database engine are created at import time.
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://ideal_dev:dev_password_change_me@localhost:5432/ideal_electric_test",
)
assert TEST_DB_URL.rsplit("/", 1)[-1].endswith("_test"), (
    "Refusing to run tests against a database whose name doesn't end in _test"
)
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters-long"

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from api.db import async_session_factory, engine  # noqa: E402
from api.main import app  # noqa: E402
from api.models import User  # noqa: E402
from api.security import hash_password  # noqa: E402

engine.sync_engine.echo = False

BASE_URL = "http://testserver"


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Build the test schema by running the real migrations, which tests them too."""
    api_dir = Path(__file__).resolve().parent.parent
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=api_dir,
        check=True,
        env=os.environ.copy(),
    )


@pytest_asyncio.fixture(autouse=True)
async def clean_auth_tables():
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE users, refresh_tokens RESTART IDENTITY CASCADE"))
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        yield c


@pytest_asyncio.fixture
async def make_user():
    async def _make(
        email="admin@example.com",
        password="correct-horse-battery",
        role="admin",
        is_active=True,
    ):
        async with async_session_factory() as session:
            user = User(
                email=email,
                full_name="Test User",
                role=role,
                password_hash=hash_password(password),
                is_active=is_active,
            )
            session.add(user)
            await session.commit()
            return user

    return _make