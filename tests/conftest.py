import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

# Override DB URL before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.api.deps import get_session
from app.db.base import Base
import app.models  # noqa: F401 — register all models with Base.metadata
from app.main import app

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# Enable foreign keys in SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(scope="session", autouse=True)
def create_tables():
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

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
