"""
API cho các báo cáo nâng cao.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from robyn import Request, Response

from ..core.db import get_session
from ..core.error_handler import json_response as _json_response
from ..services.reporting import (
    get_production_efficiency_report,
    get_profit_report,
    get_inventory_time_series,
    get_executive_dashboard_summary,
)


def _parse_date(value: str) -> date:
    """Parse date từ string."""
    return date.fromisoformat(value)


def get_production_efficiency(request: Request) -> Response:
    """GET /api/reports/production-efficiency - Báo cáo hiệu quả sản xuất."""
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    if not start_date_str or not end_date_str:
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
    else:
        try:
            start_date = _parse_date(start_date_str)
            end_date = _parse_date(end_date_str)
        except ValueError:
            return _json_response({"error": "Invalid date format"}, 400)

    with get_session() as db:
        report = get_production_efficiency_report(db, start_date, end_date)
        return _json_response(report)


def get_profit_analysis(request: Request) -> Response:
    """GET /api/reports/profit - Báo cáo lợi nhuận."""
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")

    if not start_date_str or not end_date_str:
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
    else:
        try:
            start_date = _parse_date(start_date_str)
            end_date = _parse_date(end_date_str)
        except ValueError:
            return _json_response({"error": "Invalid date format"}, 400)

    with get_session() as db:
        report = get_profit_report(db, start_date, end_date)
        return _json_response(report)


def get_inventory_time_series_report(request: Request) -> Response:
    """GET /api/reports/inventory-time-series - Báo cáo tồn kho theo thời gian."""
    product_id = request.query_params.get("product_id")
    warehouse_id = request.query_params.get("warehouse_id")
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
        data = get_inventory_time_series(db, product_id, warehouse_id, start_date, end_date)
        return _json_response(data)


def get_executive_dashboard(request: Request) -> Response:
    """GET /api/reports/executive-dashboard - Dashboard tổng quan."""
    as_of_date_str = request.query_params.get("as_of_date")

    as_of_date = None
    if as_of_date_str:
        try:
            as_of_date = _parse_date(as_of_date_str)
        except ValueError:
            return _json_response({"error": "Invalid as_of_date format"}, 400)

    with get_session() as db:
        summary = get_executive_dashboard_summary(db, as_of_date)
        return _json_response(summary)


def get_kpi_dashboard(request: Request) -> Response:
    """GET /api/reports/kpi-dashboard - Real-time KPI dashboard."""
    from ..models.crm_extended import KpiMetric, KpiRecord
    from datetime import date

    with get_session() as db:
        # Lấy các KPI metrics active
        metrics = db.query(KpiMetric).filter(KpiMetric.is_active == True).all()

        kpi_data = []
        for metric in metrics:
            # Lấy giá trị mới nhất
            latest_record = (
                db.query(KpiRecord)
                .filter(KpiRecord.kpi_metric_id == metric.id)
                .order_by(KpiRecord.record_date.desc())
                .first()
            )

            kpi_data.append({
                "kpi_code": metric.code,
                "kpi_name": metric.name,
                "category": metric.category,
                "unit": metric.unit,
                "current_value": float(latest_record.value) if latest_record else None,
                "target_value": float(metric.target_value) if metric.target_value else None,
                "variance": float(latest_record.variance) if latest_record and latest_record.variance else None,
                "variance_percentage": float(latest_record.variance_percentage) if latest_record and latest_record.variance_percentage else None,
                "last_updated": latest_record.record_date.isoformat() if latest_record else None,
            })

        return _json_response({
            "as_of_date": date.today().isoformat(),
            "kpis": kpi_data,
        })

