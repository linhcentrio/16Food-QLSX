"""
API cho module Đơn hàng.

Mục tiêu:
- Cung cấp endpoint JSON để tạo và xem đơn hàng.
- Áp dụng chính sách giá theo cấp khách hàng nếu có.
- Kiểm tra trùng đơn hàng cơ bản dựa trên KH + ngày + tổng tiền.
"""

from __future__ import annotations

import json
from datetime import date

from robyn import Request, Response

from ..core.db import get_session
from ..models.entities import SalesOrder, SalesOrderLine, Customer, Product, PricePolicy
from ..services.notification_service import (
    send_telegram_notification,
    format_order_notification,
)


def json_response(data: object, status_code: int = 200) -> Response:
    return Response(
        status_code=status_code,
        headers={"Content-Type": "application/json"},
        body=json.dumps(data, default=str),
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def list_orders() -> Response:
    """Trả về danh sách đơn hàng (JSON) đơn giản."""

    with get_session() as db:
        rows = (
            db.query(SalesOrder, Customer)
            .join(Customer, SalesOrder.customer_id == Customer.id)
            .order_by(SalesOrder.order_date.desc())
            .limit(100)
            .all()
        )

        data = [
            {
                "id": str(so.id),
                "code": so.code,
                "customer": cust.name,
                "order_date": so.order_date,
                "delivery_date": so.delivery_date,
                "status": so.status,
                "total_amount": float(so.total_amount or 0),
            }
            for so, cust in rows
        ]

    return json_response(data)


def create_order(request: Request) -> Response:  # type: ignore[override]
    """Tạo đơn hàng mới từ JSON body.

    Payload gợi ý:
    {
      "customer_code": "KH001",
      "order_date": "2025-01-01",
      "delivery_date": "2025-01-03",
      "lines": [
        {"product_code": "SP001", "quantity": 10},
        ...
      ]
    }
    """

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["customer_code", "order_date", "delivery_date", "lines"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    if not isinstance(data["lines"], list) or not data["lines"]:
        return json_response({"error": "Đơn hàng phải có ít nhất 1 dòng"}, 400)

    with get_session() as db:
        customer = (
            db.query(Customer).filter(Customer.code == data["customer_code"]).first()
        )
        if not customer:
            return json_response({"error": "Khách hàng không tồn tại"}, 400)

        order_date = _parse_date(data["order_date"])
        delivery_date = _parse_date(data["delivery_date"])

        # Tính tổng tiền và dòng chi tiết
        total_amount = 0.0
        line_entities: list[SalesOrderLine] = []

        for line in data["lines"]:
            product_code = line.get("product_code")
            quantity = float(line.get("quantity") or 0)
            if not product_code or quantity <= 0:
                continue

            product = db.query(Product).filter(Product.code == product_code).first()
            if not product:
                return json_response(
                    {"error": f"Sản phẩm không tồn tại: {product_code}"}, 400
                )

            # Lấy chính sách giá theo cấp khách hàng, ưu tiên ngày hiệu lực mới nhất
            price_row = (
                db.query(PricePolicy)
                .filter(
                    PricePolicy.product_id == product.id,
                    PricePolicy.customer_level == customer.level,
                    PricePolicy.effective_date <= order_date,
                )
                .order_by(PricePolicy.effective_date.desc())
                .first()
            )
            unit_price = float(price_row.price) if price_row else 0.0
            line_amount = unit_price * quantity
            total_amount += line_amount

            line_entities.append(
                SalesOrderLine(
                    product_id=product.id,
                    product_name=product.name,
                    uom=product.main_uom,
                    quantity=quantity,
                    unit_price=unit_price,
                    line_amount=line_amount,
                )
            )

        if not line_entities:
            return json_response({"error": "Không có dòng hợp lệ trong đơn hàng"}, 400)

        # Kiểm tra trùng đơn hàng cơ bản
        duplicate = (
            db.query(SalesOrder)
            .filter(
                SalesOrder.customer_id == customer.id,
                SalesOrder.order_date == order_date,
                SalesOrder.total_amount == total_amount,
            )
            .first()
        )
        if duplicate:
            return json_response(
                {
                    "error": "Đơn hàng có vẻ trùng (cùng KH, ngày đặt và tổng tiền).",
                    "existing_code": duplicate.code,
                },
                409,
            )

        # Sinh mã đơn hàng đơn giản DHyyyyMMdd-xxx
        count_today = (
            db.query(SalesOrder)
            .filter(SalesOrder.order_date == order_date)
            .count()
        )
        code = f"DH{order_date.strftime('%Y%m%d')}-{count_today + 1:03d}"

        order = SalesOrder(
            code=code,
            customer_id=customer.id,
            order_date=order_date,
            delivery_date=delivery_date,
            status="new",
            total_amount=total_amount,
            payment_status="unpaid",
        )

        db.add(order)
        db.flush()

        for line in line_entities:
            line.order_id = order.id
            db.add(line)
        
        db.commit()
        
        # Gửi thông báo Telegram (không fail nếu có lỗi)
        try:
            # Tổng hợp tên sản phẩm
            product_names = ", ".join([line.product_name for line in line_entities])
            total_qty = sum([float(line.quantity) for line in line_entities])
            
            message = format_order_notification(
                order_code=order.code,
                customer_name=customer.name,
                product_names=product_names,
                total_qty=total_qty,
                delivery_date=delivery_date.strftime("%d/%m/%Y %H:%M"),
                total_amount=total_amount,
                creator=None,  # Có thể lấy từ request nếu có authentication
            )
            
            send_telegram_notification(message)
        except Exception as e:
            # Log lỗi nhưng không fail request
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Không thể gửi thông báo Telegram: {str(e)}")

        return json_response(
            {
                "id": str(order.id),
                "code": order.code,
                "total_amount": total_amount,
                "status": order.status,
            },
            201,
        )


