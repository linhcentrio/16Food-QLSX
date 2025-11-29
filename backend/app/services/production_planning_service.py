"""
Service xử lý logic Kế hoạch Sản xuất (KHSX) tự động.

Bao gồm:
- Tính nhu cầu BTP từ sản phẩm
- Dự trù NVL từ LSX
- Tổng hợp kế hoạch sản xuất
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.entities import (
    Product,
    ProductionOrder,
    BomSemiProduct,
    BomMaterial,
    InventorySnapshot,
    Warehouse,
)
from .bom_service import get_bom_materials, calculate_material_requirements_for_production_order


def calculate_btp_demand_from_product(
    db: Session, product_id, planned_qty: float
) -> list[dict]:
    """
    Tính nhu cầu BTP từ sản phẩm.
    
    Logic:
    - Từ LSX sản phẩm → đọc BomSemiProduct → tính nhu cầu BTP
    - Đệ quy nếu BTP cần BTP khác
    - Tính số mẻ BTP cần dựa trên quy cách mẻ
    
    Args:
        db: Database session
        product_id: ID sản phẩm
        planned_qty: Số lượng sản phẩm cần sản xuất
    
    Returns:
        List of dict với thông tin BTP cần:
        [
            {
                "btp_id": "...",
                "btp_code": "...",
                "btp_name": "...",
                "required_qty": 100,
                "batch_count": 5,
                "uom": "kg"
            }
        ]
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Sản phẩm không tồn tại: {product_id}")
    
    btp_demand: dict[str, dict] = {}
    
    # Lấy các BTP từ BomSemiProduct
    semi_products = (
        db.query(BomSemiProduct, Product)
        .join(Product, BomSemiProduct.component_id == Product.id)
        .filter(BomSemiProduct.semi_product_id == product_id)
        .all()
    )
    
    for bom_semi, component in semi_products:
        if component.group != "BTP":
            continue
        
        component_id = str(component.id)
        required_qty = planned_qty * float(bom_semi.quantity)
        
        # Tính số mẻ BTP cần
        batch_spec = component.batch_spec
        batch_count = 1.0
        if batch_spec:
            try:
                import re
                import math
                match = re.search(r'(\d+(?:\.\d+)?)', str(batch_spec))
                if match:
                    batch_size = float(match.group(1))
                    if batch_size > 0:
                        batch_count = math.ceil(required_qty / batch_size)
            except (ValueError, TypeError):
                pass
        
        # Đệ quy: tính BTP con nếu có
        child_btp_demand = calculate_btp_demand_from_product(db, component.id, required_qty)
        
        # Cộng dồn nhu cầu BTP
        if component_id in btp_demand:
            btp_demand[component_id]["required_qty"] += required_qty
            btp_demand[component_id]["batch_count"] = max(
                btp_demand[component_id]["batch_count"],
                batch_count
            )
        else:
            btp_demand[component_id] = {
                "btp_id": component_id,
                "btp_code": component.code,
                "btp_name": component.name,
                "required_qty": required_qty,
                "batch_count": batch_count,
                "uom": bom_semi.uom,
            }
        
        # Thêm BTP con vào demand
        for child_btp in child_btp_demand:
            child_id = child_btp["btp_id"]
            if child_id in btp_demand:
                btp_demand[child_id]["required_qty"] += child_btp["required_qty"]
                btp_demand[child_id]["batch_count"] = max(
                    btp_demand[child_id]["batch_count"],
                    child_btp["batch_count"]
                )
            else:
                btp_demand[child_id] = child_btp
    
    return list(btp_demand.values())


def calculate_material_requirement_plan(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    deduct_stock: bool = True,
) -> list[dict]:
    """
    Dự trù NVL từ tất cả LSX trong khoảng thời gian.
    
    Logic theo PRD section 3.1.3 step 6:
    - Từ tất cả LSX trong khoảng thời gian
    - Tính tổng nhu cầu NVL theo từng loại
    - Trừ tồn kho NVL hiện có (nếu deduct_stock=True)
    
    Args:
        db: Database session
        start_date: Ngày bắt đầu
        end_date: Ngày kết thúc
        deduct_stock: Có trừ tồn kho không
    
    Returns:
        List of dict với dự trù NVL:
        [
            {
                "material_id": "...",
                "material_code": "...",
                "material_name": "...",
                "total_required_qty": 1000,
                "available_stock": 200,
                "net_required_qty": 800,
                "uom": "kg"
            }
        ]
    """
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    # Lấy tất cả LSX trong khoảng thời gian
    production_orders = (
        db.query(ProductionOrder)
        .filter(
            ProductionOrder.production_date >= start_date,
            ProductionOrder.production_date <= end_date,
        )
        .all()
    )
    
    # Tổng hợp nhu cầu NVL từ tất cả LSX
    material_requirements: dict[str, dict] = {}
    
    for po in production_orders:
        try:
            materials = calculate_material_requirements_for_production_order(db, po.id)
            for mat in materials:
                material_id = mat["material_id"]
                if material_id in material_requirements:
                    material_requirements[material_id]["total_required_qty"] += mat["required_quantity"]
                else:
                    material_requirements[material_id] = {
                        "material_id": material_id,
                        "material_code": mat["material_code"],
                        "material_name": mat["material_name"],
                        "total_required_qty": mat["required_quantity"],
                        "uom": mat["uom"],
                    }
        except Exception:
            # Bỏ qua nếu LSX không có BOM hoặc lỗi
            continue
    
    # Trừ tồn kho nếu cần
    result = []
    for material_id, req in material_requirements.items():
        available_stock = 0.0
        if deduct_stock:
            # Lấy tồn kho từ tất cả kho NVL
            stock = (
                db.query(func.sum(InventorySnapshot.current_qty))
                .join(Warehouse, InventorySnapshot.warehouse_id == Warehouse.id)
                .filter(
                    InventorySnapshot.product_id == material_id,
                    Warehouse.type == "NVL",
                )
                .scalar()
            )
            available_stock = float(stock or 0.0)
        
        net_required_qty = max(0.0, req["total_required_qty"] - available_stock)
        
        result.append({
            "material_id": req["material_id"],
            "material_code": req["material_code"],
            "material_name": req["material_name"],
            "total_required_qty": req["total_required_qty"],
            "available_stock": available_stock,
            "net_required_qty": net_required_qty,
            "uom": req["uom"],
        })
    
    return result


def create_pivot_material_plan(
    db: Session, production_date: date
) -> dict:
    """
    Tạo pivot table kế hoạch vật tư theo ngày sản xuất.
    
    Logic:
    - Gọi calculate_material_requirement_plan với start_date = end_date = production_date
    - Group kết quả theo material_id, material_name, uom
    - Sum: required_quantity, total_cost
    
    Args:
        db: Database session
        production_date: Ngày sản xuất
    
    Returns:
        Dict với format tương tự pivot BOM LSX:
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
    # Gọi calculate_material_requirement_plan với cùng ngày
    requirements = calculate_material_requirement_plan(
        db, production_date, production_date, deduct_stock=False
    )
    
    # Group theo material_id và sum
    material_aggregated: dict[str, dict] = {}
    
    for req in requirements:
        material_id = req.get("material_id")
        if not material_id:
            continue
        
        material_id_str = str(material_id)
        if material_id_str not in material_aggregated:
            material_aggregated[material_id_str] = {
                "material_id": material_id_str,
                "material_code": req.get("material_code", ""),
                "material_name": req.get("material_name", ""),
                "uom": req.get("uom", ""),
                "total_quantity": 0.0,
                "total_cost": 0.0,
            }
        
        # Sum các giá trị
        material_aggregated[material_id_str]["total_quantity"] += req.get("total_required_qty", 0.0)
        # Note: calculate_material_requirement_plan không trả về total_cost,
        # nên có thể cần tính lại hoặc để 0
        # material_aggregated[material_id_str]["total_cost"] += req.get("total_cost", 0.0)
    
    return {
        "production_date": production_date.isoformat(),
        "items": list(material_aggregated.values()),
    }


def get_production_planning_summary(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """
    Tổng hợp kế hoạch sản xuất.
    
    Args:
        db: Database session
        start_date: Ngày bắt đầu
        end_date: Ngày kết thúc
    
    Returns:
        Dict với tổng hợp:
        {
            "period": {"start": "...", "end": "..."},
            "total_orders": 10,
            "total_products": 5,
            "material_requirements": [...],
            "btp_requirements": [...]
        }
    """
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    # Thống kê LSX
    production_orders = (
        db.query(ProductionOrder)
        .filter(
            ProductionOrder.production_date >= start_date,
            ProductionOrder.production_date <= end_date,
        )
        .all()
    )
    
    # Đếm số sản phẩm khác nhau
    product_ids = set(str(po.product_id) for po in production_orders)
    
    # Tính dự trù NVL
    material_requirements = calculate_material_requirement_plan(
        db, start_date, end_date, deduct_stock=True
    )
    
    # Tính nhu cầu BTP (từ tất cả LSX sản phẩm)
    btp_requirements_map: dict[str, dict] = {}
    for po in production_orders:
        product = db.query(Product).filter(Product.id == po.product_id).first()
        if not product or product.group != "TP":
            continue
        
        try:
            btp_demand = calculate_btp_demand_from_product(
                db, po.product_id, float(po.planned_qty)
            )
            for btp in btp_demand:
                btp_id = btp["btp_id"]
                if btp_id in btp_requirements_map:
                    btp_requirements_map[btp_id]["required_qty"] += btp["required_qty"]
                else:
                    btp_requirements_map[btp_id] = btp
        except Exception:
            continue
    
    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "total_orders": len(production_orders),
        "total_products": len(product_ids),
        "material_requirements": material_requirements,
        "btp_requirements": list(btp_requirements_map.values()),
        "total_materials_needed": len(material_requirements),
        "total_btp_needed": len(btp_requirements_map),
    }

