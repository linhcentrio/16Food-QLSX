"""
Service xử lý business logic cho Inventory operations từ Production Orders.

Bao gồm:
- Tạo phiếu nhập kho từ LSX hoàn thành
- Tạo phiếu xuất kho từ ngày sản xuất
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from ..models.entities import (
    ProductionOrder,
    ProductionOrderLine,
    Product,
    Warehouse,
    StockDocument,
    StockDocumentLine,
    InventorySnapshot,
)


def find_warehouse_by_type(db: Session, warehouse_type: str) -> Warehouse | None:
    """
    Tìm kho theo loại (BTP, TP, NVL).
    
    Args:
        db: Database session
        warehouse_type: Loại kho ("BTP", "TP", "NVL")
    
    Returns:
        Warehouse đầu tiên tìm thấy hoặc None
    """
    return (
        db.query(Warehouse)
        .filter(Warehouse.type == warehouse_type)
        .first()
    )


def create_stock_document_from_production_order(
    db: Session, production_order_id
) -> StockDocument:
    """
    Tạo phiếu nhập kho từ LSX hoàn thành.
    
    Logic:
    - Lấy ProductionOrder theo ID
    - Kiểm tra status = "completed" và completed_qty > 0
    - Tự động xác định kho theo product.group:
      - BTP → tìm kho type "BTP"
      - SP/TP → tìm kho type "TP"
    - Tạo StockDocument loại "N" với:
      - Sản phẩm: Từ ProductionOrderLine
      - Số lượng: completed_qty
      - mfg_date: production_date
      - exp_date: Tính từ production_date + product.shelf_life_days (nếu có)
    - Cập nhật InventorySnapshot tự động
    
    Args:
        db: Database session
        production_order_id: ID của ProductionOrder
    
    Returns:
        StockDocument đã tạo
    
    Raises:
        ValueError: Nếu LSX không tồn tại, chưa hoàn thành, hoặc không tìm thấy kho
    """
    # Lấy LSX
    po = db.query(ProductionOrder).filter(ProductionOrder.id == production_order_id).first()
    if not po:
        raise ValueError(f"Lệnh sản xuất không tồn tại: {production_order_id}")
    
    # Kiểm tra trạng thái
    if po.status != "completed":
        raise ValueError(f"LSX chưa hoàn thành (status: {po.status})")
    
    if po.completed_qty <= 0:
        raise ValueError("LSX chưa có số lượng hoàn thành")
    
    # Lấy thông tin sản phẩm
    product = db.query(Product).filter(Product.id == po.product_id).first()
    if not product:
        raise ValueError(f"Sản phẩm không tồn tại: {po.product_id}")
    
    # Xác định kho theo loại sản phẩm
    if product.group == "BTP":
        warehouse_type = "BTP"
    elif product.group in ("TP", "SP"):
        warehouse_type = "TP"
    else:
        raise ValueError(f"Không thể xác định kho cho loại sản phẩm: {product.group}")
    
    warehouse = find_warehouse_by_type(db, warehouse_type)
    if not warehouse:
        raise ValueError(f"Không tìm thấy kho loại {warehouse_type}")
    
    # Lấy ProductionOrderLine
    po_line = (
        db.query(ProductionOrderLine)
        .filter(ProductionOrderLine.production_order_id == po.id)
        .first()
    )
    if not po_line:
        raise ValueError("LSX không có chi tiết")
    
    # Tính exp_date
    mfg_date = po.production_date
    exp_date = None
    if product.shelf_life_days:
        exp_date = mfg_date + timedelta(days=product.shelf_life_days)
    
    # Sinh mã phiếu nhập
    posting_date = date.today()
    count_today = (
        db.query(StockDocument)
        .filter(
            StockDocument.posting_date == posting_date,
            StockDocument.doc_type == "N",
        )
        .count()
    )
    code = f"PN{posting_date.strftime('%Y%m%d')}-{count_today + 1:03d}"
    
    # Tạo StockDocument
    doc = StockDocument(
        code=code,
        posting_date=posting_date,
        doc_type="N",
        warehouse_id=warehouse.id,
        storekeeper=None,
        partner_name=None,
        description=f"Nhập kho theo LSX {po.business_id}",
    )
    db.add(doc)
    db.flush()
    
    # Tạo StockDocumentLine
    quantity = float(po.completed_qty)
    doc_line = StockDocumentLine(
        document_id=doc.id,
        product_id=product.id,
        product_name=product.name,
        batch_spec=po_line.batch_spec,
        mfg_date=mfg_date,
        exp_date=exp_date,
        uom=po_line.uom,
        quantity=quantity,
        signed_qty=quantity,
    )
    db.add(doc_line)
    db.flush()
    
    # Cập nhật InventorySnapshot
    inv = (
        db.query(InventorySnapshot)
        .filter(
            InventorySnapshot.product_id == product.id,
            InventorySnapshot.warehouse_id == warehouse.id,
        )
        .first()
    )
    if not inv:
        inv = InventorySnapshot(
            product_id=product.id,
            warehouse_id=warehouse.id,
            total_in=0,
            total_out=0,
            current_qty=0,
        )
        db.add(inv)
        db.flush()
    
    inv.total_in = (inv.total_in or 0) + quantity
    inv.current_qty = (inv.total_in or 0) - (inv.total_out or 0)
    
    return doc


def create_stock_document_from_production_date(
    db: Session, production_date: date, warehouse_code: str
) -> StockDocument:
    """
    Tạo phiếu xuất kho từ ngày sản xuất.
    
    Logic:
    - Lấy tất cả ProductionOrder có production_date và status != "cancelled"
    - Tính tổng hợp nhu cầu NVL từ BOM của tất cả LSX
    - Group by material_id và sum required_quantity
    - Tạo StockDocument loại "X" với tổng hợp NVL
    - Cập nhật InventorySnapshot tự động
    
    Args:
        db: Database session
        production_date: Ngày sản xuất
        warehouse_code: Mã kho xuất (thường là kho NVL)
    
    Returns:
        StockDocument đã tạo
    
    Raises:
        ValueError: Nếu không tìm thấy kho hoặc không có LSX
    """
    from .bom_service import calculate_material_requirements_for_production_order
    
    # Tìm kho
    warehouse = db.query(Warehouse).filter(Warehouse.code == warehouse_code).first()
    if not warehouse:
        raise ValueError(f"Kho không tồn tại: {warehouse_code}")
    
    # Lấy tất cả LSX có production_date và status != "cancelled"
    production_orders = (
        db.query(ProductionOrder)
        .filter(
            ProductionOrder.production_date == production_date,
            ProductionOrder.status != "cancelled",
        )
        .all()
    )
    
    if not production_orders:
        raise ValueError(f"Không có LSX nào cho ngày {production_date}")
    
    # Tổng hợp nhu cầu NVL từ tất cả LSX
    material_requirements: dict[str, dict] = {}
    
    for po in production_orders:
        try:
            requirements = calculate_material_requirements_for_production_order(
                db, po.id
            )
            
            for req in requirements:
                material_id = req["material_id"]
                if material_id not in material_requirements:
                    material_requirements[material_id] = {
                        "material_id": material_id,
                        "material_code": req["material_code"],
                        "material_name": req["material_name"],
                        "uom": req["uom"],
                        "total_quantity": 0.0,
                    }
                
                material_requirements[material_id]["total_quantity"] += req["required_quantity"]
        except Exception as e:
            # Log lỗi nhưng tiếp tục với LSX khác
            continue
    
    if not material_requirements:
        raise ValueError("Không tính được nhu cầu NVL từ các LSX")
    
    # Sinh mã phiếu xuất
    posting_date = date.today()
    count_today = (
        db.query(StockDocument)
        .filter(
            StockDocument.posting_date == posting_date,
            StockDocument.doc_type == "X",
        )
        .count()
    )
    code = f"PX{posting_date.strftime('%Y%m%d')}-{count_today + 1:03d}"
    
    # Tạo StockDocument
    doc = StockDocument(
        code=code,
        posting_date=posting_date,
        doc_type="X",
        warehouse_id=warehouse.id,
        storekeeper=None,
        partner_name=None,
        description=f"Xuất kho theo NSX {production_date.isoformat()}",
    )
    db.add(doc)
    db.flush()
    
    # Tạo các dòng StockDocumentLine và cập nhật InventorySnapshot
    for material_id, req_data in material_requirements.items():
        product = db.query(Product).filter(Product.id == material_id).first()
        if not product:
            continue
        
        quantity = req_data["total_quantity"]
        
        # Kiểm tra tồn kho
        inv = (
            db.query(InventorySnapshot)
            .filter(
                InventorySnapshot.product_id == product.id,
                InventorySnapshot.warehouse_id == warehouse.id,
            )
            .first()
        )
        current_qty = float(inv.current_qty if inv else 0)
        if current_qty < quantity:
            raise ValueError(
                f"Tồn kho không đủ cho {product.code}: "
                f"hiện có {current_qty}, cần {quantity}"
            )
        
        # Tạo dòng phiếu
        doc_line = StockDocumentLine(
            document_id=doc.id,
            product_id=product.id,
            product_name=product.name,
            batch_spec=None,
            mfg_date=None,
            exp_date=None,
            uom=req_data["uom"],
            quantity=quantity,
            signed_qty=-quantity,  # Âm cho xuất kho
        )
        db.add(doc_line)
        
        # Cập nhật InventorySnapshot
        if not inv:
            inv = InventorySnapshot(
                product_id=product.id,
                warehouse_id=warehouse.id,
                total_in=0,
                total_out=0,
                current_qty=0,
            )
            db.add(inv)
            db.flush()
        
        inv.total_out = (inv.total_out or 0) + quantity
        inv.current_qty = (inv.total_in or 0) - (inv.total_out or 0)
    
    return doc


def query_inventory_with_filters(
    db: Session,
    product_group: str | None = None,
    product_code: str | None = None,
    product_name: str | None = None,
    warehouse_code: str | None = None,
    warehouse_type: str | None = None,
    min_qty: float | None = None,
    max_qty: float | None = None,
) -> list[dict[str, Any]]:
    """
    Query inventory với nhiều filters.
    
    Args:
        db: Database session
        product_group: Loại sản phẩm (NVL, BTP, TP, Phu_lieu)
        product_code: Mã sản phẩm
        product_name: Tên sản phẩm (partial match)
        warehouse_code: Mã kho
        warehouse_type: Loại kho (TP, BTP, NVL)
        min_qty: Số lượng tối thiểu
        max_qty: Số lượng tối đa
    
    Returns:
        List các dict với thông tin inventory
    """
    query = (
        db.query(InventorySnapshot, Product, Warehouse)
        .join(Product, InventorySnapshot.product_id == Product.id)
        .join(Warehouse, InventorySnapshot.warehouse_id == Warehouse.id)
    )
    
    # Apply filters
    if product_group:
        query = query.filter(Product.group == product_group)
    
    if product_code:
        query = query.filter(Product.code == product_code)
    
    if product_name:
        query = query.filter(Product.name.ilike(f"%{product_name}%"))
    
    if warehouse_code:
        query = query.filter(Warehouse.code == warehouse_code)
    
    if warehouse_type:
        query = query.filter(Warehouse.type == warehouse_type)
    
    if min_qty is not None:
        query = query.filter(InventorySnapshot.current_qty >= Decimal(str(min_qty)))
    
    if max_qty is not None:
        query = query.filter(InventorySnapshot.current_qty <= Decimal(str(max_qty)))
    
    rows = query.order_by(Product.code, Warehouse.code).all()
    
    return [
        {
            "product_id": str(p.id),
            "product_code": p.code,
            "product_name": p.name,
            "product_group": p.group,
            "warehouse_id": str(w.id),
            "warehouse_code": w.code,
            "warehouse_name": w.name,
            "warehouse_type": w.type,
            "current_qty": float(inv.current_qty),
            "total_in": float(inv.total_in),
            "total_out": float(inv.total_out),
            "inventory_value": float(inv.inventory_value),
        }
        for inv, p, w in rows
    ]

