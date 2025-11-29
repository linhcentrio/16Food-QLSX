"""
Models mở rộng cho Module CRM.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, Date, DateTime, Boolean, Numeric, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, uuid_pk


class AccountsReceivable(Base):
    """Bảng công nợ phải thu (từ khách hàng)."""

    __tablename__ = "accounts_receivable"

    id: Mapped[uuid.UUID] = uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer.id"), index=True
    )
    sales_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("salesorder.id"), nullable=True, index=True
    )
    transaction_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    invoice_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    paid_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    remaining_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(20), default="unpaid")  # unpaid, partial, paid, overdue
    payment_terms: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    customer: Mapped["Customer"] = relationship()
    sales_order: Mapped["SalesOrder | None"] = relationship()


class AccountsPayable(Base):
    """Bảng công nợ phải trả (cho nhà cung cấp)."""

    __tablename__ = "accounts_payable"

    id: Mapped[uuid.UUID] = uuid_pk()
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("supplier.id"), index=True
    )
    purchase_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("purchase_order.id"), nullable=True, index=True
    )
    transaction_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    invoice_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    paid_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    remaining_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(20), default="unpaid")  # unpaid, partial, paid, overdue
    payment_terms: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    supplier: Mapped["Supplier"] = relationship()
    purchase_order: Mapped["PurchaseOrder | None"] = relationship()


class SupplierContract(Base):
    """Bảng điều khoản hợp đồng với nhà cung cấp."""

    __tablename__ = "supplier_contract"

    id: Mapped[uuid.UUID] = uuid_pk()
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("supplier.id"), index=True
    )
    contract_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    contract_type: Mapped[str] = mapped_column(String(50))  # Framework, Specific, Service
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Net 30, Net 60, etc.
    delivery_terms: Mapped[str | None] = mapped_column(String(100), nullable=True)  # FOB, CIF, etc.
    quality_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    penalty_clause: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_terms: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON hoặc text
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, expired, terminated
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    supplier: Mapped["Supplier"] = relationship()
    evaluations: Mapped[list["SupplierEvaluation"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan"
    )


class SupplierEvaluation(Base):
    """Bảng đánh giá chất lượng nhà cung cấp."""

    __tablename__ = "supplier_evaluation"

    id: Mapped[uuid.UUID] = uuid_pk()
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("supplier.id"), index=True
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("supplier_contract.id"), nullable=True, index=True
    )
    evaluation_date: Mapped[date] = mapped_column(Date)
    evaluation_period_start: Mapped[date] = mapped_column(Date)
    evaluation_period_end: Mapped[date] = mapped_column(Date)
    evaluated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Các tiêu chí đánh giá
    quality_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100
    delivery_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100
    price_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100
    service_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100
    overall_score: Mapped[float] = mapped_column(Numeric(5, 2))  # Trung bình các điểm
    
    # Metrics
    on_time_delivery_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)  # %
    defect_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)  # %
    total_orders: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_value: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    rating: Mapped[str] = mapped_column(String(20))  # Excellent, Good, Fair, Poor
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    supplier: Mapped["Supplier"] = relationship()
    contract: Mapped[SupplierContract | None] = relationship(back_populates="evaluations")


class CustomerSegment(Base):
    """Bảng phân khúc khách hàng."""

    __tablename__ = "customer_segment"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    criteria: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON criteria
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class CustomerFeedback(Base):
    """Bảng phản hồi từ khách hàng."""

    __tablename__ = "customer_feedback"

    id: Mapped[uuid.UUID] = uuid_pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer.id"), index=True
    )
    sales_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("salesorder.id"), nullable=True, index=True
    )
    feedback_date: Mapped[date] = mapped_column(Date)
    feedback_type: Mapped[str] = mapped_column(String(50))  # Complaint, Suggestion, Praise, Question
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Product, Service, Delivery, etc.
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="new")  # new, in_progress, resolved, closed
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    customer: Mapped["Customer"] = relationship()
    sales_order: Mapped["SalesOrder | None"] = relationship()


class KpiMetric(Base):
    """Bảng KPI metrics."""

    __tablename__ = "kpi_metric"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(50))  # Sales, Production, Inventory, Quality, etc.
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    target_value: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    current_value: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    calculation_formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class KpiRecord(Base):
    """Bảng ghi nhận KPI theo thời gian."""

    __tablename__ = "kpi_record"

    id: Mapped[uuid.UUID] = uuid_pk()
    kpi_metric_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("kpi_metric.id"), index=True
    )
    record_date: Mapped[date] = mapped_column(Date)
    period_type: Mapped[str] = mapped_column(String(20))  # daily, weekly, monthly, yearly
    value: Mapped[float] = mapped_column(Numeric(18, 2))
    target_value: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    variance: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    variance_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    kpi_metric: Mapped[KpiMetric] = relationship()

