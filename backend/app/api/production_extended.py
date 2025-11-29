"""
API cho Module Sản Xuất mở rộng: Production Logbook và Production Stages.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime

from robyn import Request, Response

from ..core.db import get_session
from ..core.error_handler import json_response as _json_response, ValidationError, NotFoundError
from ..models.production_extended import (
    ProductionStage,
    StageOperation,
    ProductionLog,
    ProductionLogEntry,
)
from ..models.entities import ProductionOrder


def _parse_date(value: str) -> date:
    """Parse date từ string."""
    return date.fromisoformat(value)


def _parse_datetime(value: str) -> datetime:
    """Parse datetime từ string."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# Production Stage APIs
def list_production_stages() -> Response:
    """GET /api/production/stages - Danh sách công đoạn sản xuất."""
    with get_session() as db:
        stages = (
            db.query(ProductionStage)
            .filter(ProductionStage.is_active == True)
            .order_by(ProductionStage.sequence)
            .all()
        )

        data = []
        for stage in stages:
            operations = (
                db.query(StageOperation)
                .filter(StageOperation.stage_id == stage.id)
                .order_by(StageOperation.sequence)
                .all()
            )

            data.append({
                "id": str(stage.id),
                "code": stage.code,
                "name": stage.name,
                "sequence": stage.sequence,
                "description": stage.description,
                "standard_duration_minutes": stage.standard_duration_minutes,
                "operations": [
                    {
                        "id": str(op.id),
                        "name": op.name,
                        "sequence": op.sequence,
                        "description": op.description,
                        "standard_duration_minutes": op.standard_duration_minutes,
                    }
                    for op in operations
                ],
            })

        return _json_response(data)


def create_production_stage(request: Request) -> Response:
    """POST /api/production/stages - Tạo công đoạn sản xuất mới."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["code", "name", "sequence"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        existing = (
            db.query(ProductionStage).filter(ProductionStage.code == data["code"]).first()
        )
        if existing:
            return _json_response({"error": "Mã công đoạn đã tồn tại"}, 400)

        stage = ProductionStage(
            code=data["code"],
            name=data["name"],
            sequence=int(data["sequence"]),
            description=data.get("description"),
            standard_duration_minutes=int(data["standard_duration_minutes"])
            if data.get("standard_duration_minutes")
            else None,
            is_active=data.get("is_active", True),
        )
        db.add(stage)
        db.flush()

        # Tạo các thao tác
        operations_data = data.get("operations", [])
        for op_data in operations_data:
            operation = StageOperation(
                stage_id=stage.id,
                name=op_data.get("name", ""),
                sequence=int(op_data.get("sequence", 0)),
                description=op_data.get("description"),
                standard_duration_minutes=int(op_data["standard_duration_minutes"])
                if op_data.get("standard_duration_minutes")
                else None,
            )
            db.add(operation)

        return _json_response({
            "id": str(stage.id),
            "code": stage.code,
            "name": stage.name,
        }, 201)


# Production Log APIs
def list_production_logs(request: Request) -> Response:
    """GET /api/production/logs - Danh sách nhật ký sản xuất."""
    production_order_id = request.query_params.get("production_order_id")
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
        query = db.query(ProductionLog, ProductionOrder).join(ProductionOrder)

        if production_order_id:
            try:
                po_id = uuid.UUID(production_order_id)
                query = query.filter(ProductionLog.production_order_id == po_id)
            except ValueError:
                return _json_response({"error": "Invalid production_order_id"}, 400)

        if start_date:
            query = query.filter(ProductionLog.log_date >= start_date)
        if end_date:
            query = query.filter(ProductionLog.log_date <= end_date)

        rows = query.order_by(ProductionLog.log_date.desc(), ProductionLog.created_at.desc()).limit(100).all()

        data = [
            {
                "id": str(log.id),
                "code": log.code,
                "production_order_code": po.business_id,
                "log_date": log.log_date.isoformat(),
                "shift": log.shift,
                "operator": log.operator,
                "actual_quantity": float(log.actual_quantity) if log.actual_quantity else None,
                "start_time": log.start_time.isoformat() if log.start_time else None,
                "end_time": log.end_time.isoformat() if log.end_time else None,
            }
            for log, po in rows
        ]

        return _json_response(data)


def create_production_log(request: Request) -> Response:
    """POST /api/production/logs - Tạo nhật ký sản xuất."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["production_order_id", "log_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        try:
            po_id = uuid.UUID(data["production_order_id"])
            production_order = (
                db.query(ProductionOrder).filter(ProductionOrder.id == po_id).first()
            )
            if not production_order:
                return _json_response({"error": "Lệnh sản xuất không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid production_order_id"}, 400)

        log_date = _parse_date(data["log_date"])

        count_today = (
            db.query(ProductionLog)
            .filter(
                ProductionLog.production_order_id == po_id,
                ProductionLog.log_date == log_date,
            )
            .count()
        )
        code = f"NK{log_date.strftime('%Y%m%d')}-{count_today + 1:03d}"

        start_time = None
        if data.get("start_time"):
            try:
                start_time = _parse_datetime(data["start_time"])
            except ValueError:
                return _json_response({"error": "Invalid start_time format"}, 400)

        end_time = None
        if data.get("end_time"):
            try:
                end_time = _parse_datetime(data["end_time"])
            except ValueError:
                return _json_response({"error": "Invalid end_time format"}, 400)

        production_log = ProductionLog(
            code=code,
            production_order_id=po_id,
            log_date=log_date,
            shift=data.get("shift"),
            operator=data.get("operator"),
            start_time=start_time,
            end_time=end_time,
            actual_quantity=float(data["actual_quantity"])
            if data.get("actual_quantity")
            else None,
            quality_notes=data.get("quality_notes"),
            issues=data.get("issues"),
            note=data.get("note"),
        )
        db.add(production_log)
        db.flush()

        # Tạo các entry theo công đoạn
        entries_data = data.get("entries", [])
        for entry_data in entries_data:
            try:
                stage_id = uuid.UUID(entry_data.get("stage_id", ""))
            except (ValueError, TypeError):
                continue

            entry_start_time = None
            if entry_data.get("start_time"):
                try:
                    entry_start_time = _parse_datetime(entry_data["start_time"])
                except ValueError:
                    pass

            entry_end_time = None
            if entry_data.get("end_time"):
                try:
                    entry_end_time = _parse_datetime(entry_data["end_time"])
                except ValueError:
                    pass

            duration_minutes = None
            if entry_start_time and entry_end_time:
                duration_minutes = int((entry_end_time - entry_start_time).total_seconds() / 60)

            entry = ProductionLogEntry(
                log_id=production_log.id,
                stage_id=stage_id,
                start_time=entry_start_time,
                end_time=entry_end_time,
                duration_minutes=duration_minutes,
                operator=entry_data.get("operator"),
                quantity_processed=float(entry_data["quantity_processed"])
                if entry_data.get("quantity_processed")
                else None,
                quality_status=entry_data.get("quality_status"),
                issues=entry_data.get("issues"),
                note=entry_data.get("note"),
            )
            db.add(entry)

        return _json_response({
            "id": str(production_log.id),
            "code": production_log.code,
        }, 201)


def get_production_log_detail(log_id: str, request: Request) -> Response:
    """GET /api/production/logs/:id - Chi tiết nhật ký sản xuất."""
    try:
        log_uuid = uuid.UUID(log_id)
    except ValueError:
        return _json_response({"error": "Invalid log_id"}, 400)

    with get_session() as db:
        log = (
            db.query(ProductionLog, ProductionOrder)
            .join(ProductionOrder)
            .filter(ProductionLog.id == log_uuid)
            .first()
        )
        if not log:
            return _json_response({"error": "Nhật ký sản xuất không tồn tại"}, 404)

        production_log, production_order = log

        entries = (
            db.query(ProductionLogEntry, ProductionStage)
            .join(ProductionStage)
            .filter(ProductionLogEntry.log_id == log_uuid)
            .order_by(ProductionStage.sequence)
            .all()
        )

        return _json_response({
            "id": str(production_log.id),
            "code": production_log.code,
            "production_order_code": production_order.business_id,
            "log_date": production_log.log_date.isoformat(),
            "shift": production_log.shift,
            "operator": production_log.operator,
            "start_time": production_log.start_time.isoformat() if production_log.start_time else None,
            "end_time": production_log.end_time.isoformat() if production_log.end_time else None,
            "actual_quantity": float(production_log.actual_quantity) if production_log.actual_quantity else None,
            "quality_notes": production_log.quality_notes,
            "issues": production_log.issues,
            "entries": [
                {
                    "id": str(entry.id),
                    "stage_code": stage.code,
                    "stage_name": stage.name,
                    "start_time": entry.start_time.isoformat() if entry.start_time else None,
                    "end_time": entry.end_time.isoformat() if entry.end_time else None,
                    "duration_minutes": entry.duration_minutes,
                    "operator": entry.operator,
                    "quantity_processed": float(entry.quantity_processed) if entry.quantity_processed else None,
                    "quality_status": entry.quality_status,
                    "issues": entry.issues,
                }
                for entry, stage in entries
            ],
        })

