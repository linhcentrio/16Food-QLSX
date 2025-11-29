"""
API cho Module Giao Vận (Logistics).
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime

from robyn import Request, Response

from ..core.db import get_session
from ..core.error_handler import json_response as _json_response, ValidationError, NotFoundError
from ..models.logistics import DeliveryVehicle, Delivery, DeliveryLine
from ..models.entities import SalesOrder, Product


def _parse_date(value: str) -> date:
    """Parse date từ string."""
    return date.fromisoformat(value)


# Delivery Vehicle APIs
def list_delivery_vehicles(request: Request) -> Response:
    """GET /api/logistics/vehicles - Danh sách phương tiện giao hàng."""
    status = request.query_params.get("status")

    with get_session() as db:
        query = db.query(DeliveryVehicle)

        if status:
            query = query.filter(DeliveryVehicle.status == status)

        vehicles = query.order_by(DeliveryVehicle.code).all()

        data = [
            {
                "id": str(v.id),
                "code": v.code,
                "license_plate": v.license_plate,
                "vehicle_type": v.vehicle_type,
                "driver_name": v.driver_name,
                "driver_phone": v.driver_phone,
                "capacity_kg": float(v.capacity_kg) if v.capacity_kg else None,
                "status": v.status,
            }
            for v in vehicles
        ]

        return _json_response(data)


def create_delivery_vehicle(request: Request) -> Response:
    """POST /api/logistics/vehicles - Tạo phương tiện giao hàng mới."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["code", "license_plate", "vehicle_type"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        existing = (
            db.query(DeliveryVehicle)
            .filter(DeliveryVehicle.code == data["code"])
            .first()
        )
        if existing:
            return _json_response({"error": "Mã phương tiện đã tồn tại"}, 400)

        existing_plate = (
            db.query(DeliveryVehicle)
            .filter(DeliveryVehicle.license_plate == data["license_plate"])
            .first()
        )
        if existing_plate:
            return _json_response({"error": "Biển số xe đã tồn tại"}, 400)

        vehicle = DeliveryVehicle(
            code=data["code"],
            license_plate=data["license_plate"],
            vehicle_type=data["vehicle_type"],
            driver_name=data.get("driver_name"),
            driver_phone=data.get("driver_phone"),
            capacity_kg=float(data["capacity_kg"]) if data.get("capacity_kg") else None,
            status=data.get("status", "available"),
            note=data.get("note"),
        )
        db.add(vehicle)
        db.flush()

        return _json_response({
            "id": str(vehicle.id),
            "code": vehicle.code,
            "license_plate": vehicle.license_plate,
        }, 201)


# Delivery APIs
def list_deliveries(request: Request) -> Response:
    """GET /api/logistics/deliveries - Danh sách phiếu giao hàng."""
    sales_order_id = request.query_params.get("sales_order_id")
    status = request.query_params.get("status")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    start_date = None
    if start_date_str:
        try:
            start_date = _parse_date(start_date_str)
        except ValueError:
            return _json_response({"error": "Invalid start_date format"}, 400)

    end_date = None
    if end_date_str:
        try:
            end_date = _parse_date(end_date_str)
        except ValueError:
            return _json_response({"error": "Invalid end_date format"}, 400)

    with get_session() as db:
        query = (
            db.query(Delivery, SalesOrder, DeliveryVehicle)
            .join(SalesOrder, Delivery.sales_order_id == SalesOrder.id)
            .outerjoin(DeliveryVehicle, Delivery.vehicle_id == DeliveryVehicle.id)
        )

        if sales_order_id:
            try:
                so_id = uuid.UUID(sales_order_id)
                query = query.filter(Delivery.sales_order_id == so_id)
            except ValueError:
                return _json_response({"error": "Invalid sales_order_id"}, 400)

        if status:
            query = query.filter(Delivery.status == status)
        if start_date:
            query = query.filter(Delivery.planned_delivery_date >= start_date)
        if end_date:
            query = query.filter(Delivery.planned_delivery_date <= end_date)

        rows = query.order_by(Delivery.planned_delivery_date.desc()).limit(100).all()

        data = [
            {
                "id": str(delivery.id),
                "code": delivery.code,
                "sales_order_code": so.code,
                "planned_delivery_date": delivery.planned_delivery_date.isoformat(),
                "actual_delivery_date": delivery.actual_delivery_date.isoformat()
                if delivery.actual_delivery_date
                else None,
                "vehicle_license_plate": vehicle.license_plate if vehicle else None,
                "driver_name": delivery.driver_name,
                "status": delivery.status,
            }
            for delivery, so, vehicle in rows
        ]

        return _json_response(data)


def create_delivery(request: Request) -> Response:
    """POST /api/logistics/deliveries - Tạo phiếu giao hàng."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["sales_order_id", "planned_delivery_date", "lines"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    if not isinstance(data["lines"], list) or not data["lines"]:
        return _json_response({"error": "Phiếu phải có ít nhất 1 dòng"}, 400)

    with get_session() as db:
        try:
            so_id = uuid.UUID(data["sales_order_id"])
            sales_order = db.query(SalesOrder).filter(SalesOrder.id == so_id).first()
            if not sales_order:
                return _json_response({"error": "Đơn hàng không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid sales_order_id"}, 400)

        planned_delivery_date = _parse_date(data["planned_delivery_date"])

        count_today = (
            db.query(Delivery)
            .filter(Delivery.planned_delivery_date == planned_delivery_date)
            .count()
        )
        code = f"GH{planned_delivery_date.strftime('%Y%m%d')}-{count_today + 1:03d}"

        vehicle_id = None
        if data.get("vehicle_id"):
            try:
                vehicle_id = uuid.UUID(data["vehicle_id"])
            except ValueError:
                return _json_response({"error": "Invalid vehicle_id"}, 400)

        delivery = Delivery(
            code=code,
            sales_order_id=so_id,
            vehicle_id=vehicle_id,
            planned_delivery_date=planned_delivery_date,
            delivery_address=data.get("delivery_address"),
            contact_person=data.get("contact_person"),
            contact_phone=data.get("contact_phone"),
            driver_name=data.get("driver_name"),
            status=data.get("status", "planned"),
            delivery_notes=data.get("delivery_notes"),
            signature_url=data.get("signature_url"),
        )
        db.add(delivery)
        db.flush()

        # Tạo các dòng giao hàng
        for line_data in data["lines"]:
            product_code = line_data.get("product_code")
            if not product_code:
                continue

            product = (
                db.query(Product).filter(Product.code == product_code).first()
            )
            if not product:
                continue

            line = DeliveryLine(
                delivery_id=delivery.id,
                product_id=product.id,
                product_name=product.name,
                quantity=float(line_data.get("quantity", 0)),
                delivered_quantity=0,
                uom=line_data.get("uom") or product.main_uom,
                note=line_data.get("note"),
            )
            db.add(line)

        return _json_response({
            "id": str(delivery.id),
            "code": delivery.code,
        }, 201)


def update_delivery_status(delivery_id: str, request: Request) -> Response:
    """PUT /api/logistics/deliveries/:id/status - Cập nhật trạng thái giao hàng."""
    try:
        del_id = uuid.UUID(delivery_id)
    except ValueError:
        return _json_response({"error": "Invalid delivery_id"}, 400)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    with get_session() as db:
        delivery = db.query(Delivery).filter(Delivery.id == del_id).first()
        if not delivery:
            return _json_response({"error": "Phiếu giao hàng không tồn tại"}, 404)

        if "status" in data:
            delivery.status = data["status"]

        if "actual_delivery_date" in data:
            try:
                delivery.actual_delivery_date = _parse_date(data["actual_delivery_date"])
            except ValueError:
                return _json_response({"error": "Invalid actual_delivery_date format"}, 400)

        if "delivered_quantities" in data:
            # Cập nhật số lượng đã giao cho từng dòng
            for line_data in data["delivered_quantities"]:
                product_code = line_data.get("product_code")
                delivered_qty = float(line_data.get("delivered_quantity", 0))

                product = (
                    db.query(Product).filter(Product.code == product_code).first()
                )
                if not product:
                    continue

                line = (
                    db.query(DeliveryLine)
                    .filter(
                        DeliveryLine.delivery_id == del_id,
                        DeliveryLine.product_id == product.id,
                    )
                    .first()
                )
                if line:
                    line.delivered_quantity = delivered_qty

        return _json_response({
            "id": str(delivery.id),
            "code": delivery.code,
            "status": delivery.status,
        })

