"""
API cho Module Thu Mua (Procurement).
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime

from robyn import Request, Response

from ..core.db import get_session
from ..core.error_handler import json_response as _json_response, ValidationError, NotFoundError
from ..models.procurement import (
    PurchaseRequest,
    PurchaseRequestLine,
    PurchaseOrder,
    PurchaseOrderLine,
)
from ..models.entities import Product, Supplier


def _parse_date(value: str) -> date:
    """Parse date từ string."""
    return date.fromisoformat(value)


# Purchase Request APIs
def list_purchase_requests(request: Request) -> Response:
    """GET /api/procurement/requests - Danh sách phiếu yêu cầu mua hàng."""
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
        query = db.query(PurchaseRequest)

        if status:
            query = query.filter(PurchaseRequest.status == status)
        if start_date:
            query = query.filter(PurchaseRequest.request_date >= start_date)
        if end_date:
            query = query.filter(PurchaseRequest.request_date <= end_date)

        requests = query.order_by(PurchaseRequest.request_date.desc()).limit(100).all()

        data = [
            {
                "id": str(req.id),
                "code": req.code,
                "request_date": req.request_date.isoformat(),
                "requested_by": req.requested_by,
                "department": req.department,
                "status": req.status,
                "total_amount": float(req.total_amount),
                "approved_by": req.approved_by,
                "approved_date": req.approved_date.isoformat() if req.approved_date else None,
            }
            for req in requests
        ]

        return _json_response(data)


def create_purchase_request(request: Request) -> Response:
    """POST /api/procurement/requests - Tạo phiếu yêu cầu mua hàng."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["request_date", "lines"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    if not isinstance(data["lines"], list) or not data["lines"]:
        return _json_response({"error": "Phiếu phải có ít nhất 1 dòng"}, 400)

    with get_session() as db:
        request_date = _parse_date(data["request_date"])

        count_today = (
            db.query(PurchaseRequest)
            .filter(PurchaseRequest.request_date == request_date)
            .count()
        )
        code = f"YCMH{request_date.strftime('%Y%m%d')}-{count_today + 1:03d}"

        purchase_request = PurchaseRequest(
            code=code,
            request_date=request_date,
            requested_by=data.get("requested_by"),
            department=data.get("department"),
            purpose=data.get("purpose"),
            status=data.get("status", "draft"),
            note=data.get("note"),
        )
        db.add(purchase_request)
        db.flush()

        total_amount = 0.0
        for line_data in data["lines"]:
            product_code = line_data.get("product_code")
            if not product_code:
                continue

            product = (
                db.query(Product).filter(Product.code == product_code).first()
            )
            if not product:
                continue

            quantity = float(line_data.get("quantity", 0))
            unit_price = float(line_data.get("estimated_unit_price", 0))
            line_amount = quantity * unit_price
            total_amount += line_amount

            required_date = None
            if line_data.get("required_date"):
                try:
                    required_date = _parse_date(line_data["required_date"])
                except ValueError:
                    pass

            line = PurchaseRequestLine(
                request_id=purchase_request.id,
                product_id=product.id,
                product_name=product.name,
                specification=line_data.get("specification"),
                quantity=quantity,
                uom=line_data.get("uom") or product.main_uom,
                estimated_unit_price=unit_price if unit_price > 0 else None,
                estimated_amount=line_amount,
                required_date=required_date,
                note=line_data.get("note"),
            )
            db.add(line)

        purchase_request.total_amount = total_amount

        return _json_response({
            "id": str(purchase_request.id),
            "code": purchase_request.code,
            "total_amount": float(total_amount),
        }, 201)


def approve_purchase_request(request_id: str, request: Request) -> Response:
    """POST /api/procurement/requests/:id/approve - Phê duyệt phiếu yêu cầu mua hàng."""
    try:
        req_id = uuid.UUID(request_id)
    except ValueError:
        return _json_response({"error": "Invalid request_id"}, 400)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    with get_session() as db:
        purchase_request = (
            db.query(PurchaseRequest).filter(PurchaseRequest.id == req_id).first()
        )
        if not purchase_request:
            return _json_response({"error": "Phiếu yêu cầu không tồn tại"}, 404)

        if purchase_request.status != "draft" and purchase_request.status != "pending":
            return _json_response(
                {"error": "Chỉ có thể phê duyệt phiếu ở trạng thái draft hoặc pending"}, 400
            )

        approved = data.get("approved", True)
        if approved:
            purchase_request.status = "approved"
            purchase_request.approved_by = data.get("approved_by")
            purchase_request.approved_date = date.today()
        else:
            purchase_request.status = "rejected"

        return _json_response({
            "id": str(purchase_request.id),
            "code": purchase_request.code,
            "status": purchase_request.status,
        })


# Purchase Order APIs
def list_purchase_orders(request: Request) -> Response:
    """GET /api/procurement/orders - Danh sách đơn mua hàng."""
    supplier_id = request.query_params.get("supplier_id")
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
        query = db.query(PurchaseOrder, Supplier).join(Supplier)

        if supplier_id:
            try:
                sup_id = uuid.UUID(supplier_id)
                query = query.filter(PurchaseOrder.supplier_id == sup_id)
            except ValueError:
                return _json_response({"error": "Invalid supplier_id"}, 400)

        if status:
            query = query.filter(PurchaseOrder.status == status)
        if start_date:
            query = query.filter(PurchaseOrder.order_date >= start_date)
        if end_date:
            query = query.filter(PurchaseOrder.order_date <= end_date)

        rows = query.order_by(PurchaseOrder.order_date.desc()).limit(100).all()

        data = [
            {
                "id": str(po.id),
                "code": po.code,
                "supplier_code": sup.code,
                "supplier_name": sup.name,
                "order_date": po.order_date.isoformat(),
                "expected_delivery_date": po.expected_delivery_date.isoformat()
                if po.expected_delivery_date
                else None,
                "status": po.status,
                "total_amount": float(po.total_amount),
                "payment_status": po.payment_status,
            }
            for po, sup in rows
        ]

        return _json_response(data)


def create_purchase_order(request: Request) -> Response:
    """POST /api/procurement/orders - Tạo đơn mua hàng."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["supplier_code", "order_date", "lines"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    if not isinstance(data["lines"], list) or not data["lines"]:
        return _json_response({"error": "Đơn phải có ít nhất 1 dòng"}, 400)

    with get_session() as db:
        supplier = (
            db.query(Supplier)
            .filter(Supplier.code == data["supplier_code"])
            .first()
        )
        if not supplier:
            return _json_response({"error": "Nhà cung cấp không tồn tại"}, 404)

        order_date = _parse_date(data["order_date"])

        count_today = (
            db.query(PurchaseOrder)
            .filter(PurchaseOrder.order_date == order_date)
            .count()
        )
        code = f"DMH{order_date.strftime('%Y%m%d')}-{count_today + 1:03d}"

        expected_delivery_date = None
        if data.get("expected_delivery_date"):
            try:
                expected_delivery_date = _parse_date(data["expected_delivery_date"])
            except ValueError:
                return _json_response({"error": "Invalid expected_delivery_date format"}, 400)

        purchase_request_id = None
        if data.get("purchase_request_id"):
            try:
                purchase_request_id = uuid.UUID(data["purchase_request_id"])
            except ValueError:
                return _json_response({"error": "Invalid purchase_request_id"}, 400)

        purchase_order = PurchaseOrder(
            code=code,
            purchase_request_id=purchase_request_id,
            supplier_id=supplier.id,
            order_date=order_date,
            expected_delivery_date=expected_delivery_date,
            status=data.get("status", "draft"),
            payment_status=data.get("payment_status", "unpaid"),
            note=data.get("note"),
        )
        db.add(purchase_order)
        db.flush()

        total_amount = 0.0
        for line_data in data["lines"]:
            product_code = line_data.get("product_code")
            if not product_code:
                continue

            product = (
                db.query(Product).filter(Product.code == product_code).first()
            )
            if not product:
                continue

            quantity = float(line_data.get("quantity", 0))
            unit_price = float(line_data.get("unit_price", 0))
            line_amount = quantity * unit_price
            total_amount += line_amount

            line = PurchaseOrderLine(
                order_id=purchase_order.id,
                product_id=product.id,
                product_name=product.name,
                specification=line_data.get("specification"),
                quantity=quantity,
                received_quantity=0,
                uom=line_data.get("uom") or product.main_uom,
                unit_price=unit_price,
                line_amount=line_amount,
                note=line_data.get("note"),
            )
            db.add(line)

        purchase_order.total_amount = total_amount

        return _json_response({
            "id": str(purchase_order.id),
            "code": purchase_order.code,
            "total_amount": float(total_amount),
        }, 201)


def get_purchase_history(request: Request) -> Response:
    """GET /api/procurement/history - Lịch sử mua hàng."""
    supplier_id = request.query_params.get("supplier_id")
    product_id = request.query_params.get("product_id")
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
            db.query(PurchaseOrderLine, PurchaseOrder, Supplier, Product)
            .join(PurchaseOrder, PurchaseOrderLine.order_id == PurchaseOrder.id)
            .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
            .join(Product, PurchaseOrderLine.product_id == Product.id)
            .filter(PurchaseOrder.status.in_(["received", "completed"]))
        )

        if supplier_id:
            try:
                sup_id = uuid.UUID(supplier_id)
                query = query.filter(PurchaseOrder.supplier_id == sup_id)
            except ValueError:
                return _json_response({"error": "Invalid supplier_id"}, 400)

        if product_id:
            try:
                prod_id = uuid.UUID(product_id)
                query = query.filter(PurchaseOrderLine.product_id == prod_id)
            except ValueError:
                return _json_response({"error": "Invalid product_id"}, 400)

        if start_date:
            query = query.filter(PurchaseOrder.order_date >= start_date)
        if end_date:
            query = query.filter(PurchaseOrder.order_date <= end_date)

        rows = query.order_by(PurchaseOrder.order_date.desc()).limit(500).all()

        data = [
            {
                "order_code": po.code,
                "order_date": po.order_date.isoformat(),
                "supplier_code": sup.code,
                "supplier_name": sup.name,
                "product_code": prod.code,
                "product_name": prod.name,
                "quantity": float(line.quantity),
                "received_quantity": float(line.received_quantity),
                "unit_price": float(line.unit_price),
                "line_amount": float(line.line_amount),
                "uom": line.uom,
            }
            for line, po, sup, prod in rows
        ]

        return _json_response({
            "total_records": len(data),
            "history": data,
        })

