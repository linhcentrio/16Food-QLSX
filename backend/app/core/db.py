"""
Khởi tạo kết nối SQLAlchemy cho backend Robyn.

Hiện tại dùng sync engine + sessionmaker đơn giản với SQLite.
Sau này có thể chuyển sang async engine nếu cần.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from .config import settings
from ..models.base import Base

# Đảm bảo thư mục chứa database tồn tại
db_path = Path(settings.db_path)
if db_path.parent != Path("."):
    db_path.parent.mkdir(parents=True, exist_ok=True)

# Tạo engine SQLite với các cấu hình phù hợp
engine = create_engine(
    settings.sqlalchemy_database_uri,
    echo=settings.debug,
    connect_args={"check_same_thread": False},  # Cho phép multi-threading
    pool_pre_ping=False,  # Không cần cho SQLite
)

# Đăng ký event để hỗ trợ foreign keys trong SQLite (mặc định tắt)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Bật foreign key constraints cho SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Khởi tạo database (tạo bảng nếu chưa có).

    Trong môi trường production nên dùng migration (Alembic) thay vì auto-create.
    Ở giai đoạn MVP có thể dùng hàm này để nhanh chóng có schema.
    """

    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager cung cấp SQLAlchemy Session an toàn."""

    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


