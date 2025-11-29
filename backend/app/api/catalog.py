"""
API cho các danh mục cơ bản: sản phẩm, kho, khách hàng, nhà cung cấp.

Hiện tại implement đơn giản:
- List (GET)
- Tạo mới (POST, JSON body)

Sau này có thể bổ sung update/delete, filter nâng cao, phân trang.
"""

from __future__ import annotations

import json
import uuid
from datetime import date

from robyn import Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..core.db import get_session
from ..models.entities import Product, Warehouse, Customer, Supplier, PricePolicy


def json_response(data: object, status_code: int = 200) -> Response:
    return Response(
        status_code=status_code,
        headers={"Content-Type": "application/json"},
        body=json.dumps(data, default=str),
    )


def get_db() -> Session:
    # Helper nhỏ để lấy session (không dùng context manager cho đơn giản trong handler sync)
    return next(get_session().__enter__().__iter__())  # type: ignore[misc]


def list_products() -> Response:
    with get_session() as db:
        items = db.query(Product).limit(200).all()
        return json_response(
            [
                {
                    "id": str(p.id),
                    "code": p.code,
                    "name": p.name,
                    "group": p.group,
                    "main_uom": p.main_uom,
                }
                for p in items
            ]
        )


def list_customers() -> Response:
    """Danh sách khách hàng cơ bản."""

    with get_session() as db:
        items = db.query(Customer).limit(200).all()
        return json_response(
            [
                {
                    "id": str(c.id),
                    "code": c.code,
                    "name": c.name,
                    "level": c.level,
                    "channel": c.channel,
                }
                for c in items
            ]
        )


def create_customer(request: Request) -> Response:  # type: ignore[override]
    data = json.loads(request.body or "{}")
    required_fields = ["code", "name", "level", "channel"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        exists = db.query(Customer).filter(Customer.code == data["code"]).first()
        if exists:
            return json_response({"error": "Mã khách hàng đã tồn tại"}, 409)

        customer = Customer(
            code=data["code"],
            name=data["name"],
            level=data["level"],
            channel=data["channel"],
            phone=data.get("phone"),
            email=data.get("email"),
            address=data.get("address"),
        )
        db.add(customer)
        db.flush()
        return json_response(
            {
                "id": str(customer.id),
                "code": customer.code,
                "name": customer.name,
            },
            201,
        )


def list_price_policies() -> Response:
    """Danh sách chính sách giá theo sản phẩm + cấp KH."""

    with get_session() as db:
        rows = (
            db.query(PricePolicy, Product)
            .join(Product, PricePolicy.product_id == Product.id)
            .order_by(PricePolicy.effective_date.desc())
            .limit(500)
            .all()
        )
        data = [
            {
                "id": str(pp.id),
                "product_code": p.code,
                "product_name": p.name,
                "customer_level": pp.customer_level,
                "price": float(pp.price),
                "effective_date": pp.effective_date,
            }
            for pp, p in rows
        ]
        return json_response(data)


def create_price_policy(request: Request) -> Response:  # type: ignore[override]
    """Tạo mới chính sách giá cho 1 sản phẩm + cấp KH."""

    data = json.loads(request.body or "{}")
    required_fields = ["product_code", "customer_level", "price", "effective_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        product = (
            db.query(Product).filter(Product.code == data["product_code"]).first()
        )
        if not product:
            return json_response({"error": "Sản phẩm không tồn tại"}, 400)

        pp = PricePolicy(
            product_id=product.id,
            customer_level=data["customer_level"],
            price=float(data["price"]),
            effective_date=data["effective_date"],
        )
        db.add(pp)
        db.flush()
        return json_response(
            {
                "id": str(pp.id),
                "product_code": product.code,
                "customer_level": pp.customer_level,
                "price": float(pp.price),
            },
            201,
        )


def create_product(request: Request) -> Response:  # type: ignore[override]
    data = json.loads(request.body or "{}")
    required_fields = ["code", "name", "group", "main_uom"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return json_response(
            {"error": f"Missing fields: {', '.join(missing)}"}, status_code=400
        )

    with get_session() as db:
        product = Product(
            code=data["code"],
            name=data["name"],
            group=data["group"],
            main_uom=data["main_uom"],
        )
        db.add(product)
        db.flush()
        return json_response(
            {
                "id": str(product.id),
                "code": product.code,
                "name": product.name,
            },
            status_code=201,
        )


def update_price_policy(product_id: str, request: Request) -> Response:  # type: ignore[override]
    """
    PUT /api/catalog/products/{product_id}/price-policy
    
    Cập nhật hoặc tạo mới PricePolicy cho sản phẩm.
    
    Payload:
    {
      "customer_level": "C1",
      "price": 50000.0,
      "effective_date": "2025-01-15"
    }
    """
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        return json_response({"error": "product_id không hợp lệ"}, 400)
    
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return json_response({"error": "Body không phải JSON hợp lệ"}, 400)
    
    required_fields = ["customer_level", "price", "effective_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )
    
    try:
        customer_level = data["customer_level"]
        price = float(data["price"])
        effective_date = date.fromisoformat(data["effective_date"])
    except (ValueError, TypeError, KeyError) as e:
        return json_response({"error": f"Dữ liệu không hợp lệ: {str(e)}"}, 400)
    
    if price < 0:
        return json_response({"error": "price phải >= 0"}, 400)
    
    try:
        with get_session() as db:
            # Kiểm tra product tồn tại
            product = db.query(Product).filter(Product.id == product_uuid).first()
            if not product:
                return json_response({"error": "Sản phẩm không tồn tại"}, 404)
            
            # Tìm PricePolicy hiện tại với cùng product_id, customer_level, effective_date
            existing_policy = (
                db.query(PricePolicy)
                .filter(
                    and_(
                        PricePolicy.product_id == product_uuid,
                        PricePolicy.customer_level == customer_level,
                        PricePolicy.effective_date == effective_date,
                    )
                )
                .first()
            )
            
            if existing_policy:
                # Cập nhật giá
                existing_policy.price = price
                db.add(existing_policy)
                policy = existing_policy
            else:
                # Tạo mới
                policy = PricePolicy(
                    product_id=product_uuid,
                    customer_level=customer_level,
                    price=price,
                    effective_date=effective_date,
                )
                db.add(policy)
            
            db.commit()
            
            return json_response({
                "id": str(policy.id),
                "product_id": str(policy.product_id),
                "product_code": product.code,
                "product_name": product.name,
                "customer_level": policy.customer_level,
                "price": float(policy.price),
                "effective_date": policy.effective_date.isoformat(),
                "message": "Cập nhật chính sách giá thành công",
            })
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi cập nhật chính sách giá: {str(e)}"}, 500
        )


def bulk_update_price_policy(request: Request) -> Response:  # type: ignore[override]
    """
    POST /api/catalog/products/price-policy/bulk-update
    
    Cập nhật nhiều PricePolicy cùng lúc.
    
    Payload:
    {
      "updates": [
        {
          "product_id": "uuid",
          "customer_level": "C1",
          "price": 50000.0,
          "effective_date": "2025-01-15"
        },
        ...
      ]
    }
    """
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return json_response({"error": "Body không phải JSON hợp lệ"}, 400)
    
    if "updates" not in data:
        return json_response({"error": "Thiếu trường 'updates'"}, 400)
    
    if not isinstance(data["updates"], list) or not data["updates"]:
        return json_response({"error": "'updates' phải là mảng không rỗng"}, 400)
    
    # Validate tất cả updates trước khi commit
    validated_updates = []
    for idx, update in enumerate(data["updates"]):
        required_fields = ["product_id", "customer_level", "price", "effective_date"]
        missing = [f for f in required_fields if f not in update]
        if missing:
            return json_response(
                {"error": f"Update {idx}: Thiếu trường: {', '.join(missing)}"}, 400
            )
        
        try:
            product_uuid = uuid.UUID(update["product_id"])
            customer_level = update["customer_level"]
            price = float(update["price"])
            effective_date = date.fromisoformat(update["effective_date"])
        except (ValueError, TypeError, KeyError) as e:
            return json_response(
                {"error": f"Update {idx}: Dữ liệu không hợp lệ: {str(e)}"}, 400
            )
        
        if price < 0:
            return json_response(
                {"error": f"Update {idx}: price phải >= 0"}, 400
            )
        
        validated_updates.append({
            "product_id": product_uuid,
            "customer_level": customer_level,
            "price": price,
            "effective_date": effective_date,
        })
    
    try:
        with get_session() as db:
            updated_policies = []
            
            for update in validated_updates:
                # Kiểm tra product tồn tại
                product = (
                    db.query(Product)
                    .filter(Product.id == update["product_id"])
                    .first()
                )
                if not product:
                    continue
                
                # Tìm hoặc tạo PricePolicy
                existing_policy = (
                    db.query(PricePolicy)
                    .filter(
                        and_(
                            PricePolicy.product_id == update["product_id"],
                            PricePolicy.customer_level == update["customer_level"],
                            PricePolicy.effective_date == update["effective_date"],
                        )
                    )
                    .first()
                )
                
                if existing_policy:
                    existing_policy.price = update["price"]
                    db.add(existing_policy)
                    updated_policies.append({
                        "id": str(existing_policy.id),
                        "product_id": str(existing_policy.product_id),
                        "product_code": product.code,
                        "customer_level": existing_policy.customer_level,
                        "price": float(existing_policy.price),
                        "effective_date": existing_policy.effective_date.isoformat(),
                        "action": "updated",
                    })
                else:
                    new_policy = PricePolicy(
                        product_id=update["product_id"],
                        customer_level=update["customer_level"],
                        price=update["price"],
                        effective_date=update["effective_date"],
                    )
                    db.add(new_policy)
                    db.flush()
                    updated_policies.append({
                        "id": str(new_policy.id),
                        "product_id": str(new_policy.product_id),
                        "product_code": product.code,
                        "customer_level": new_policy.customer_level,
                        "price": float(new_policy.price),
                        "effective_date": new_policy.effective_date.isoformat(),
                        "action": "created",
                    })
            
            db.commit()
            
            return json_response({
                "updated_count": len(updated_policies),
                "policies": updated_policies,
                "message": f"Đã cập nhật {len(updated_policies)} chính sách giá",
            })
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi cập nhật chính sách giá: {str(e)}"}, 500
        )


# Các handler tương tự cho Warehouse, Customer, Supplier có thể được bổ sung sau.


