"""
Service xử lý business logic cho BOM (Bill of Materials).

Bao gồm:
- Tính toán nhu cầu NVL từ LSX
- Tính giá vốn từ BOM
- Xử lý BOM đa cấp (BTP → NVL)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.entities import (
    Product,
    ProductionOrder,
    BomMaterial,
    BomSemiProduct,
    BomLabor,
    MaterialPriceHistory,
)


def get_bom_materials(
    db: Session, product_id, effective_date: date | None = None
) -> list[dict]:
    """
    Lấy danh sách NVL trong BOM của sản phẩm.
    
    Args:
        db: Database session
        product_id: ID sản phẩm
        effective_date: Ngày hiệu lực (lấy BOM có ngày <= effective_date, mới nhất)
    
    Returns:
        List of dict với thông tin NVL và định mức
    """
    query = db.query(BomMaterial, Product).join(
        Product, BomMaterial.material_id == Product.id
    ).filter(BomMaterial.product_id == product_id)
    
    if effective_date:
        query = query.filter(
            (BomMaterial.effective_date <= effective_date) | (BomMaterial.effective_date.is_(None))
        )
    
    rows = query.order_by(BomMaterial.effective_date.desc().nullslast()).all()
    
    # Nhóm theo material_id, lấy bản ghi có effective_date mới nhất
    materials_map = {}
    for bom_material, material in rows:
        material_id = str(material.id)
        if material_id not in materials_map:
            materials_map[material_id] = {
                "material_id": material_id,
                "material_code": material.code,
                "material_name": material.name,
                "quantity": float(bom_material.quantity),
                "uom": bom_material.uom,
                "cost": float(bom_material.cost) if bom_material.cost else None,
                "effective_date": bom_material.effective_date.isoformat() if bom_material.effective_date else None,
            }
    
    return list(materials_map.values())


def get_bom_semi_products(db: Session, product_id) -> list[dict]:
    """
    Lấy danh sách BTP/component trong BOM của sản phẩm.
    
    Args:
        db: Database session
        product_id: ID sản phẩm (BTP)
    
    Returns:
        List of dict với thông tin BTP component
    """
    rows = (
        db.query(BomSemiProduct, Product)
        .join(Product, BomSemiProduct.component_id == Product.id)
        .filter(BomSemiProduct.semi_product_id == product_id)
        .order_by(BomSemiProduct.operation_sequence.asc().nullslast())
        .all()
    )
    
    return [
        {
            "component_id": str(component.id),
            "component_code": component.code,
            "component_name": component.name,
            "quantity": float(bom_semi.quantity),
            "uom": bom_semi.uom,
            "operation_sequence": bom_semi.operation_sequence,
        }
        for bom_semi, component in rows
    ]


def get_material_price(
    db: Session, material_id, pricing_date: date | None = None
) -> float | None:
    """
    Lấy giá NVL mới nhất từ MaterialPriceHistory.
    
    Args:
        db: Database session
        material_id: ID NVL
        pricing_date: Ngày định giá (mặc định: hôm nay)
    
    Returns:
        Giá NVL hoặc None nếu không tìm thấy
    """
    if not pricing_date:
        pricing_date = date.today()
    
    price_row = (
        db.query(MaterialPriceHistory)
        .filter(
            MaterialPriceHistory.material_id == material_id,
            MaterialPriceHistory.quoted_date <= pricing_date,
        )
        .order_by(MaterialPriceHistory.quoted_date.desc())
        .first()
    )
    
    return float(price_row.price) if price_row else None


def calculate_material_requirements_for_production_order(
    db: Session, production_order_id
) -> list[dict]:
    """
    Tính toán nhu cầu NVL từ LSX.
    
    Logic:
    1. Đọc LSX và số lượng sản xuất
    2. Đọc BOM vật tư (BomMaterial) của sản phẩm
    3. Xử lý BOM đa cấp (BTP → NVL) qua BomSemiProduct
    4. Tính số lượng NVL cần = số lượng sản phẩm × định mức BOM
    
    Args:
        db: Database session
        production_order_id: ID của ProductionOrder
    
    Returns:
        List of dict với thông tin NVL cần thiết
    """
    po = db.query(ProductionOrder).filter(ProductionOrder.id == production_order_id).first()
    if not po:
        raise ValueError(f"Lệnh sản xuất không tồn tại: {production_order_id}")
    
    product = db.query(Product).filter(Product.id == po.product_id).first()
    if not product:
        raise ValueError(f"Sản phẩm không tồn tại: {po.product_id}")
    
    planned_qty = float(po.planned_qty)
    
    # Tổng hợp NVL từ BOM trực tiếp và gián tiếp (qua BTP)
    material_requirements: dict[str, dict] = {}
    
    # Bước 1: Tính NVL trực tiếp từ BomMaterial
    bom_materials = get_bom_materials(db, po.product_id)
    for bom_item in bom_materials:
        material_id = bom_item["material_id"]
        required_qty = planned_qty * bom_item["quantity"]
        
        material_requirements[material_id] = {
            "material_id": material_id,
            "material_code": bom_item["material_code"],
            "material_name": bom_item["material_name"],
            "required_quantity": required_qty,
            "uom": bom_item["uom"],
            "unit_cost": bom_item["cost"],
            "total_cost": required_qty * (bom_item["cost"] or 0),
        }
    
    # Bước 2: Xử lý BTP (BomSemiProduct) - tính NVL gián tiếp
    semi_products = get_bom_semi_products(db, po.product_id)
    for semi_item in semi_products:
        component_id = semi_item["component_id"]
        required_btp_qty = planned_qty * semi_item["quantity"]
        
        # Đệ quy: tính NVL cần để sản xuất BTP này
        component_product = (
            db.query(Product).filter(Product.id == component_id).first()
        )
        if not component_product:
            continue
        
        # Nếu component là BTP, tính số mẻ cần sản xuất
        if component_product.group == "BTP":
            # Tính số mẻ BTP cần
            batch_spec = component_product.batch_spec
            if batch_spec:
                try:
                    import re
                    match = re.search(r'(\d+(?:\.\d+)?)', str(batch_spec))
                    if match:
                        batch_size = float(match.group(1))
                        if batch_size > 0:
                            # Số mẻ BTP cần = số lượng BTP cần / quy cách mẻ
                            batch_count = required_btp_qty / batch_size
                            # Tính NVL cho số mẻ BTP này
                            btp_materials = get_bom_materials(db, component_id)
                            for btp_bom_item in btp_materials:
                                mat_id = btp_bom_item["material_id"]
                                mat_qty_per_batch = btp_bom_item["quantity"]
                                total_mat_qty = batch_count * mat_qty_per_batch
                                
                                if mat_id in material_requirements:
                                    material_requirements[mat_id]["required_quantity"] += total_mat_qty
                                    material_requirements[mat_id]["total_cost"] += (
                                        total_mat_qty * (btp_bom_item["cost"] or 0)
                                    )
                                else:
                                    material_requirements[mat_id] = {
                                        "material_id": mat_id,
                                        "material_code": btp_bom_item["material_code"],
                                        "material_name": btp_bom_item["material_name"],
                                        "required_quantity": total_mat_qty,
                                        "uom": btp_bom_item["uom"],
                                        "unit_cost": btp_bom_item["cost"],
                                        "total_cost": total_mat_qty * (btp_bom_item["cost"] or 0),
                                    }
        else:
            # Component là NVL trực tiếp, cộng vào requirements
            if component_id in material_requirements:
                material_requirements[component_id]["required_quantity"] += required_btp_qty
            else:
                component_price = get_material_price(db, component_id)
                material_requirements[component_id] = {
                    "material_id": component_id,
                    "material_code": component_product.code,
                    "material_name": component_product.name,
                    "required_quantity": required_btp_qty,
                    "uom": semi_item["uom"],
                    "unit_cost": component_price,
                    "total_cost": required_btp_qty * (component_price or 0),
                }
    
    return list(material_requirements.values())


def calculate_product_cost_from_bom(
    db: Session, product_id, pricing_date: date | None = None
) -> dict:
    """
    Tính giá vốn sản phẩm từ BOM.
    
    Logic:
    - Giá vốn = SUM(material_quantity × material_price) + labor_cost
    - Lấy giá NVL từ MaterialPriceHistory (ưu tiên ngày mới nhất)
    
    Args:
        db: Database session
        product_id: ID sản phẩm
        pricing_date: Ngày định giá
    
    Returns:
        Dict với giá vốn chi tiết
    """
    if not pricing_date:
        pricing_date = date.today()
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Sản phẩm không tồn tại: {product_id}")
    
    total_material_cost = 0.0
    material_details = []
    
    # Tính giá vật tư
    bom_materials = get_bom_materials(db, product_id, pricing_date)
    for bom_item in bom_materials:
        material_price = bom_item.get("cost")
        if not material_price:
            material_price = get_material_price(db, bom_item["material_id"], pricing_date)
        
        quantity = bom_item["quantity"]
        unit_cost = material_price or 0.0
        line_cost = quantity * unit_cost
        total_material_cost += line_cost
        
        material_details.append({
            "material_code": bom_item["material_code"],
            "material_name": bom_item["material_name"],
            "quantity": quantity,
            "uom": bom_item["uom"],
            "unit_cost": unit_cost,
            "line_cost": line_cost,
        })
    
    # Tính giá nhân công
    labor_rows = (
        db.query(BomLabor)
        .filter(BomLabor.product_id == product_id)
        .all()
    )
    
    total_labor_cost = 0.0
    labor_details = []
    for labor in labor_rows:
        labor_cost = 0.0
        if labor.unit_cost and labor.duration_minutes:
            # Tính theo phút × đơn giá
            labor_cost = (labor.duration_minutes / 60.0) * float(labor.unit_cost)
        elif labor.unit_cost and labor.quantity:
            labor_cost = float(labor.quantity) * float(labor.unit_cost)
        
        total_labor_cost += labor_cost
        labor_details.append({
            "equipment": labor.equipment,
            "labor_type": labor.labor_type,
            "duration_minutes": labor.duration_minutes,
            "quantity": float(labor.quantity) if labor.quantity else None,
            "unit_cost": float(labor.unit_cost) if labor.unit_cost else None,
            "line_cost": labor_cost,
        })
    
    total_cost = total_material_cost + total_labor_cost
    
    return {
        "product_id": str(product_id),
        "product_code": product.code,
        "product_name": product.name,
        "pricing_date": pricing_date.isoformat(),
        "total_material_cost": total_material_cost,
        "total_labor_cost": total_labor_cost,
        "total_cost": total_cost,
        "material_details": material_details,
        "labor_details": labor_details,
    }


def recalculate_product_cost_on_material_price_change(
    db: Session, material_id
) -> dict:
    """
    Tự động tính lại giá vốn cho tất cả sản phẩm/BTP sử dụng vật tư này.
    
    Logic:
    - Tìm tất cả BomMaterial có material_id = material_id
    - Với mỗi BomMaterial, lấy product_id (sản phẩm/BTP sử dụng vật tư này)
    - Tính lại giá vốn cho từng sản phẩm:
      - Gọi calculate_product_cost_from_bom() với giá mới
      - Cập nhật Product.cost_price
    - Nếu sản phẩm là BTP, cần tính lại giá vốn cho các sản phẩm sử dụng BTP này (cascade)
    
    Args:
        db: Database session
        material_id: ID của vật tư đã thay đổi giá
    
    Returns:
        Dict với thông tin các sản phẩm đã được cập nhật:
        {
            "material_id": "...",
            "updated_products": [
                {
                    "product_id": "...",
                    "product_code": "...",
                    "old_cost_price": 100000.0,
                    "new_cost_price": 120000.0
                }
            ],
            "cascade_updated": [...]
        }
    """
    from ..models.entities import BomSemiProduct
    
    updated_products = []
    cascade_updated = []
    
    # Tìm tất cả sản phẩm/BTP sử dụng vật tư này
    bom_materials = (
        db.query(BomMaterial, Product)
        .join(Product, BomMaterial.product_id == Product.id)
        .filter(BomMaterial.material_id == material_id)
        .all()
    )
    
    if not bom_materials:
        return {
            "material_id": str(material_id),
            "updated_products": [],
            "cascade_updated": [],
        }
    
    # Tính lại giá vốn cho từng sản phẩm
    for bom_mat, product in bom_materials:
        try:
            # Tính giá vốn mới
            cost_data = calculate_product_cost_from_bom(db, product.id)
            new_cost_price = cost_data.get("total_cost", 0.0)
            
            old_cost_price = float(product.cost_price) if product.cost_price else None
            
            # Cập nhật cost_price
            product.cost_price = new_cost_price
            
            updated_products.append({
                "product_id": str(product.id),
                "product_code": product.code,
                "product_name": product.name,
                "old_cost_price": old_cost_price,
                "new_cost_price": new_cost_price,
            })
            
            # Nếu sản phẩm là BTP, cần tính lại giá vốn cho các sản phẩm sử dụng BTP này
            if product.group == "BTP":
                # Tìm các sản phẩm sử dụng BTP này
                products_using_btp = (
                    db.query(BomSemiProduct, Product)
                    .join(Product, BomSemiProduct.semi_product_id == Product.id)
                    .filter(BomSemiProduct.component_id == product.id)
                    .all()
                )
                
                for bom_semi, parent_product in products_using_btp:
                    try:
                        parent_cost_data = calculate_product_cost_from_bom(db, parent_product.id)
                        parent_new_cost = parent_cost_data.get("total_cost", 0.0)
                        parent_old_cost = float(parent_product.cost_price) if parent_product.cost_price else None
                        
                        parent_product.cost_price = parent_new_cost
                        
                        cascade_updated.append({
                            "product_id": str(parent_product.id),
                            "product_code": parent_product.code,
                            "product_name": parent_product.name,
                            "old_cost_price": parent_old_cost,
                            "new_cost_price": parent_new_cost,
                            "triggered_by_btp": product.code,
                        })
                    except Exception:
                        # Bỏ qua nếu có lỗi
                        continue
        except Exception:
            # Bỏ qua nếu có lỗi tính toán
            continue
    
    return {
        "material_id": str(material_id),
        "updated_products": updated_products,
        "cascade_updated": cascade_updated,
    }
