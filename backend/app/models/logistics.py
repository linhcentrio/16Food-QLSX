"""
Models cho Module Giao Vận (Logistics).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, uuid_pk


class DeliveryVehicle(Base):
    """Bảng phương tiện giao hàng."""

    __tablename__ = "delivery_vehicle"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    license_plate: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(50))  # xe tải, xe máy, etc.
    driver_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    driver_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    capacity_kg: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="available")  # available, in_use, maintenance
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    deliveries: Mapped[list["Delivery"]] = relationship(back_populates="vehicle")


class Delivery(Base):
    """Bảng phiếu giao hàng."""

    __tablename__ = "delivery"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    sales_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("salesorder.id"), index=True
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("delivery_vehicle.id"), nullable=True, index=True
    )
    planned_delivery_date: Mapped[date] = mapped_column(Date)
    actual_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivery_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    driver_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="planned"
    )  # planned, in_transit, delivered, cancelled
    delivery_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # Chữ ký khách hàng
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    sales_order: Mapped["SalesOrder"] = relationship()
    vehicle: Mapped[DeliveryVehicle | None] = relationship(back_populates="deliveries")
    lines: Mapped[list["DeliveryLine"]] = relationship(
        back_populates="delivery", cascade="all, delete-orphan"
    )


class DeliveryLine(Base):
    """Bảng chi tiết phiếu giao hàng."""

    __tablename__ = "delivery_line"

    id: Mapped[uuid.UUID] = uuid_pk()
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("delivery.id"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Numeric(18, 3))
    delivered_quantity: Mapped[float] = mapped_column(Numeric(18, 3), default=0)
    uom: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    delivery: Mapped[Delivery] = relationship(back_populates="lines")
    product: Mapped["Product"] = relationship()

