"""
API cho phân tích kho: ABC Analysis và Turnover Analysis.
"""

from __future__ import annotations

import json
from datetime import date

from robyn import Request, Response

from ..core.db import get_session
from ..core.error_handler import json_response as _json_response, ValidationError
from ..services.inventory_analysis import (
    calculate_abc_analysis,
    calculate_turnover_analysis,
)


def _parse_date(value: str) -> date:
    """Parse date từ string."""
    return date.fromisoformat(value)


def get_abc_analysis(request: Request) -> Response:
    """
    GET /api/inventory/analysis/abc
    
    Tính ABC Analysis cho tồn kho.
    
    Query params:
    - warehouse_id: Lọc theo kho (optional)
    - as_of_date: Ngày tính toán (optional, format: YYYY-MM-DD)
    """
    warehouse_id = request.query_params.get("warehouse_id")
    as_of_date_str = request.query_params.get("as_of_date")
    
    as_of_date = None
    if as_of_date_str:
        try:
            as_of_date = _parse_date(as_of_date_str)
        except ValueError:
            return _json_response(
                {"error": "Invalid date format. Use YYYY-MM-DD"}, 400
            )
    
    with get_session() as db:
        results = calculate_abc_analysis(
            db,
            warehouse_id=warehouse_id,
            as_of_date=as_of_date,
        )
        
        return _json_response({
            "analysis_type": "ABC",
            "warehouse_id": warehouse_id,
            "as_of_date": as_of_date.isoformat() if as_of_date else None,
            "results": results,
            "summary": {
                "total_products": len(results),
                "category_a_count": len([r for r in results if r["category"] == "A"]),
                "category_b_count": len([r for r in results if r["category"] == "B"]),
                "category_c_count": len([r for r in results if r["category"] == "C"]),
            },
        })


def get_turnover_analysis(request: Request) -> Response:
    """
    GET /api/inventory/analysis/turnover
    
    Tính vòng quay hàng tồn kho.
    
    Query params:
    - warehouse_id: Lọc theo kho (optional)
    - start_date: Ngày bắt đầu (optional, format: YYYY-MM-DD)
    - end_date: Ngày kết thúc (optional, format: YYYY-MM-DD)
    """
    warehouse_id = request.query_params.get("warehouse_id")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")
    
    start_date = None
    if start_date_str:
        try:
            start_date = _parse_date(start_date_str)
        except ValueError:
            return _json_response(
                {"error": "Invalid start_date format. Use YYYY-MM-DD"}, 400
            )
    
    end_date = None
    if end_date_str:
        try:
            end_date = _parse_date(end_date_str)
        except ValueError:
            return _json_response(
                {"error": "Invalid end_date format. Use YYYY-MM-DD"}, 400
            )
    
    with get_session() as db:
        results = calculate_turnover_analysis(
            db,
            warehouse_id=warehouse_id,
            start_date=start_date,
            end_date=end_date,
        )
        
        return _json_response({
            "analysis_type": "Turnover",
            "warehouse_id": warehouse_id,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "results": results,
            "summary": {
                "total_products": len(results),
                "high_turnover_count": len([r for r in results if r["turnover_ratio"] > 12]),
                "medium_turnover_count": len([r for r in results if 4 <= r["turnover_ratio"] <= 12]),
                "low_turnover_count": len([r for r in results if r["turnover_ratio"] < 4]),
            },
        })

