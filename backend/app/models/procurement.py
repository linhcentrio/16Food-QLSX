"""
Models cho Module Thu Mua (Procurement).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, Date, DateTime, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, uuid_pk


class PurchaseRequest(Base):
    """Bảng phiếu yêu cầu mua hàng."""

    __tablename__ = "purchase_request"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    request_date: Mapped[date] = mapped_column(Date)
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="draft"
    )  # draft, pending, approved, rejected, ordered, completed
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    lines: Mapped[list["PurchaseRequestLine"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        back_populates="purchase_request"
    )


class PurchaseRequestLine(Base):
    """Bảng chi tiết phiếu yêu cầu mua hàng."""

    __tablename__ = "purchase_request_line"

    id: Mapped[uuid.UUID] = uuid_pk()
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchase_request.id"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(255))
    specification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(18, 3))
    uom: Mapped[str] = mapped_column(String(20))
    estimated_unit_price: Mapped[float | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    estimated_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    required_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    request: Mapped[PurchaseRequest] = relationship(back_populates="lines")
    product: Mapped["Product"] = relationship()


class PurchaseOrder(Base):
    """Bảng đơn mua hàng."""

    __tablename__ = "purchase_order"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    purchase_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("purchase_request.id"), nullable=True, index=True
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("supplier.id"), index=True
    )
    order_date: Mapped[date] = mapped_column(Date)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="draft"
    )  # draft, ordered, received, completed, cancelled
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    payment_status: Mapped[str] = mapped_column(String(20), default="unpaid")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    supplier: Mapped["Supplier"] = relationship()
    purchase_request: Mapped[PurchaseRequest | None] = relationship(
        back_populates="purchase_orders"
    )
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class PurchaseOrderLine(Base):
    """Bảng chi tiết đơn mua hàng."""

    __tablename__ = "purchase_order_line"

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchase_order.id"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(255))
    specification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(18, 3))
    received_quantity: Mapped[float] = mapped_column(Numeric(18, 3), default=0)
    uom: Mapped[str] = mapped_column(String(20))
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2))
    line_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped[PurchaseOrder] = relationship(back_populates="lines")
    product: Mapped["Product"] = relationship()

