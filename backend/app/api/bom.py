"""
API endpoints cho BOM (Bill of Materials) Management.

Bao gồm:
- Xem BOM của sản phẩm
- Thêm/sửa/xóa NVL trong BOM
- Tính toán nhu cầu NVL từ LSX
- Tính giá vốn từ BOM
"""

from __future__ import annotations

import json
from datetime import date

from robyn import Request, Response

from ..core.db import get_session
from ..models.entities import Product, BomMaterial, BomSemiProduct, BomLabor
from ..services.bom_service import (
    get_bom_materials,
    get_bom_semi_products,
    calculate_material_requirements_for_production_order,
    calculate_product_cost_from_bom,
    recalculate_product_cost_on_material_price_change,
)


def json_response(data: object, status_code: int = 200) -> Response:
    return Response(
        status_code=status_code,
        headers={"Content-Type": "application/json"},
        body=json.dumps(data, default=str),
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def get_product_bom(product_id: str, request: Request) -> Response:  # type: ignore[override]
    """
    GET /api/bom/products/{product_id}
    
    Lấy BOM của sản phẩm bao gồm:
    - NVL (BomMaterial)
    - BTP components (BomSemiProduct)
    - Nhân công (BomLabor)
    """
    try:
        import uuid
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        return json_response({"error": "ID sản phẩm không hợp lệ"}, 400)
    
    effective_date = None
    if "effective_date" in request.query_params:
        try:
            effective_date = _parse_date(request.query_params["effective_date"])
        except ValueError:
            return json_response({"error": "effective_date không đúng định dạng YYYY-MM-DD"}, 400)
    
    with get_session() as db:
        product = db.query(Product).filter(Product.id == product_uuid).first()
        if not product:
            return json_response({"error": "Sản phẩm không tồn tại"}, 404)
        
        materials = get_bom_materials(db, product_uuid, effective_date)
        semi_products = get_bom_semi_products(db, product_uuid)
        
        # Lấy nhân công
        labor_rows = (
            db.query(BomLabor)
            .filter(BomLabor.product_id == product_uuid)
            .all()
        )
        labor = [
            {
                "id": str(l.id),
                "equipment": l.equipment,
                "labor_type": l.labor_type,
                "quantity": float(l.quantity) if l.quantity else None,
                "duration_minutes": l.duration_minutes,
                "unit_cost": float(l.unit_cost) if l.unit_cost else None,
            }
            for l in labor_rows
        ]
        
        return json_response({
            "product_id": product_id,
            "product_code": product.code,
            "product_name": product.name,
            "materials": materials,
            "semi_products": semi_products,
            "labor": labor,
        })


def add_material_to_bom(product_id: str, request: Request) -> Response:  # type: ignore[override]
    """
    POST /api/bom/products/{product_id}/materials
    
    Thêm NVL vào BOM của sản phẩm.
    
    Payload:
    {
      "material_code": "NVL001",
      "quantity": 10.5,
      "uom": "kg",
      "cost": 50000,
      "effective_date": "2025-01-01"  // optional
    }
    """
    try:
        import uuid
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        return json_response({"error": "ID sản phẩm không hợp lệ"}, 400)
    
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return json_response({"error": "Body không phải JSON hợp lệ"}, 400)
    
    required_fields = ["material_code", "quantity", "uom"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )
    
    with get_session() as db:
        product = db.query(Product).filter(Product.id == product_uuid).first()
        if not product:
            return json_response({"error": "Sản phẩm không tồn tại"}, 404)
        
        material = (
            db.query(Product)
            .filter(Product.code == data["material_code"])
            .first()
        )
        if not material:
            return json_response({"error": "Vật tư không tồn tại"}, 400)
        
        effective_date = None
        if "effective_date" in data:
            try:
                effective_date = _parse_date(data["effective_date"])
            except ValueError:
                return json_response(
                    {"error": "effective_date không đúng định dạng YYYY-MM-DD"}, 400
                )
        
        bom_material = BomMaterial(
            product_id=product_uuid,
            material_id=material.id,
            quantity=float(data["quantity"]),
            uom=data["uom"],
            cost=float(data["cost"]) if "cost" in data else None,
            effective_date=effective_date,
        )
        db.add(bom_material)
        db.flush()
        
        return json_response(
            {
                "id": str(bom_material.id),
                "material_code": material.code,
                "material_name": material.name,
                "quantity": float(bom_material.quantity),
                "uom": bom_material.uom,
            },
            201,
        )


def get_material_requirements_for_production_order(
    order_id: str, request: Request
) -> Response:  # type: ignore[override]
    """
    GET /api/bom/production-orders/{order_id}/material-requirements
    
    Tính toán nhu cầu NVL từ LSX.
    
    Returns:
    {
      "production_order_id": "...",
      "product_name": "...",
      "planned_qty": 100,
      "materials": [
        {
          "material_code": "NVL001",
          "required_quantity": 50,
          "uom": "kg",
          ...
        }
      ]
    }
    """
    try:
        import uuid
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        return json_response({"error": "ID lệnh sản xuất không hợp lệ"}, 400)
    
    try:
        with get_session() as db:
            from ..models.entities import ProductionOrder
            
            production_order = db.query(ProductionOrder).filter(ProductionOrder.id == order_uuid).first()
            if not production_order:
                return json_response({"error": "Lệnh sản xuất không tồn tại"}, 404)
            
            materials = calculate_material_requirements_for_production_order(db, order_uuid)
            
            return json_response({
                "production_order_id": order_id,
                "production_order_business_id": production_order.business_id,
                "product_name": production_order.product_name,
                "planned_qty": float(production_order.planned_qty),
                "production_date": production_order.production_date.isoformat(),
                "materials": materials,
                "total_materials": len(materials),
            })
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tính toán nhu cầu NVL: {str(e)}"}, 500
        )


def get_product_cost_calculation(
    product_id: str, request: Request
) -> Response:  # type: ignore[override]
    """
    GET /api/bom/products/{product_id}/cost-calculation
    
    Tính giá vốn sản phẩm từ BOM.
    
    Query params:
    - pricing_date: YYYY-MM-DD (optional, default: today)
    
    Returns:
    {
      "product_code": "...",
      "total_cost": 100000,
      "material_details": [...],
      "labor_details": [...]
    }
    """
    try:
        import uuid
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        return json_response({"error": "ID sản phẩm không hợp lệ"}, 400)
    
    pricing_date = None
    if "pricing_date" in request.query_params:
        try:
            pricing_date = _parse_date(request.query_params["pricing_date"])
        except ValueError:
            return json_response(
                {"error": "pricing_date không đúng định dạng YYYY-MM-DD"}, 400
            )
    
    try:
        with get_session() as db:
            cost_data = calculate_product_cost_from_bom(db, product_uuid, pricing_date)
            return json_response(cost_data)
    except ValueError as e:
        return json_response({"error": str(e)}, 404)
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tính giá vốn: {str(e)}"}, 500
        )


def recalculate_costs(material_id: str, request: Request) -> Response:  # type: ignore[override]
    """
    POST /api/bom/recalculate-costs/:material_id
    
    Tự động tính lại giá vốn cho tất cả sản phẩm/BTP sử dụng vật tư này.
    
    Endpoint này nên được gọi sau khi tạo/cập nhật MaterialPriceHistory.
    """
    try:
        import uuid
        material_uuid = uuid.UUID(material_id)
    except ValueError:
        return json_response({"error": "ID vật tư không hợp lệ"}, 400)
    
    try:
        with get_session() as db:
            result = recalculate_product_cost_on_material_price_change(db, material_uuid)
            db.commit()
            
            return json_response(result, 200)
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tính lại giá vốn: {str(e)}"}, 500
        )

