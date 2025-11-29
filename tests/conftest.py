"""
Pytest configuration và fixtures cho tests.

Fixtures:
- test_db: Test database session
- test_client: Test HTTP client cho Robyn app
"""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

# Override database path cho tests - sử dụng in-memory SQLite
os.environ["DB_PATH"] = ":memory:"

# Import sau khi set environment variable
from backend.app.models.base import Base


@pytest.fixture(scope="session")
def test_db_engine():
    """Tạo SQLite in-memory engine cho tests."""
    # Tạo engine riêng cho tests
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    
    # Bật foreign keys cho SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Tạo tất cả tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def test_db(test_db_engine) -> Generator[Session, None, None]:
    """Tạo database session cho mỗi test.
    
    Mỗi test sẽ có transaction riêng và rollback sau khi test xong.
    """
    connection = test_db_engine.connect()
    transaction = connection.begin()
    
    # Tạo session bound to connection
    TestSessionLocal = sessionmaker(bind=connection)
    session = TestSessionLocal()
    
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def override_get_session(test_db, monkeypatch):
    """Override get_session trong backend.app.core.db để dùng test_db."""
    from backend.app.core import db
    
    @contextmanager
    def get_test_session():
        try:
            yield test_db
            test_db.commit()
        except Exception:
            test_db.rollback()
            raise
    
    # Override get_session function
    monkeypatch.setattr(db, "get_session", get_test_session)
    
    # Cũng override engine để đảm bảo consistency
    monkeypatch.setattr(db, "engine", test_db.bind)


@pytest.fixture
def test_client(override_get_session, monkeypatch):
    """Tạo test client để gọi API endpoints."""
    # Import sau khi override database
    from backend.app.main import app
    from tests.utils.test_client import APIClient
    
    # Ensure database is initialized (already done in test_db_engine fixture)
    
    return APIClient(app)


@pytest.fixture
def temp_dir():
    """Tạo temporary directory cho file tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
