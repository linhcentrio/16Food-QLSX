"""
Service phân tích kho: ABC Analysis và Turnover Analysis.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.entities import (
    InventorySnapshot,
    Product,
    StockDocument,
    StockDocumentLine,
    Warehouse,
)

logger = logging.getLogger(__name__)


def calculate_abc_analysis(
    db: Session,
    warehouse_id: str | None = None,
    as_of_date: date | None = None,
) -> list[dict[str, Any]]:
    """
    Tính ABC Analysis cho tồn kho.
    
    Phân loại sản phẩm theo giá trị tồn kho:
    - A: 80% giá trị (top 20% sản phẩm)
    - B: 15% giá trị (tiếp theo 30% sản phẩm)
    - C: 5% giá trị (còn lại 50% sản phẩm)
    """
    query = (
        db.query(
            InventorySnapshot.product_id,
            Product.code,
            Product.name,
            func.sum(InventorySnapshot.current_qty).label("total_qty"),
            func.sum(InventorySnapshot.inventory_value).label("total_value"),
        )
        .join(Product, InventorySnapshot.product_id == Product.id)
    )

    if warehouse_id:
        query = query.filter(InventorySnapshot.warehouse_id == warehouse_id)

    if as_of_date:
        # Có thể filter theo ngày nếu có snapshot theo thời gian
        pass

    results = query.group_by(
        InventorySnapshot.product_id, Product.code, Product.name
    ).order_by(func.sum(InventorySnapshot.inventory_value).desc()).all()

    if not results:
        return []

    # Tính tổng giá trị
    total_value = sum(float(r.total_value or 0) for r in results)

    if total_value == 0:
        return []

    # Phân loại ABC
    abc_results = []
    cumulative_value = 0.0

    for result in results:
        product_value = float(result.total_value or 0)
        if product_value <= 0:
            continue
            
        cumulative_value += product_value
        percentage = (cumulative_value / total_value) * 100

        if percentage <= 80:
            category = "A"
        elif percentage <= 95:
            category = "B"
        else:
            category = "C"

        abc_results.append({
            "product_id": str(result.product_id),
            "product_code": result.code,
            "product_name": result.name,
            "quantity": float(result.total_qty or 0),
            "value": product_value,
            "percentage_of_total": (product_value / total_value) * 100,
            "cumulative_percentage": percentage,
            "category": category,
        })

    return abc_results


def calculate_turnover_analysis(
    db: Session,
    warehouse_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """
    Tính vòng quay hàng tồn kho (Inventory Turnover).
    
    Công thức: Cost of Goods Sold / Average Inventory
    Hoặc đơn giản: Total Out / Average Inventory
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=365)

    # Lấy tồn kho trung bình
    avg_inv_query = (
        db.query(
            InventorySnapshot.product_id,
            Product.code,
            Product.name,
            func.avg(InventorySnapshot.current_qty).label("avg_qty"),
            func.avg(InventorySnapshot.inventory_value).label("avg_value"),
        )
        .join(Product, InventorySnapshot.product_id == Product.id)
    )

    if warehouse_id:
        avg_inv_query = avg_inv_query.filter(InventorySnapshot.warehouse_id == warehouse_id)

    avg_inventory = avg_inv_query.group_by(
        InventorySnapshot.product_id, Product.code, Product.name
    ).all()

    # Lấy tổng xuất trong kỳ
    out_query = (
        db.query(
            StockDocumentLine.product_id,
            Product.code,
            Product.name,
            func.sum(func.abs(StockDocumentLine.signed_qty)).label("total_out"),
        )
        .join(Product, StockDocumentLine.product_id == Product.id)
        .join(StockDocument, StockDocumentLine.document_id == StockDocument.id)
        .filter(
            StockDocument.doc_type == "X",
            StockDocument.posting_date >= start_date,
            StockDocument.posting_date <= end_date,
        )
    )

    if warehouse_id:
        out_query = out_query.filter(StockDocument.warehouse_id == warehouse_id)

    total_out = out_query.group_by(
        StockDocumentLine.product_id, Product.code, Product.name
    ).all()

    # Tạo dict để lookup
    out_dict = {
        str(r.product_id): float(r.total_out or 0) for r in total_out
    }

    # Tính turnover
    turnover_results = []
    for avg in avg_inventory:
        product_id = str(avg.product_id)
        avg_qty = float(avg.avg_qty or 0)
        avg_value = float(avg.avg_value or 0)
        total_out_qty = out_dict.get(product_id, 0.0)

        if avg_qty > 0:
            turnover_ratio = total_out_qty / avg_qty
            days_supply = (avg_qty / total_out_qty * 365) if total_out_qty > 0 else 999
        else:
            turnover_ratio = 0.0
            days_supply = 999

        turnover_results.append({
            "product_id": product_id,
            "product_code": avg.code,
            "product_name": avg.name,
            "average_quantity": avg_qty,
            "average_value": avg_value,
            "total_out_quantity": total_out_qty,
            "turnover_ratio": turnover_ratio,
            "days_supply": days_supply,
        })

    # Sắp xếp theo turnover ratio
    turnover_results.sort(key=lambda x: x["turnover_ratio"], reverse=True)

    return turnover_results

