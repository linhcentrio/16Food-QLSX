"""
Database utilities cho tests.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session


@contextmanager
def db_transaction(db: Session) -> Generator[Session, None, None]:
    """Context manager để wrap database transaction.
    
    Usage:
        with db_transaction(db) as session:
            # Do database operations
            session.add(...)
            # Commit happens automatically on exit
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


def cleanup_db(db: Session) -> None:
    """Xóa tất cả dữ liệu trong database (giữ lại schema).
    
    Warning: Chỉ dùng trong tests!
    """
    from backend.app.models.base import Base
    
    # Xóa theo thứ tự để tránh foreign key violations
    # Cần xóa child tables trước
    tables_to_delete = [
        "stockdocumentline",
        "stockdocument",
        "stocktakingline",
        "stocktaking",
        "salesorderline",
        "salesorder",
        "productionorderline",
        "productionorder",
        "productionplanday",
        "bommaterial",
        "bomlabor",
        "bomsemiproduct",
        "inventorysnapshot",
        "pricepolicy",
        "materialpricehistory",
        "product",
        "customer",
        "supplier",
        "warehouse",
    ]
    
    for table_name in tables_to_delete:
        try:
            table = Base.metadata.tables.get(table_name)
            if table is not None:
                db.execute(table.delete())
        except Exception:
            pass  # Ignore if table doesn't exist
    
    db.commit()

