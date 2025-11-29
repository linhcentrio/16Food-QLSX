"""
Định nghĩa các entity chính theo PRD cho hệ thống QLSX 16Food.

Lưu ý:
- Dùng UUID làm khóa chính.
- Dùng tên bảng theo tiếng Anh ngắn gọn để thuận tiện cho SQL.
- Các enum trong PRD được biểu diễn bằng String + CHECK constraint bổ sung sau (qua migration).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    String,
    Text,
    Date,
    DateTime,
    Boolean,
    Numeric,
    Integer,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, uuid_pk


class Product(Base):
    """Bảng `san_pham`: NVL, BTP, thành phẩm, phụ liệu."""

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    group: Mapped[str] = mapped_column(String(30))  # NVL, BTP, TP, Phu_lieu
    specification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    main_uom: Mapped[str] = mapped_column(String(20))
    secondary_uom: Mapped[str | None] = mapped_column(String(20), nullable=True)
    conversion_rate: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    batch_spec: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_price: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")

    # Relationships
    bom_materials: Mapped[list["BomMaterial"]] = relationship(
        "BomMaterial",
        foreign_keys="BomMaterial.product_id",
        back_populates="product",
        cascade="all, delete-orphan"
    )


class Customer(Base):
    """Bảng `khach_hang`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    level: Mapped[str] = mapped_column(String(10))  # A, B, C, Khac
    channel: Mapped[str] = mapped_column(String(20))  # GT, MT, Online, Khac
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    credit_limit: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")


class Supplier(Base):
    """Bảng `nha_cung_cap`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)


class PricePolicy(Base):
    """Bảng `chinh_sach_gia`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product.id"), index=True)
    customer_level: Mapped[str] = mapped_column(String(10))
    price: Mapped[float] = mapped_column(Numeric(18, 2))
    effective_date: Mapped[date] = mapped_column(Date)

    product: Mapped[Product] = relationship()


class MaterialPriceHistory(Base):
    """Bảng `lich_su_gia_nvl` / `bang_gia_nvl` gộp đơn giản."""

    id: Mapped[uuid.UUID] = uuid_pk()
    material_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("supplier.id"), index=True
    )
    price: Mapped[float] = mapped_column(Numeric(18, 4))
    quoted_date: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    material: Mapped[Product] = relationship()
    supplier: Mapped[Supplier] = relationship()


class Warehouse(Base):
    """Bảng `dm_kho`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(20))  # NVL, BTP, TP, Khac
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class InventorySnapshot(Base):
    """
    Bảng `ton_kho_song` – có thể là materialized view trong tương lai.
    Ở mức DB ban đầu để dạng bảng maintain bằng trigger/service.
    """

    id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouse.id"), index=True
    )
    total_in: Mapped[float] = mapped_column(Numeric(18, 3), default=0)
    total_out: Mapped[float] = mapped_column(Numeric(18, 3), default=0)
    current_qty: Mapped[float] = mapped_column(Numeric(18, 3), default=0)
    inventory_value: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    product: Mapped[Product] = relationship()
    warehouse: Mapped[Warehouse] = relationship()


class StockDocument(Base):
    """Bảng `phieu_nx`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    posting_date: Mapped[date] = mapped_column(Date)
    doc_type: Mapped[str] = mapped_column(String(10))  # N, X
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouse.id"), index=True
    )
    storekeeper: Mapped[str | None] = mapped_column(String(255), nullable=True)
    partner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_code_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    warehouse: Mapped[Warehouse] = relationship()
    lines: Mapped[list["StockDocumentLine"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class StockDocumentLine(Base):
    """Bảng `phieu_nx_ct`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stockdocument.id"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(255))
    batch_spec: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mfg_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exp_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    uom: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Numeric(18, 3))
    signed_qty: Mapped[float] = mapped_column(
        Numeric(18, 3)
    )  # + nhập, - xuất (sl_nx)

    document: Mapped[StockDocument] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()


class StockTaking(Base):
    """Bảng `kiem_ke`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouse.id"), index=True
    )
    stocktaking_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="draft")

    warehouse: Mapped[Warehouse] = relationship()
    lines: Mapped[list["StockTakingLine"]] = relationship(
        back_populates="stocktaking", cascade="all, delete-orphan"
    )


class StockTakingLine(Base):
    """Bảng `kiem_ke_ct`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    stocktaking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stocktaking.id"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    book_qty: Mapped[float] = mapped_column(Numeric(18, 3))
    counted_qty: Mapped[float] = mapped_column(Numeric(18, 3))
    difference_qty: Mapped[float] = mapped_column(Numeric(18, 3))
    adjustment_created: Mapped[bool] = mapped_column(Boolean, default=False)

    stocktaking: Mapped[StockTaking] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()


class SalesOrder(Base):
    """Bảng `don_hang`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer.id"), index=True
    )
    order_date: Mapped[date] = mapped_column(Date)
    delivery_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="new")
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    payment_status: Mapped[str] = mapped_column(String(20), default="unpaid")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    customer: Mapped[Customer] = relationship()
    lines: Mapped[list["SalesOrderLine"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class SalesOrderLine(Base):
    """Bảng `don_hang_ct`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("salesorder.id"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(255))
    sales_spec: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uom: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Numeric(18, 3))
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2))
    line_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    batch_spec: Mapped[str | None] = mapped_column(String(100), nullable=True)

    order: Mapped[SalesOrder] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()


class ProductionPlanDay(Base):
    """Bảng `khsx_ngay`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    production_date: Mapped[date] = mapped_column(Date)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    planned_qty: Mapped[float] = mapped_column(Numeric(18, 3))
    ordered_qty: Mapped[float] = mapped_column(Numeric(18, 3), default=0)
    remaining_qty: Mapped[float] = mapped_column(Numeric(18, 3), default=0)
    capacity_max: Mapped[float] = mapped_column(Numeric(18, 3))

    product: Mapped[Product] = relationship()


class ProductionOrder(Base):
    """Bảng `lenh_sx`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    production_date: Mapped[date] = mapped_column(Date)
    order_type: Mapped[str] = mapped_column(String(20))  # SP/BTP
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(255))
    planned_qty: Mapped[float] = mapped_column(Numeric(18, 3))
    completed_qty: Mapped[float] = mapped_column(Numeric(18, 3), default=0)
    expected_diff_qty: Mapped[float] = mapped_column(Numeric(18, 3), default=0)
    status: Mapped[str] = mapped_column(String(20), default="new")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    product: Mapped[Product] = relationship()
    lines: Mapped[list["ProductionOrderLine"]] = relationship(
        back_populates="production_order", cascade="all, delete-orphan"
    )


class ProductionOrderLine(Base):
    """Bảng `lenh_sx_ct`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    production_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("productionorder.id"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(255))
    batch_spec: Mapped[str | None] = mapped_column(String(100), nullable=True)
    batch_count: Mapped[float | None] = mapped_column(
        Numeric(18, 3), nullable=True
    )
    uom: Mapped[str] = mapped_column(String(20))
    planned_qty: Mapped[float] = mapped_column(Numeric(18, 3))
    actual_qty: Mapped[float] = mapped_column(Numeric(18, 3), default=0)
    expected_loss: Mapped[float | None] = mapped_column(
        Numeric(18, 3), nullable=True
    )
    actual_loss: Mapped[float | None] = mapped_column(
        Numeric(18, 3), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    production_order: Mapped[ProductionOrder] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()


class BomMaterial(Base):
    """Bảng `bom_sp` (định mức NVL)."""

    id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    quantity: Mapped[float] = mapped_column(Numeric(18, 6))
    uom: Mapped[str] = mapped_column(String(20))
    cost: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    product: Mapped[Product] = relationship(
        foreign_keys=[product_id], back_populates="bom_materials"
    )
    material: Mapped[Product] = relationship(foreign_keys=[material_id])


class BomLabor(Base):
    """Bảng `bom_nhan_cong`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    equipment: Mapped[str | None] = mapped_column(String(100), nullable=True)
    labor_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[float | None] = mapped_column(Numeric(18, 3), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)

    product: Mapped[Product] = relationship()


class BomSemiProduct(Base):
    """Bảng `bom_btp`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    semi_product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    component_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    quantity: Mapped[float] = mapped_column(Numeric(18, 6))
    uom: Mapped[str] = mapped_column(String(20))
    operation_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)

    semi_product: Mapped[Product] = relationship(
        foreign_keys=[semi_product_id], backref="bom_components"
    )
    component: Mapped[Product] = relationship(foreign_keys=[component_id])


class Department(Base):
    """Bảng `phong_ban`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))


class JobTitle(Base):
    """Bảng `chuc_danh`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255))
    base_salary: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)


class Employee(Base):
    """Bảng `nhan_su`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("department.id"), index=True
    )
    job_title_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobtitle.id"), index=True
    )
    join_date: Mapped[date] = mapped_column(Date)
    leave_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")

    department: Mapped[Department] = relationship()
    job_title: Mapped[JobTitle] = relationship()


class TimeSheet(Base):
    """Bảng `cham_cong`."""

    id: Mapped[uuid.UUID] = uuid_pk()
    work_date: Mapped[date] = mapped_column(Date)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employee.id"), index=True
    )
    shift: Mapped[str | None] = mapped_column(String(50), nullable=True)
    working_hours: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    overtime_hours: Mapped[float] = mapped_column(Numeric(5, 2), default=0)

    employee: Mapped[Employee] = relationship()


class User(Base):
    """Bảng user đăng nhập hệ thống, gắn với nhân sự và role.

    Lưu ý: cần thêm migration tạo bảng tương ứng trong DB.
    """

    id: Mapped[uuid.UUID] = uuid_pk()
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30))  # admin, accountant, warehouse, production, sales
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("employee.id"), nullable=True
    )

    employee: Mapped[Employee | None] = relationship()


