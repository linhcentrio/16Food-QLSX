"""
Services cho phân tích CRM: hành vi mua hàng, segmentation, etc.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, extract, case
from sqlalchemy.orm import Session

from ..models.entities import Customer, SalesOrder, SalesOrderLine, Product

logger = logging.getLogger(__name__)


def analyze_customer_purchase_behavior(
    db: Session,
    customer_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """
    Phân tích hành vi mua hàng của khách hàng.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=365)

    query = (
        db.query(
            Customer.id,
            Customer.code,
            Customer.name,
            Customer.level,
            func.count(SalesOrder.id).label("total_orders"),
            func.sum(SalesOrder.total_amount).label("total_revenue"),
            func.avg(SalesOrder.total_amount).label("avg_order_value"),
            func.max(SalesOrder.order_date).label("last_order_date"),
            func.min(SalesOrder.order_date).label("first_order_date"),
            func.count(func.distinct(extract("year", SalesOrder.order_date))).label("years_active"),
        )
        .join(SalesOrder, Customer.id == SalesOrder.customer_id)
        .filter(
            SalesOrder.order_date >= start_date,
            SalesOrder.order_date <= end_date,
        )
    )

    if customer_id:
        try:
            from uuid import UUID
            customer_uuid = UUID(customer_id)
            query = query.filter(Customer.id == customer_uuid)
        except ValueError:
            return []

    results = query.group_by(Customer.id, Customer.code, Customer.name, Customer.level).all()

    data = []
    for r in results:
        days_active = (r.last_order_date - r.first_order_date).days if r.last_order_date and r.first_order_date else 0
        order_frequency = days_active / float(r.total_orders) if r.total_orders > 0 else 0

        data.append({
            "customer_id": str(r.id),
            "customer_code": r.code,
            "customer_name": r.name,
            "customer_level": r.level,
            "total_orders": r.total_orders,
            "total_revenue": float(r.total_revenue or 0),
            "avg_order_value": float(r.avg_order_value or 0),
            "first_order_date": r.first_order_date.isoformat() if r.first_order_date else None,
            "last_order_date": r.last_order_date.isoformat() if r.last_order_date else None,
            "days_active": days_active,
            "years_active": r.years_active,
            "order_frequency_days": round(order_frequency, 2),
        })

    return data


def get_customer_segmentation(
    db: Session,
    segment_criteria: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Phân khúc khách hàng dựa trên các tiêu chí.
    """
    # Phân khúc đơn giản dựa trên doanh thu và số đơn hàng
    query = (
        db.query(
            Customer.id,
            Customer.code,
            Customer.name,
            Customer.level,
            func.count(SalesOrder.id).label("total_orders"),
            func.sum(SalesOrder.total_amount).label("total_revenue"),
        )
        .outerjoin(SalesOrder, Customer.id == SalesOrder.customer_id)
        .group_by(Customer.id, Customer.code, Customer.name, Customer.level)
    )

    results = query.all()

    segments = []
    for r in results:
        total_revenue = float(r.total_revenue or 0)
        total_orders = r.total_orders or 0

        # Phân loại đơn giản
        if total_revenue >= 1000000 and total_orders >= 10:
            segment = "VIP"
        elif total_revenue >= 500000 and total_orders >= 5:
            segment = "High Value"
        elif total_revenue >= 100000:
            segment = "Medium Value"
        elif total_revenue > 0:
            segment = "Low Value"
        else:
            segment = "Inactive"

        segments.append({
            "customer_id": str(r.id),
            "customer_code": r.code,
            "customer_name": r.name,
            "customer_level": r.level,
            "segment": segment,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
        })

    return segments


def get_customer_product_preferences(
    db: Session,
    customer_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """
    Phân tích sản phẩm ưa thích của khách hàng.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=365)

    try:
        from uuid import UUID
        customer_uuid = UUID(customer_id)
    except ValueError:
        return []

    results = (
        db.query(
            Product.code,
            Product.name,
            func.sum(SalesOrderLine.quantity).label("total_quantity"),
            func.sum(SalesOrderLine.line_amount).label("total_amount"),
            func.count(func.distinct(SalesOrder.id)).label("order_count"),
        )
        .join(SalesOrderLine, Product.id == SalesOrderLine.product_id)
        .join(SalesOrder, SalesOrderLine.order_id == SalesOrder.id)
        .filter(
            SalesOrder.customer_id == customer_uuid,
            SalesOrder.order_date >= start_date,
            SalesOrder.order_date <= end_date,
        )
        .group_by(Product.code, Product.name)
        .order_by(func.sum(SalesOrderLine.line_amount).desc())
        .limit(20)
        .all()
    )

    return [
        {
            "product_code": r.code,
            "product_name": r.name,
            "total_quantity": float(r.total_quantity or 0),
            "total_amount": float(r.total_amount or 0),
            "order_count": r.order_count,
        }
        for r in results
    ]

