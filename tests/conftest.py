import atexit
import os

import pytest
from testcontainers.postgres import PostgresContainer

# ---------------------------------------------------------------------------
# Start PostgreSQL container BEFORE any app imports.
# This ensures settings.DATABASE_URL resolves to the container URL everywhere,
# including app.db.session.SessionLocal used by _persist_invocation.
# ---------------------------------------------------------------------------

_pg = PostgresContainer("postgres:16-alpine", driver="psycopg2")
_pg.start()
os.environ["DATABASE_URL"] = _pg.get_connection_url()
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
atexit.register(_pg.stop)

# Now safe to import app modules — they'll pick up the Postgres URL
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

import app.models  # noqa: E402, F401 — register all models with Base.metadata
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

engine = create_engine(_pg.get_connection_url())
TestSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def db():
    session = TestSessionLocal()
    try:
        # Seed OperationalSettings with auto_classify_inbound=False to match
        # the env-var default and keep tests deterministic.
        from app.models.settings import OperationalSettings

        ops = OperationalSettings(id=1, auto_classify_inbound=False, reviewer_enabled=True)
        session.add(ops)
        session.commit()
        yield session
    finally:
        session.rollback()
        # Clean up all data between tests
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()


@pytest.fixture
def client(db: Session):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
