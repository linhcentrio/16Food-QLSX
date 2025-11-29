"""
Factory functions để tạo test data nhanh chóng.

Các factory này giúp tạo test data với default values hợp lý,
giảm boilerplate code trong tests.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.models.entities import (
    Customer,
    Product,
    Supplier,
    Warehouse,
    PricePolicy,
    MaterialPriceHistory,
    SalesOrder,
    SalesOrderLine,
    ProductionOrder,
    ProductionOrderLine,
    ProductionPlanDay,
    BomMaterial,
    BomLabor,
    InventorySnapshot,
    StockDocument,
    StockDocumentLine,
    StockTaking,
    StockTakingLine,
)


# ============================================================================
# Customer & Supplier Factories
# ============================================================================

def create_test_customer(
    db: Session,
    code: str | None = None,
    name: str | None = None,
    level: str = "A",
    channel: str = "GT",
    **kwargs
) -> Customer:
    """Tạo test customer."""
    customer = Customer(
        code=code or f"KH{uuid.uuid4().hex[:6].upper()}",
        name=name or f"Khách hàng Test {code or ''}",
        level=level,
        channel=channel,
        **kwargs
    )
    db.add(customer)
    db.flush()
    return customer


def create_test_supplier(
    db: Session,
    code: str | None = None,
    name: str | None = None,
    **kwargs
) -> Supplier:
    """Tạo test supplier."""
    supplier = Supplier(
        code=code or f"NCC{uuid.uuid4().hex[:6].upper()}",
        name=name or f"Nhà cung cấp Test {code or ''}",
        **kwargs
    )
    db.add(supplier)
    db.flush()
    return supplier


# ============================================================================
# Product Factories
# ============================================================================

def create_test_product(
    db: Session,
    code: str | None = None,
    name: str | None = None,
    group: str = "TP",
    main_uom: str = "kg",
    **kwargs
) -> Product:
    """Tạo test product."""
    product = Product(
        code=code or f"SP{uuid.uuid4().hex[:6].upper()}",
        name=name or f"Sản phẩm Test {code or ''}",
        group=group,
        main_uom=main_uom,
        status="active",
        **kwargs
    )
    db.add(product)
    db.flush()
    return product


def create_test_material(
    db: Session,
    code: str | None = None,
    name: str | None = None,
    cost_price: float = 10000.0,
    **kwargs
) -> Product:
    """Tạo test material (NVL)."""
    return create_test_product(
        db,
        code=code or f"NVL{uuid.uuid4().hex[:6].upper()}",
        name=name or f"Nguyên vật liệu Test {code or ''}",
        group="NVL",
        cost_price=cost_price,
        **kwargs
    )


def create_test_semi_product(
    db: Session,
    code: str | None = None,
    name: str | None = None,
    **kwargs
) -> Product:
    """Tạo test semi-product (BTP)."""
    return create_test_product(
        db,
        code=code or f"BTP{uuid.uuid4().hex[:6].upper()}",
        name=name or f"Bán thành phẩm Test {code or ''}",
        group="BTP",
        **kwargs
    )


# ============================================================================
# Warehouse Factory
# ============================================================================

def create_test_warehouse(
    db: Session,
    code: str | None = None,
    name: str | None = None,
    warehouse_type: str = "TP",
    **kwargs
) -> Warehouse:
    """Tạo test warehouse."""
    warehouse = Warehouse(
        code=code or f"KHO{uuid.uuid4().hex[:6].upper()}",
        name=name or f"Kho Test {code or ''}",
        type=warehouse_type,
        **kwargs
    )
    db.add(warehouse)
    db.flush()
    return warehouse


# ============================================================================
# Sales Order Factories
# ============================================================================

def create_test_sales_order(
    db: Session,
    customer: Customer,
    order_date: date | None = None,
    delivery_date: date | None = None,
    status: str = "new",
    **kwargs
) -> SalesOrder:
    """Tạo test sales order."""
    if order_date is None:
        order_date = date.today()
    if delivery_date is None:
        delivery_date = order_date + timedelta(days=3)
    
    order = SalesOrder(
        code=kwargs.pop("code", f"DH{uuid.uuid4().hex[:8].upper()}"),
        customer_id=customer.id,
        order_date=order_date,
        delivery_date=delivery_date,
        status=status,
        total_amount=0.0,
        **kwargs
    )
    db.add(order)
    db.flush()
    return order


def create_test_sales_order_line(
    db: Session,
    order: SalesOrder,
    product: Product,
    quantity: float = 10.0,
    unit_price: float | None = None,
    **kwargs
) -> SalesOrderLine:
    """Tạo test sales order line."""
    if unit_price is None:
        # Lấy giá từ PricePolicy hoặc dùng giá mặc định
        unit_price = 50000.0
    
    line = SalesOrderLine(
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        quantity=quantity,
        unit_price=unit_price,
        line_amount=quantity * unit_price,
        uom=product.main_uom,
        **kwargs
    )
    db.add(line)
    
    # Cập nhật total_amount của order
    order.total_amount = sum(line.line_amount for line in order.lines) + line.line_amount
    db.flush()
    return line


# ============================================================================
# Production Order Factories
# ============================================================================

def create_test_production_order(
    db: Session,
    product: Product,
    production_date: date | None = None,
    planned_qty: float = 100.0,
    status: str = "new",
    order_type: str = "SP",
    **kwargs
) -> ProductionOrder:
    """Tạo test production order."""
    if production_date is None:
        production_date = date.today()
    
    order = ProductionOrder(
        business_id=kwargs.pop("business_id", f"LSX{uuid.uuid4().hex[:8].upper()}"),
        product_id=product.id,
        product_name=product.name,
        production_date=production_date,
        planned_qty=planned_qty,
        order_type=order_type,
        status=status,
        **kwargs
    )
    db.add(order)
    db.flush()
    return order


def create_test_production_order_line(
    db: Session,
    production_order: ProductionOrder,
    product: Product,
    planned_qty: float = 10.0,
    **kwargs
) -> ProductionOrderLine:
    """Tạo test production order line."""
    line = ProductionOrderLine(
        production_order_id=production_order.id,
        product_id=product.id,
        product_name=product.name,
        planned_qty=planned_qty,
        uom=product.main_uom,
        **kwargs
    )
    db.add(line)
    db.flush()
    return line


# ============================================================================
# BOM Factories
# ============================================================================

def create_test_bom_material(
    db: Session,
    product: Product,
    material: Product,
    quantity: float = 1.0,
    **kwargs
) -> BomMaterial:
    """Tạo test BOM material."""
    bom = BomMaterial(
        product_id=product.id,
        material_id=material.id,
        quantity=quantity,
        uom=material.main_uom,
        **kwargs
    )
    db.add(bom)
    db.flush()
    return bom


def create_test_bom_labor(
    db: Session,
    product: Product,
    labor_type: str = "Công nhân",
    duration_minutes: int = 60,
    unit_cost: float = 50000.0,
    **kwargs
) -> BomLabor:
    """Tạo test BOM labor."""
    bom = BomLabor(
        product_id=product.id,
        labor_type=labor_type,
        duration_minutes=duration_minutes,
        unit_cost=unit_cost,
        **kwargs
    )
    db.add(bom)
    db.flush()
    return bom


# ============================================================================
# Inventory Factories
# ============================================================================

def create_test_inventory_snapshot(
    db: Session,
    product: Product,
    warehouse: Warehouse,
    current_qty: float = 100.0,
    **kwargs
) -> InventorySnapshot:
    """Tạo test inventory snapshot."""
    snapshot = InventorySnapshot(
        product_id=product.id,
        warehouse_id=warehouse.id,
        current_qty=current_qty,
        total_in=kwargs.get("total_in", current_qty),
        total_out=kwargs.get("total_out", 0.0),
        inventory_value=kwargs.get("inventory_value", 0.0),
        **{k: v for k, v in kwargs.items() if k not in ["total_in", "total_out", "inventory_value"]}
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def create_test_stock_document(
    db: Session,
    warehouse: Warehouse,
    doc_type: str = "N",
    posting_date: date | None = None,
    **kwargs
) -> StockDocument:
    """Tạo test stock document."""
    if posting_date is None:
        posting_date = date.today()
    
    doc = StockDocument(
        code=kwargs.pop("code", f"PNX{uuid.uuid4().hex[:8].upper()}"),
        warehouse_id=warehouse.id,
        doc_type=doc_type,
        posting_date=posting_date,
        **kwargs
    )
    db.add(doc)
    db.flush()
    return doc


def create_test_stock_document_line(
    db: Session,
    document: StockDocument,
    product: Product,
    quantity: float = 10.0,
    **kwargs
) -> StockDocumentLine:
    """Tạo test stock document line."""
    line = StockDocumentLine(
        document_id=document.id,
        product_id=product.id,
        product_name=product.name,
        quantity=quantity,
        signed_qty=kwargs.get("signed_qty", quantity),
        uom=product.main_uom,
        **kwargs
    )
    db.add(line)
    db.flush()
    return line


def create_test_stock_taking(
    db: Session,
    warehouse: Warehouse,
    stocktaking_date: date | None = None,
    status: str = "draft",
    **kwargs
) -> StockTaking:
    """Tạo test stock taking."""
    if stocktaking_date is None:
        stocktaking_date = date.today()
    
    stocktaking = StockTaking(
        code=kwargs.pop("code", f"KK{uuid.uuid4().hex[:8].upper()}"),
        warehouse_id=warehouse.id,
        stocktaking_date=stocktaking_date,
        status=status,
        **kwargs
    )
    db.add(stocktaking)
    db.flush()
    return stocktaking


def create_test_stock_taking_line(
    db: Session,
    stocktaking: StockTaking,
    product: Product,
    book_qty: float = 100.0,
    counted_qty: float = 95.0,
    **kwargs
) -> StockTakingLine:
    """Tạo test stock taking line."""
    line = StockTakingLine(
        stocktaking_id=stocktaking.id,
        product_id=product.id,
        book_qty=book_qty,
        counted_qty=counted_qty,
        difference_qty=counted_qty - book_qty,
        **kwargs
    )
    db.add(line)
    db.flush()
    return line


# ============================================================================
# Price Policy Factory
# ============================================================================

def create_test_price_policy(
    db: Session,
    product: Product,
    customer_level: str = "A",
    price: float = 50000.0,
    effective_date: date | None = None,
    **kwargs
) -> PricePolicy:
    """Tạo test price policy."""
    if effective_date is None:
        effective_date = date.today()
    
    policy = PricePolicy(
        product_id=product.id,
        customer_level=customer_level,
        price=price,
        effective_date=effective_date,
        **kwargs
    )
    db.add(policy)
    db.flush()
    return policy

