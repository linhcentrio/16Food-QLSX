"""
Services cho các báo cáo nâng cao.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, extract, case
from sqlalchemy.orm import Session

from ..models.entities import (
    ProductionOrder,
    ProductionOrderLine,
    SalesOrder,
    SalesOrderLine,
    InventorySnapshot,
    StockDocument,
    StockDocumentLine,
    Product,
)

logger = logging.getLogger(__name__)


def get_production_efficiency_report(
    db: Session,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """
    Báo cáo hiệu quả sản xuất.
    """
    # Tổng số lệnh sản xuất
    total_orders = (
        db.query(func.count(ProductionOrder.id))
        .filter(
            ProductionOrder.production_date >= start_date,
            ProductionOrder.production_date <= end_date,
        )
        .scalar()
    ) or 0

    # Tổng số lượng sản xuất
    total_produced = (
        db.query(func.sum(ProductionOrderLine.actual_qty))
        .join(ProductionOrder, ProductionOrderLine.production_order_id == ProductionOrder.id)
        .filter(
            ProductionOrder.production_date >= start_date,
            ProductionOrder.production_date <= end_date,
        )
        .scalar()
    ) or 0.0

    # Số lệnh hoàn thành
    completed_orders = (
        db.query(func.count(ProductionOrder.id))
        .filter(
            ProductionOrder.production_date >= start_date,
            ProductionOrder.production_date <= end_date,
            ProductionOrder.status == "completed",
        )
        .scalar()
    ) or 0

    # Tỷ lệ hoàn thành
    completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0.0

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "completion_rate": round(completion_rate, 2),
        "total_produced_quantity": float(total_produced),
    }


def get_profit_report(
    db: Session,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """
    Báo cáo lợi nhuận.
    Tính đơn giản: Doanh thu - Giá vốn (từ BOM)
    """
    # Tổng doanh thu từ đơn hàng đã giao
    total_revenue = (
        db.query(func.sum(SalesOrder.total_amount))
        .filter(
            SalesOrder.order_date >= start_date,
            SalesOrder.order_date <= end_date,
            SalesOrder.status.in_(["delivered", "completed"]),
        )
        .scalar()
    ) or 0.0

    # Tổng giá vốn (ước tính từ giá trị xuất kho)
    # Đơn giản: lấy tổng giá trị xuất kho sản phẩm
    total_cost = (
        db.query(func.sum(InventorySnapshot.inventory_value))
        .join(StockDocumentLine, InventorySnapshot.product_id == StockDocumentLine.product_id)
        .join(StockDocument, StockDocumentLine.document_id == StockDocument.id)
        .filter(
            StockDocument.posting_date >= start_date,
            StockDocument.posting_date <= end_date,
            StockDocument.doc_type == "X",
        )
        .scalar()
    ) or 0.0

    gross_profit = total_revenue - total_cost
    profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "total_revenue": float(total_revenue),
        "total_cost": float(total_cost),
        "gross_profit": float(gross_profit),
        "profit_margin": round(profit_margin, 2),
    }


def get_inventory_time_series(
    db: Session,
    product_id: str | None = None,
    warehouse_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """
    Báo cáo tồn kho theo thời gian.
    Lấy từ bảng inventory_snapshot và stock_document.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=90)

    query = (
        db.query(
            StockDocument.posting_date,
            Product.code,
            Product.name,
            func.sum(StockDocumentLine.quantity).label("total_in"),
            func.sum(
                case((StockDocument.doc_type == "X", StockDocumentLine.quantity), else_=0)
            ).label("total_out"),
        )
        .join(StockDocumentLine, StockDocument.id == StockDocumentLine.document_id)
        .join(Product, StockDocumentLine.product_id == Product.id)
        .filter(
            StockDocument.posting_date >= start_date,
            StockDocument.posting_date <= end_date,
        )
    )

    if product_id:
        try:
            from uuid import UUID
            prod_id = UUID(product_id)
            query = query.filter(Product.id == prod_id)
        except ValueError:
            return []

    if warehouse_id:
        try:
            from uuid import UUID
            wh_id = UUID(warehouse_id)
            query = query.filter(StockDocument.warehouse_id == wh_id)
        except ValueError:
            return []

    results = query.group_by(StockDocument.posting_date, Product.code, Product.name).order_by(StockDocument.posting_date).all()

    return [
        {
            "date": r.posting_date.isoformat(),
            "product_code": r.code,
            "product_name": r.name,
            "total_in": float(r.total_in or 0),
            "total_out": float(r.total_out or 0),
        }
        for r in results
    ]


def get_executive_dashboard_summary(
    db: Session,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """
    Dashboard tổng quan cho lãnh đạo.
    """
    if not as_of_date:
        as_of_date = date.today()

    start_of_month = date(as_of_date.year, as_of_date.month, 1)
    start_of_year = date(as_of_date.year, 1, 1)

    # Doanh thu tháng
    monthly_revenue = (
        db.query(func.sum(SalesOrder.total_amount))
        .filter(
            SalesOrder.order_date >= start_of_month,
            SalesOrder.order_date <= as_of_date,
            SalesOrder.status.in_(["delivered", "completed"]),
        )
        .scalar()
    ) or 0.0

    # Doanh thu năm
    yearly_revenue = (
        db.query(func.sum(SalesOrder.total_amount))
        .filter(
            SalesOrder.order_date >= start_of_year,
            SalesOrder.order_date <= as_of_date,
            SalesOrder.status.in_(["delivered", "completed"]),
        )
        .scalar()
    ) or 0.0

    # Tổng số đơn hàng tháng
    monthly_orders = (
        db.query(func.count(SalesOrder.id))
        .filter(
            SalesOrder.order_date >= start_of_month,
            SalesOrder.order_date <= as_of_date,
        )
        .scalar()
    ) or 0

    # Tổng giá trị tồn kho
    total_inventory_value = (
        db.query(func.sum(InventorySnapshot.inventory_value))
        .scalar()
    ) or 0.0

    # Số lệnh sản xuất đang thực hiện
    active_production_orders = (
        db.query(func.count(ProductionOrder.id))
        .filter(ProductionOrder.status == "in_progress")
        .scalar()
    ) or 0

    return {
        "as_of_date": as_of_date.isoformat(),
        "monthly_revenue": float(monthly_revenue),
        "yearly_revenue": float(yearly_revenue),
        "monthly_orders": monthly_orders,
        "total_inventory_value": float(total_inventory_value),
        "active_production_orders": active_production_orders,
    }

