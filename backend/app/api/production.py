"""
API/Service đơn giản cho module QLSX (KHSX ngày + Lệnh sản xuất).

Mục tiêu giai đoạn này:
- Cung cấp endpoint để xem nhanh KHSX ngày và LSX gần nhất.
- Tự động tạo LSX từ đơn hàng (UC-01).
"""

from __future__ import annotations

import json
from datetime import date

from robyn import Request, Response

from ..core.db import get_session
from ..models.entities import ProductionPlanDay, ProductionOrder, Product
from ..services.production_service import (
    generate_production_orders_from_sales_orders,
    create_pivot_bom_lsx,
    update_production_order_line,
    bulk_update_production_order_lines,
    create_manual_production_order,
)
from ..services.production_planning_service import (
    calculate_btp_demand_from_product,
    calculate_material_requirement_plan,
    get_production_planning_summary,
    create_pivot_material_plan,
)
from ..services.qr_service import (
    generate_qr_code_base64,
    generate_qr_code_data_url,
    create_production_order_qr_data,
)


def json_response(data: object, status_code: int = 200) -> Response:
    return Response(
        status_code=status_code,
        headers={"Content-Type": "application/json"},
        body=json.dumps(data, default=str),
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def list_daily_plan(target_date: date | None = None) -> Response:
    """Danh sách kế hoạch sản xuất theo ngày (KHSX ngày).

    Nếu không truyền ngày, lấy ngày hôm nay.
    """

    target_date = target_date or date.today()
    with get_session() as db:
        rows = (
            db.query(ProductionPlanDay, Product)
            .join(Product, ProductionPlanDay.product_id == Product.id)
            .filter(ProductionPlanDay.production_date == target_date)
            .order_by(Product.name)
            .all()
        )
        data = [
            {
                "product_code": p.code,
                "product_name": p.name,
                "planned_qty": float(plan.planned_qty),
                "ordered_qty": float(plan.ordered_qty),
                "remaining_qty": float(plan.remaining_qty),
                "capacity_max": float(plan.capacity_max),
            }
            for plan, p in rows
        ]

    return json_response(data)


def list_recent_production_orders(limit: int = 50) -> Response:
    """Danh sách LSX gần nhất."""

    with get_session() as db:
        rows = (
            db.query(ProductionOrder)
            .order_by(ProductionOrder.production_date.desc())
            .limit(limit)
            .all()
        )
        data = [
            {
                "business_id": o.business_id,
                "production_date": o.production_date,
                "product_name": o.product_name,
                "planned_qty": float(o.planned_qty),
                "completed_qty": float(o.completed_qty),
                "status": o.status,
            }
            for o in rows
        ]

    return json_response(data)


def create_production_orders_from_orders(request: Request) -> Response:  # type: ignore[override]
    """
    API: Tự động tạo LSX từ đơn hàng (UC-01).
    
    Payload (tùy chọn):
    {
      "start_date": "2025-01-01",  // mặc định: hôm nay
      "end_date": "2025-01-31",    // mặc định: +30 ngày
      "auto_deduct_stock": true    // mặc định: true
    }
    
    Returns:
    {
      "created_count": 5,
      "orders": [
        {
          "business_id": "LSX-20250101-001",
          "product_name": "...",
          "planned_qty": 100,
          ...
        }
      ]
    }
    """
    
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return json_response({"error": "Body không phải JSON hợp lệ"}, 400)
    
    start_date = None
    end_date = None
    auto_deduct_stock = data.get("auto_deduct_stock", True)
    
    if "start_date" in data:
        try:
            start_date = date.fromisoformat(data["start_date"])
        except ValueError:
            return json_response({"error": "start_date không đúng định dạng YYYY-MM-DD"}, 400)
    
    if "end_date" in data:
        try:
            end_date = date.fromisoformat(data["end_date"])
        except ValueError:
            return json_response({"error": "end_date không đúng định dạng YYYY-MM-DD"}, 400)
    
    try:
        with get_session() as db:
            created_orders = generate_production_orders_from_sales_orders(
                db, start_date, end_date, auto_deduct_stock
            )
            db.commit()
            
            orders_data = [
                {
                    "id": str(po.id),
                    "business_id": po.business_id,
                    "production_date": po.production_date.isoformat(),
                    "product_name": po.product_name,
                    "order_type": po.order_type,
                    "planned_qty": float(po.planned_qty),
                    "status": po.status,
                }
                for po in created_orders
            ]
            
            return json_response(
                {
                    "created_count": len(created_orders),
                    "orders": orders_data,
                },
                201,
            )
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tạo LSX: {str(e)}"},
            500,
        )


def get_material_requirement_plan(request: Request) -> Response:  # type: ignore[override]
    """
    GET /api/production/planning/material-requirement
    
    Lấy dự trù NVL từ tất cả LSX trong khoảng thời gian.
    
    Query params:
    - start_date: YYYY-MM-DD (optional, default: today)
    - end_date: YYYY-MM-DD (optional, default: +30 days)
    - deduct_stock: true/false (optional, default: true)
    """
    start_date = None
    end_date = None
    deduct_stock = True
    
    if "start_date" in request.query_params:
        try:
            start_date = date.fromisoformat(request.query_params["start_date"])
        except ValueError:
            return json_response(
                {"error": "start_date không đúng định dạng YYYY-MM-DD"}, 400
            )
    
    if "end_date" in request.query_params:
        try:
            end_date = date.fromisoformat(request.query_params["end_date"])
        except ValueError:
            return json_response(
                {"error": "end_date không đúng định dạng YYYY-MM-DD"}, 400
            )
    
    if "deduct_stock" in request.query_params:
        deduct_stock = request.query_params["deduct_stock"].lower() == "true"
    
    try:
        with get_session() as db:
            requirements = calculate_material_requirement_plan(
                db, start_date, end_date, deduct_stock
            )
            return json_response({
                "material_requirements": requirements,
                "total_materials": len(requirements),
            })
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tính dự trù NVL: {str(e)}"}, 500
        )


def calculate_btp_demand(request: Request) -> Response:  # type: ignore[override]
    """
    POST /api/production/planning/calculate-btp-demand
    
    Tính nhu cầu BTP từ LSX sản phẩm.
    
    Payload:
    {
      "product_id": "uuid",
      "planned_qty": 100
    }
    """
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return json_response({"error": "Body không phải JSON hợp lệ"}, 400)
    
    required_fields = ["product_id", "planned_qty"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )
    
    try:
        import uuid
        product_uuid = uuid.UUID(data["product_id"])
    except ValueError:
        return json_response({"error": "product_id không hợp lệ"}, 400)
    
    planned_qty = float(data.get("planned_qty", 0))
    if planned_qty <= 0:
        return json_response({"error": "planned_qty phải > 0"}, 400)
    
    try:
        with get_session() as db:
            btp_demand = calculate_btp_demand_from_product(
                db, product_uuid, planned_qty
            )
            return json_response({
                "product_id": data["product_id"],
                "planned_qty": planned_qty,
                "btp_requirements": btp_demand,
                "total_btp_types": len(btp_demand),
            })
    except ValueError as e:
        return json_response({"error": str(e)}, 404)
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tính nhu cầu BTP: {str(e)}"}, 500
        )


def get_production_planning_summary_api(request: Request) -> Response:  # type: ignore[override]
    """
    GET /api/production/planning/summary
    
    Tổng hợp kế hoạch sản xuất.
    
    Query params:
    - start_date: YYYY-MM-DD (optional, default: today)
    - end_date: YYYY-MM-DD (optional, default: +30 days)
    """
    start_date = None
    end_date = None
    
    if "start_date" in request.query_params:
        try:
            start_date = date.fromisoformat(request.query_params["start_date"])
        except ValueError:
            return json_response(
                {"error": "start_date không đúng định dạng YYYY-MM-DD"}, 400
            )
    
    if "end_date" in request.query_params:
        try:
            end_date = date.fromisoformat(request.query_params["end_date"])
        except ValueError:
            return json_response(
                {"error": "end_date không đúng định dạng YYYY-MM-DD"}, 400
            )
    
    try:
        with get_session() as db:
            summary = get_production_planning_summary(db, start_date, end_date)
            return json_response(summary)
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tổng hợp kế hoạch: {str(e)}"}, 500
        )


def get_production_order_qr_code(order_id: str, request: Request) -> Response:  # type: ignore[override]
    """
    GET /api/production/orders/{id}/qr-code
    
    Lấy QR code của LSX.
    
    Query params:
    - format: "base64" hoặc "data_url" (default: "data_url")
    - size: Kích thước QR code (1-40, default: 10)
    """
    try:
        import uuid
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        return json_response({"error": "ID lệnh sản xuất không hợp lệ"}, 400)
    
    format_type = request.query_params.get("format", "data_url")
    size = int(request.query_params.get("size", "10"))
    
    try:
        with get_session() as db:
            from ..models.entities import ProductionOrder
            
            po = db.query(ProductionOrder).filter(ProductionOrder.id == order_uuid).first()
            if not po:
                return json_response({"error": "Lệnh sản xuất không tồn tại"}, 404)
            
            qr_data = create_production_order_qr_data(
                production_order_id=str(po.id),
                business_id=po.business_id,
                production_date=po.production_date.isoformat(),
                product_name=po.product_name,
            )
            
            if format_type == "base64":
                qr_code = generate_qr_code_base64(qr_data, size=size)
                return json_response({
                    "qr_code": qr_code,
                    "format": "base64",
                })
            else:
                qr_code = generate_qr_code_data_url(qr_data, size=size)
                return json_response({
                    "qr_code": qr_code,
                    "format": "data_url",
                })
    except ImportError as e:
        return json_response(
            {"error": f"QR code library chưa được cài đặt: {str(e)}"}, 500
        )
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tạo QR code: {str(e)}"}, 500
        )


def get_pivot_bom_lsx(request: Request) -> Response:  # type: ignore[override]
    """
    GET /api/production/pivot/bom-lsx
    
    Tạo pivot table BOM LSX theo ngày sản xuất.
    
    Query params:
    - production_date: Ngày sản xuất (required, format: YYYY-MM-DD)
    """
    if "production_date" not in request.query_params:
        return json_response(
            {"error": "Thiếu tham số production_date"}, 400
        )
    
    try:
        production_date = _parse_date(request.query_params["production_date"])
    except ValueError:
        return json_response(
            {"error": "production_date không đúng định dạng YYYY-MM-DD"}, 400
        )
    
    try:
        with get_session() as db:
            result = create_pivot_bom_lsx(db, production_date)
            return json_response(result)
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tạo pivot BOM LSX: {str(e)}"}, 500
        )


def get_pivot_material_plan(request: Request) -> Response:  # type: ignore[override]
    """
    GET /api/production/pivot/material-plan
    
    Tạo pivot table kế hoạch vật tư theo ngày sản xuất.
    
    Query params:
    - production_date: Ngày sản xuất (required, format: YYYY-MM-DD)
    """
    if "production_date" not in request.query_params:
        return json_response(
            {"error": "Thiếu tham số production_date"}, 400
        )
    
    try:
        production_date = _parse_date(request.query_params["production_date"])
    except ValueError:
        return json_response(
            {"error": "production_date không đúng định dạng YYYY-MM-DD"}, 400
        )
    
    try:
        with get_session() as db:
            result = create_pivot_material_plan(db, production_date)
            return json_response(result)
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tạo pivot kế hoạch vật tư: {str(e)}"}, 500
        )


def update_production_order_line_api(order_id: str, line_id: str, request: Request) -> Response:  # type: ignore[override]
    """
    PUT /api/production/orders/{order_id}/lines/{line_id}
    
    Cập nhật ProductionOrderLine.
    
    Payload:
    {
      "planned_qty": 150.0,
      "note": "Điều chỉnh số lượng"
    }
    """
    try:
        import uuid
        order_uuid = uuid.UUID(order_id)
        line_uuid = uuid.UUID(line_id)
    except ValueError:
        return json_response({"error": "ID không hợp lệ"}, 400)
    
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return json_response({"error": "Body không phải JSON hợp lệ"}, 400)
    
    planned_qty = data.get("planned_qty")
    note = data.get("note")
    
    if planned_qty is None and note is None:
        return json_response({"error": "Phải có ít nhất một trường để cập nhật (planned_qty hoặc note)"}, 400)
    
    if planned_qty is not None:
        try:
            planned_qty = float(planned_qty)
        except (ValueError, TypeError):
            return json_response({"error": "planned_qty phải là số hợp lệ"}, 400)
    
    try:
        with get_session() as db:
            line = update_production_order_line(
                db, order_uuid, line_uuid, planned_qty, note
            )
            db.commit()
            
            return json_response({
                "id": str(line.id),
                "production_order_id": str(line.production_order_id),
                "planned_qty": float(line.planned_qty),
                "batch_count": float(line.batch_count) if line.batch_count else None,
                "note": line.note,
                "message": "Cập nhật thành công",
            })
    except ValueError as e:
        return json_response({"error": str(e)}, 404)
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi cập nhật ProductionOrderLine: {str(e)}"}, 500
        )


def bulk_update_production_order_lines_api(order_id: str, request: Request) -> Response:  # type: ignore[override]
    """
    PUT /api/production/orders/{order_id}/lines/bulk
    
    Cập nhật nhiều ProductionOrderLine cùng lúc.
    
    Payload:
    {
      "lines": [
        {"line_id": "uuid", "planned_qty": 100.0, "note": "..."},
        {"line_id": "uuid", "planned_qty": 200.0, "note": "..."}
      ]
    }
    """
    try:
        import uuid
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        return json_response({"error": "ID lệnh sản xuất không hợp lệ"}, 400)
    
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return json_response({"error": "Body không phải JSON hợp lệ"}, 400)
    
    if "lines" not in data:
        return json_response({"error": "Thiếu trường 'lines'"}, 400)
    
    if not isinstance(data["lines"], list) or not data["lines"]:
        return json_response({"error": "'lines' phải là mảng không rỗng"}, 400)
    
    try:
        with get_session() as db:
            updated_lines = bulk_update_production_order_lines(
                db, order_uuid, data["lines"]
            )
            db.commit()
            
            return json_response({
                "updated_count": len(updated_lines),
                "lines": [
                    {
                        "id": str(line.id),
                        "planned_qty": float(line.planned_qty),
                        "batch_count": float(line.batch_count) if line.batch_count else None,
                        "note": line.note,
                    }
                    for line in updated_lines
                ],
                "message": "Cập nhật thành công",
            })
    except ValueError as e:
        return json_response({"error": str(e)}, 400)
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi cập nhật ProductionOrderLines: {str(e)}"}, 500
        )


def create_manual_production_order_api(request: Request) -> Response:  # type: ignore[override]
    """
    POST /api/production/orders/manual
    
    Tạo lệnh sản xuất thủ công (không từ đơn hàng).
    
    Payload:
    {
      "production_date": "2025-01-15",
      "order_type": "SP",
      "product_id": "uuid",
      "planned_qty": 100.0,
      "note": "LSX thủ công"
    }
    """
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return json_response({"error": "Body không phải JSON hợp lệ"}, 400)
    
    required_fields = ["production_date", "order_type", "product_id", "planned_qty"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )
    
    try:
        import uuid
        production_date = _parse_date(data["production_date"])
        product_uuid = uuid.UUID(data["product_id"])
        order_type = data["order_type"]
        planned_qty = float(data["planned_qty"])
        note = data.get("note")
    except ValueError as e:
        return json_response({"error": f"Dữ liệu không hợp lệ: {str(e)}"}, 400)
    except (TypeError, KeyError) as e:
        return json_response({"error": f"Dữ liệu không hợp lệ: {str(e)}"}, 400)
    
    try:
        with get_session() as db:
            po = create_manual_production_order(
                db, production_date, order_type, product_uuid, planned_qty, note
            )
            db.commit()
            
            return json_response({
                "id": str(po.id),
                "business_id": po.business_id,
                "production_date": po.production_date.isoformat(),
                "order_type": po.order_type,
                "product_id": str(po.product_id),
                "product_name": po.product_name,
                "planned_qty": float(po.planned_qty),
                "status": po.status,
                "note": po.note,
                "message": "Tạo lệnh sản xuất thủ công thành công",
            }, 201)
    except ValueError as e:
        return json_response({"error": str(e)}, 400)
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tạo lệnh sản xuất: {str(e)}"}, 500
        )


