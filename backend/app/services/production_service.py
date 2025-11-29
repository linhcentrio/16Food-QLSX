"""
Service xử lý business logic cho module Quản lý Sản xuất (QLSX).

Bao gồm:
- Tự động tạo LSX từ đơn hàng
- Tính toán kế hoạch sản xuất (KHSX)
- Quản lý BOM và nhu cầu vật tư
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta, datetime
from decimal import Decimal
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.entities import (
    SalesOrder,
    SalesOrderLine,
    Product,
    ProductionOrder,
    ProductionOrderLine,
    ProductionPlanDay,
    InventorySnapshot,
    Warehouse,
)
from .bom_service import calculate_material_requirements_for_production_order


def calculate_batch_count(planned_qty: float, batch_spec: str | None) -> float:
    """
    Tính số mẻ cần sản xuất dựa trên số lượng kế hoạch và quy cách mẻ.
    
    Args:
        planned_qty: Số lượng kế hoạch cần sản xuất
        batch_spec: Quy cách mẻ (vd: "20kg/mẻ", "100cái/mẻ") hoặc số lượng/mẻ
    
    Returns:
        Số mẻ (làm tròn lên)
    """
    if not batch_spec or planned_qty <= 0:
        return 0.0
    
    # Nếu batch_spec là số đơn giản (ví dụ: "20")
    try:
        batch_size = float(batch_spec)
        if batch_size > 0:
            return math.ceil(planned_qty / batch_size)
    except (ValueError, TypeError):
        pass
    
    # Nếu batch_spec có định dạng "20kg/mẻ" hoặc "100cái/mẻ"
    # Tách số từ chuỗi (lấy số đầu tiên)
    import re
    match = re.search(r'(\d+(?:\.\d+)?)', str(batch_spec))
    if match:
        batch_size = float(match.group(1))
        if batch_size > 0:
            return math.ceil(planned_qty / batch_size)
    
    return 1.0


def get_available_stock(
    db: Session, product_id, warehouse_type: str = "TP"
) -> float:
    """
    Lấy tồn kho khả dụng của sản phẩm trong các kho theo loại.
    
    Args:
        db: Database session
        product_id: ID sản phẩm
        warehouse_type: Loại kho (TP, BTP, NVL)
    
    Returns:
        Tổng số lượng tồn kho khả dụng
    """
    result = (
        db.query(func.sum(InventorySnapshot.current_qty))
        .join(Warehouse, InventorySnapshot.warehouse_id == Warehouse.id)
        .filter(
            InventorySnapshot.product_id == product_id,
            Warehouse.type == warehouse_type,
        )
        .scalar()
    )
    return float(result or 0.0)


def aggregate_demand_from_orders(
    db: Session, start_date: date | None = None, end_date: date | None = None
) -> dict[str, dict[str, float]]:
    """
    Tổng hợp nhu cầu sản phẩm từ các đơn hàng trong khoảng thời gian.
    
    Args:
        db: Database session
        start_date: Ngày bắt đầu (lấy từ ngày giao hàng)
        end_date: Ngày kết thúc
    
    Returns:
        Dict {product_id: {delivery_date: total_quantity}}
    """
    query = (
        db.query(
            SalesOrderLine.product_id,
            SalesOrder.delivery_date,
            func.sum(SalesOrderLine.quantity).label("total_qty"),
        )
        .join(SalesOrder, SalesOrderLine.order_id == SalesOrder.id)
        .filter(SalesOrder.status.in_(["new", "in_production"]))
    )
    
    if start_date:
        query = query.filter(SalesOrder.delivery_date >= start_date)
    if end_date:
        query = query.filter(SalesOrder.delivery_date <= end_date)
    
    results = query.group_by(SalesOrderLine.product_id, SalesOrder.delivery_date).all()
    
    demand: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    
    for product_id, delivery_date, total_qty in results:
        demand[str(product_id)][delivery_date.isoformat()] += float(total_qty)
    
    return demand


def create_production_plan_day(
    db: Session,
    product_id,
    production_date: date,
    planned_qty: float,
    capacity_max: float = 1000.0,
) -> ProductionPlanDay:
    """
    Tạo hoặc cập nhật kế hoạch sản xuất theo ngày.
    
    Args:
        db: Database session
        product_id: ID sản phẩm
        production_date: Ngày sản xuất
        planned_qty: Số lượng kế hoạch
        capacity_max: Công suất tối đa/ngày
    
    Returns:
        ProductionPlanDay entity
    """
    existing = (
        db.query(ProductionPlanDay)
        .filter(
            ProductionPlanDay.product_id == product_id,
            ProductionPlanDay.production_date == production_date,
        )
        .first()
    )
    
    if existing:
        existing.planned_qty += Decimal(str(planned_qty))
        existing.remaining_qty = existing.planned_qty - existing.ordered_qty
        return existing
    
    plan = ProductionPlanDay(
        product_id=product_id,
        production_date=production_date,
        planned_qty=Decimal(str(planned_qty)),
        ordered_qty=Decimal("0"),
        remaining_qty=Decimal(str(planned_qty)),
        capacity_max=Decimal(str(capacity_max)),
    )
    db.add(plan)
    return plan


def create_production_order_from_demand(
    db: Session,
    product_id,
    production_date: date,
    planned_qty: float,
    order_type: str = "SP",
) -> ProductionOrder:
    """
    Tạo lệnh sản xuất từ nhu cầu.
    
    Args:
        db: Database session
        product_id: ID sản phẩm
        production_date: Ngày sản xuất
        planned_qty: Số lượng kế hoạch
        order_type: Loại lệnh (SP: Sản phẩm, BTP: Bán thành phẩm)
    
    Returns:
        ProductionOrder entity
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Sản phẩm không tồn tại: {product_id}")
    
    # Sinh mã LSX: LSX-yyyyMMdd-xxx
    count_today = (
        db.query(ProductionOrder)
        .filter(ProductionOrder.production_date == production_date)
        .count()
    )
    business_id = f"LSX-{production_date.strftime('%Y%m%d')}-{count_today + 1:03d}"
    
    # Tính số mẻ
    batch_count = calculate_batch_count(planned_qty, product.batch_spec)
    
    # Tạo LSX
    po = ProductionOrder(
        business_id=business_id,
        production_date=production_date,
        order_type=order_type,
        product_id=product_id,
        product_name=product.name,
        planned_qty=Decimal(str(planned_qty)),
        status="new",
    )
    db.add(po)
    db.flush()
    
    # Tạo chi tiết LSX (lenh_sx_ct)
    pol = ProductionOrderLine(
        production_order_id=po.id,
        product_id=product_id,
        product_name=product.name,
        batch_spec=product.batch_spec,
        batch_count=Decimal(str(batch_count)),
        uom=product.main_uom,
        planned_qty=Decimal(str(planned_qty)),
    )
    db.add(pol)
    
    return po


def generate_production_orders_from_sales_orders(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    auto_deduct_stock: bool = True,
) -> list[ProductionOrder]:
    """
    Tự động tạo LSX từ đơn hàng (Use Case UC-01).
    
    Business Logic:
    1. Tổng hợp nhu cầu sản phẩm từ đơn_hang_ct trong khoảng ngày giao hàng
    2. Trừ đi tồn kho BTP/thành phẩm hiện có (nếu auto_deduct_stock=True)
    3. Quy đổi ra số mẻ cần SX dựa trên quy_cach_me
    4. Sinh bản ghi khsx_ngay theo từng ngày SX, tôn trọng công_suat_max
    5. Từ kế hoạch, sinh lenh_sx + lenh_sx_ct
    
    Args:
        db: Database session
        start_date: Ngày bắt đầu (mặc định: hôm nay)
        end_date: Ngày kết thúc (mặc định: +30 ngày)
        auto_deduct_stock: Có tự động trừ tồn kho không
    
    Returns:
        Danh sách ProductionOrder đã tạo
    """
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    # Bước 1: Tổng hợp nhu cầu từ đơn hàng
    demand = aggregate_demand_from_orders(db, start_date, end_date)
    
    created_orders: list[ProductionOrder] = []
    
    # Bước 2 & 3: Xử lý từng sản phẩm
    for product_id, delivery_by_date in demand.items():
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            continue
        
        # Xác định loại sản phẩm
        order_type = "BTP" if product.group == "BTP" else "SP"
        warehouse_type = "BTP" if product.group == "BTP" else "TP"
        
        # Tính tổng nhu cầu
        total_demand = sum(delivery_by_date.values())
        
        # Trừ tồn kho hiện có (nếu có)
        if auto_deduct_stock:
            available_stock = get_available_stock(db, product_id, warehouse_type)
            net_demand = max(0.0, total_demand - available_stock)
        else:
            net_demand = total_demand
        
        if net_demand <= 0:
            continue
        
        # Bước 4: Phân bổ theo ngày sản xuất (đơn giản: sản xuất trước ngày giao 1-2 ngày)
        # Ưu tiên các đơn hàng có ngày giao sớm nhất
        sorted_dates = sorted(delivery_by_date.keys())
        
        remaining_demand = net_demand
        current_prod_date = start_date
        
        for delivery_date_str in sorted_dates:
            delivery_date = date.fromisoformat(delivery_date_str)
            # Sản xuất trước ngày giao 1-2 ngày
            prod_date = delivery_date - timedelta(days=1)
            if prod_date < start_date:
                prod_date = start_date
            
            demand_for_date = delivery_by_date[delivery_date_str]
            demand_to_fulfill = min(demand_for_date, remaining_demand)
            
            if demand_to_fulfill <= 0:
                continue
            
            # Kiểm tra công suất (đơn giản: giả sử capacity_max = 1000)
            # Trong thực tế cần lấy từ bảng khsx_ngay hoặc config
            capacity_max = 1000.0
            existing_plan = (
                db.query(ProductionPlanDay)
                .filter(
                    ProductionPlanDay.product_id == product_id,
                    ProductionPlanDay.production_date == prod_date,
                )
                .first()
            )
            
            used_capacity = float(existing_plan.ordered_qty) if existing_plan else 0.0
            available_capacity = capacity_max - used_capacity
            
            if available_capacity <= 0:
                # Chuyển sang ngày tiếp theo
                prod_date = prod_date + timedelta(days=1)
                available_capacity = capacity_max
            
            qty_to_produce = min(demand_to_fulfill, available_capacity)
            
            # Bước 5: Tạo LSX
            po = create_production_order_from_demand(
                db, product_id, prod_date, qty_to_produce, order_type
            )
            created_orders.append(po)
            
            # Cập nhật KHSX ngày
            create_production_plan_day(
                db, product_id, prod_date, qty_to_produce, capacity_max
            )
            
            remaining_demand -= qty_to_produce
    
    return created_orders


def create_pivot_bom_lsx(
    db: Session, production_date: date
) -> dict:
    """
    Tạo pivot table BOM LSX theo ngày sản xuất.
    
    Logic:
    - Lấy tất cả ProductionOrder có production_date
    - Với mỗi LSX, tính nhu cầu NVL/BTP từ BOM
    - Group by: material_id, material_name, uom
    - Sum: required_quantity, total_cost
    
    Args:
        db: Database session
        production_date: Ngày sản xuất
    
    Returns:
        Dict với format:
        {
            "production_date": "2025-01-15",
            "items": [
                {
                    "material_id": "...",
                    "material_code": "...",
                    "material_name": "...",
                    "uom": "kg",
                    "total_quantity": 100.0,
                    "total_cost": 5000000.0
                }
            ]
        }
    """
    # Lấy tất cả LSX có production_date
    production_orders = (
        db.query(ProductionOrder)
        .filter(ProductionOrder.production_date == production_date)
        .all()
    )
    
    if not production_orders:
        return {
            "production_date": production_date.isoformat(),
            "items": [],
        }
    
    # Tổng hợp nhu cầu NVL/BTP từ tất cả LSX
    material_requirements: dict[str, dict] = {}
    
    for po in production_orders:
        try:
            requirements = calculate_material_requirements_for_production_order(
                db, po.id
            )
            
            for req in requirements:
                material_id = req["material_id"]
                material_code = req.get("material_code", "")
                material_name = req.get("material_name", "")
                
                if material_id not in material_requirements:
                    material_requirements[material_id] = {
                        "material_id": str(material_id),
                        "material_code": material_code,
                        "material_name": material_name,
                        "uom": req.get("uom", ""),
                        "total_quantity": 0.0,
                        "total_cost": 0.0,
                    }
                
                material_requirements[material_id]["total_quantity"] += req.get("required_quantity", 0.0)
                material_requirements[material_id]["total_cost"] += req.get("total_cost", 0.0)
        except Exception:
            # Bỏ qua LSX có lỗi, tiếp tục với LSX khác
            continue
    
    return {
        "production_date": production_date.isoformat(),
        "items": list(material_requirements.values()),
    }


def update_production_order_line(
    db: Session,
    order_id: uuid.UUID,
    line_id: uuid.UUID,
    planned_qty: float | None = None,
    note: str | None = None,
) -> ProductionOrderLine:
    """
    Cập nhật ProductionOrderLine.
    
    Args:
        db: Database session
        order_id: ID của ProductionOrder
        line_id: ID của ProductionOrderLine
        planned_qty: Số lượng kế hoạch mới (optional)
        note: Ghi chú mới (optional)
    
    Returns:
        ProductionOrderLine đã được cập nhật
    
    Raises:
        ValueError: Nếu order hoặc line không tồn tại
    """
    # Kiểm tra ProductionOrder tồn tại
    production_order = (
        db.query(ProductionOrder)
        .filter(ProductionOrder.id == order_id)
        .first()
    )
    if not production_order:
        raise ValueError(f"ProductionOrder không tồn tại: {order_id}")
    
    # Kiểm tra ProductionOrderLine tồn tại và thuộc về ProductionOrder
    line = (
        db.query(ProductionOrderLine)
        .filter(
            ProductionOrderLine.id == line_id,
            ProductionOrderLine.production_order_id == order_id,
        )
        .first()
    )
    if not line:
        raise ValueError(f"ProductionOrderLine không tồn tại hoặc không thuộc về ProductionOrder: {line_id}")
    
    # Cập nhật planned_qty nếu có
    if planned_qty is not None:
        if planned_qty < 0:
            raise ValueError("planned_qty phải >= 0")
        
        line.planned_qty = Decimal(str(planned_qty))
        
        # Tính lại batch_count dựa trên batch_spec
        if line.batch_spec:
            line.batch_count = Decimal(str(calculate_batch_count(planned_qty, line.batch_spec)))
        
        # Cập nhật tổng planned_qty trong ProductionOrder
        total_planned_qty = (
            db.query(func.sum(ProductionOrderLine.planned_qty))
            .filter(ProductionOrderLine.production_order_id == order_id)
            .scalar()
        )
        if total_planned_qty:
            production_order.planned_qty = Decimal(str(total_planned_qty))
    
    # Cập nhật note nếu có
    if note is not None:
        line.note = note
    
    # Cập nhật updated_at của ProductionOrder
    production_order.updated_at = datetime.utcnow()
    
    db.add(line)
    db.add(production_order)
    
    return line


def bulk_update_production_order_lines(
    db: Session,
    order_id: uuid.UUID,
    updates: list[dict],
) -> list[ProductionOrderLine]:
    """
    Cập nhật nhiều ProductionOrderLine cùng lúc.
    
    Args:
        db: Database session
        order_id: ID của ProductionOrder
        updates: List các dict với format:
            [
                {"line_id": "uuid", "planned_qty": 100.0, "note": "..."},
                ...
            ]
    
    Returns:
        List các ProductionOrderLine đã được cập nhật
    
    Raises:
        ValueError: Nếu có lỗi validation
    """
    # Kiểm tra ProductionOrder tồn tại
    production_order = (
        db.query(ProductionOrder)
        .filter(ProductionOrder.id == order_id)
        .first()
    )
    if not production_order:
        raise ValueError(f"ProductionOrder không tồn tại: {order_id}")
    
    updated_lines: list[ProductionOrderLine] = []
    
    # Validate tất cả updates trước khi commit
    line_ids = [uuid.UUID(update["line_id"]) for update in updates]
    existing_lines = (
        db.query(ProductionOrderLine)
        .filter(
            ProductionOrderLine.id.in_(line_ids),
            ProductionOrderLine.production_order_id == order_id,
        )
        .all()
    )
    
    existing_line_ids = {str(line.id) for line in existing_lines}
    for update in updates:
        if update["line_id"] not in existing_line_ids:
            raise ValueError(f"ProductionOrderLine không tồn tại: {update['line_id']}")
    
    # Cập nhật từng line
    for update in updates:
        line_id = uuid.UUID(update["line_id"])
        line = next((l for l in existing_lines if l.id == line_id), None)
        if not line:
            continue
        
        if "planned_qty" in update:
            planned_qty = float(update["planned_qty"])
            if planned_qty < 0:
                raise ValueError(f"planned_qty phải >= 0 cho line {line_id}")
            
            line.planned_qty = Decimal(str(planned_qty))
            
            # Tính lại batch_count
            if line.batch_spec:
                line.batch_count = Decimal(str(calculate_batch_count(planned_qty, line.batch_spec)))
        
        if "note" in update:
            line.note = update["note"]
        
        updated_lines.append(line)
        db.add(line)
    
    # Cập nhật tổng planned_qty trong ProductionOrder
    total_planned_qty = (
        db.query(func.sum(ProductionOrderLine.planned_qty))
        .filter(ProductionOrderLine.production_order_id == order_id)
        .scalar()
    )
    if total_planned_qty:
        production_order.planned_qty = Decimal(str(total_planned_qty))
    
    production_order.updated_at = datetime.utcnow()
    db.add(production_order)
    
    return updated_lines


def create_manual_production_order(
    db: Session,
    production_date: date,
    order_type: str,
    product_id: uuid.UUID,
    planned_qty: float,
    note: str | None = None,
) -> ProductionOrder:
    """
    Tạo lệnh sản xuất thủ công (không từ đơn hàng).
    
    Args:
        db: Database session
        production_date: Ngày sản xuất
        order_type: Loại lệnh (SP hoặc BTP)
        product_id: ID sản phẩm
        planned_qty: Số lượng kế hoạch
        note: Ghi chú (optional)
    
    Returns:
        ProductionOrder đã được tạo
    
    Raises:
        ValueError: Nếu dữ liệu không hợp lệ
    """
    if order_type not in ["SP", "BTP"]:
        raise ValueError("order_type phải là 'SP' hoặc 'BTP'")
    
    if planned_qty <= 0:
        raise ValueError("planned_qty phải > 0")
    
    # Kiểm tra product tồn tại
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Sản phẩm không tồn tại: {product_id}")
    
    # Sinh mã LSX: LSX-yyyyMMdd-xxx
    count_today = (
        db.query(ProductionOrder)
        .filter(ProductionOrder.production_date == production_date)
        .count()
    )
    business_id = f"LSX-{production_date.strftime('%Y%m%d')}-{count_today + 1:03d}"
    
    # Tính số mẻ
    batch_count = calculate_batch_count(planned_qty, product.batch_spec)
    
    # Tạo ProductionOrder
    po = ProductionOrder(
        business_id=business_id,
        production_date=production_date,
        order_type=order_type,
        product_id=product_id,
        product_name=product.name,
        planned_qty=Decimal(str(planned_qty)),
        status="new",
        note=note,
    )
    db.add(po)
    db.flush()
    
    # Tạo ProductionOrderLine
    pol = ProductionOrderLine(
        production_order_id=po.id,
        product_id=product_id,
        product_name=product.name,
        batch_spec=product.batch_spec,
        batch_count=Decimal(str(batch_count)),
        uom=product.main_uom,
        planned_qty=Decimal(str(planned_qty)),
        note=note,
    )
    db.add(pol)
    
    return po

