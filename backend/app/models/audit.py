"""
Bảng audit trail để ghi lại tất cả các thay đổi trong hệ thống.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, uuid_pk


class AuditLog(Base):
    """Bảng audit log - ghi lại tất cả các thay đổi trong hệ thống."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = uuid_pk()
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id"), nullable=True, index=True
    )
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(50), index=True)  # CREATE, UPDATE, DELETE, VIEW
    entity_type: Mapped[str] = mapped_column(String(100), index=True)  # Product, Order, etc.
    entity_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

