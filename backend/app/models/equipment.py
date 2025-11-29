"""
Models cho Module Thiết Bị, CCDC (Equipment & Tools).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, Date, DateTime, Boolean, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, uuid_pk


class EquipmentType(Base):
    """Bảng loại thiết bị."""

    __tablename__ = "equipment_type"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    equipment: Mapped[list["Equipment"]] = relationship(back_populates="equipment_type")


class Equipment(Base):
    """Bảng thiết bị."""

    __tablename__ = "equipment"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    equipment_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment_type.id"), index=True
    )
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    warranty_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, maintenance, repair, retired
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    equipment_type: Mapped[EquipmentType] = relationship(back_populates="equipment")
    fuel_norms: Mapped[list["FuelConsumptionNorm"]] = relationship(
        back_populates="equipment", cascade="all, delete-orphan"
    )
    repairs: Mapped[list["EquipmentRepair"]] = relationship(
        back_populates="equipment", cascade="all, delete-orphan"
    )
    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(
        back_populates="equipment", cascade="all, delete-orphan"
    )


class FuelConsumptionNorm(Base):
    """Bảng định mức nhiên liệu."""

    __tablename__ = "fuel_consumption_norm"

    id: Mapped[uuid.UUID] = uuid_pk()
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id"), index=True
    )
    fuel_type: Mapped[str] = mapped_column(String(50))  # xăng, dầu, điện, etc.
    consumption_rate: Mapped[float] = mapped_column(Numeric(18, 4))  # lít/giờ, kWh/giờ
    unit: Mapped[str] = mapped_column(String(20))  # lít, kWh, etc.
    effective_date: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    equipment: Mapped[Equipment] = relationship(back_populates="fuel_norms")


class EquipmentRepair(Base):
    """Bảng phiếu sửa chữa thiết bị."""

    __tablename__ = "equipment_repair"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id"), index=True
    )
    request_date: Mapped[date] = mapped_column(Date)
    repair_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    issue_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    repair_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="requested")  # requested, in_progress, completed, cancelled
    repaired_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    equipment: Mapped[Equipment] = relationship(back_populates="repairs")
    lines: Mapped[list["EquipmentRepairLine"]] = relationship(
        back_populates="repair", cascade="all, delete-orphan"
    )


class EquipmentRepairLine(Base):
    """Bảng chi tiết phiếu sửa chữa."""

    __tablename__ = "equipment_repair_line"

    id: Mapped[uuid.UUID] = uuid_pk()
    repair_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment_repair.id"), index=True
    )
    item_description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Numeric(18, 3))
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2))
    line_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    repair: Mapped[EquipmentRepair] = relationship(back_populates="lines")


class MaintenanceSchedule(Base):
    """Bảng lịch bảo dưỡng."""

    __tablename__ = "maintenance_schedule"

    id: Mapped[uuid.UUID] = uuid_pk()
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id"), index=True
    )
    maintenance_type: Mapped[str] = mapped_column(String(50))  # định kỳ, theo giờ, theo km
    interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interval_hours: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    next_maintenance_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_maintenance_hours: Mapped[float | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    equipment: Mapped[Equipment] = relationship()
    records: Mapped[list["MaintenanceRecord"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )


class MaintenanceRecord(Base):
    """Bảng lịch sử bảo dưỡng."""

    __tablename__ = "maintenance_record"

    id: Mapped[uuid.UUID] = uuid_pk()
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id"), index=True
    )
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("maintenance_schedule.id"), nullable=True, index=True
    )
    maintenance_date: Mapped[date] = mapped_column(Date)
    maintenance_hours: Mapped[float | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    maintenance_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cost: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    next_maintenance_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_maintenance_hours: Mapped[float | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    equipment: Mapped[Equipment] = relationship(back_populates="maintenance_records")
    schedule: Mapped[MaintenanceSchedule | None] = relationship(back_populates="records")

