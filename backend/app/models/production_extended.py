"""
Models mở rộng cho Module Sản Xuất: Production Logbook và Production Stages.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, Date, DateTime, Boolean, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, uuid_pk


class ProductionStage(Base):
    """Bảng công đoạn sản xuất."""

    __tablename__ = "production_stage"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    sequence: Mapped[int] = mapped_column(Integer)  # Thứ tự công đoạn
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    standard_duration_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    operations: Mapped[list["StageOperation"]] = relationship(
        back_populates="stage", cascade="all, delete-orphan"
    )
    log_entries: Mapped[list["ProductionLogEntry"]] = relationship(
        back_populates="stage"
    )


class StageOperation(Base):
    """Bảng thao tác trong công đoạn."""

    __tablename__ = "stage_operation"

    id: Mapped[uuid.UUID] = uuid_pk()
    stage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("production_stage.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    sequence: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    standard_duration_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    stage: Mapped[ProductionStage] = relationship(back_populates="operations")


class ProductionLog(Base):
    """Bảng nhật ký sản xuất (theo ca/ngày)."""

    __tablename__ = "production_log"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    production_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("productionorder.id"), index=True
    )
    log_date: Mapped[date] = mapped_column(Date)
    shift: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Ca sáng, ca chiều, ca đêm
    operator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_quantity: Mapped[float | None] = mapped_column(
        Numeric(18, 3), nullable=True
    )
    quality_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    issues: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    production_order: Mapped["ProductionOrder"] = relationship()
    entries: Mapped[list["ProductionLogEntry"]] = relationship(
        back_populates="log", cascade="all, delete-orphan"
    )


class ProductionLogEntry(Base):
    """Bảng chi tiết nhật ký sản xuất (theo công đoạn)."""

    __tablename__ = "production_log_entry"

    id: Mapped[uuid.UUID] = uuid_pk()
    log_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("production_log.id"), index=True
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("production_stage.id"), index=True
    )
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity_processed: Mapped[float | None] = mapped_column(
        Numeric(18, 3), nullable=True
    )
    quality_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # OK, NG, Rework
    issues: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    log: Mapped[ProductionLog] = relationship(back_populates="entries")
    stage: Mapped[ProductionStage] = relationship(back_populates="log_entries")

