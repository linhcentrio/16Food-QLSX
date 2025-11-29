"""
API cho Module Thiết Bị, CCDC (Equipment & Tools).
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime

from robyn import Request, Response

from ..core.db import get_session
from ..core.error_handler import json_response as _json_response, ValidationError, NotFoundError
from ..models.equipment import (
    EquipmentType,
    Equipment,
    FuelConsumptionNorm,
    EquipmentRepair,
    EquipmentRepairLine,
    MaintenanceSchedule,
    MaintenanceRecord,
)


def _parse_date(value: str) -> date:
    """Parse date từ string."""
    return date.fromisoformat(value)


# Equipment Type APIs
def list_equipment_types() -> Response:
    """GET /api/equipment/types - Danh sách loại thiết bị."""
    with get_session() as db:
        types = db.query(EquipmentType).order_by(EquipmentType.code).all()
        data = [
            {
                "id": str(t.id),
                "code": t.code,
                "name": t.name,
                "description": t.description,
            }
            for t in types
        ]
        return _json_response(data)


def create_equipment_type(request: Request) -> Response:
    """POST /api/equipment/types - Tạo loại thiết bị mới."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["code", "name"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        existing = db.query(EquipmentType).filter(EquipmentType.code == data["code"]).first()
        if existing:
            return _json_response({"error": "Mã loại thiết bị đã tồn tại"}, 400)

        eq_type = EquipmentType(
            code=data["code"],
            name=data["name"],
            description=data.get("description"),
        )
        db.add(eq_type)
        db.flush()

        return _json_response({
            "id": str(eq_type.id),
            "code": eq_type.code,
            "name": eq_type.name,
        }, 201)


# Equipment APIs
def list_equipment(request: Request) -> Response:
    """GET /api/equipment - Danh sách thiết bị."""
    equipment_type_id = request.query_params.get("equipment_type_id")
    status = request.query_params.get("status")

    with get_session() as db:
        query = db.query(Equipment, EquipmentType).join(EquipmentType)

        if equipment_type_id:
            try:
                eq_type_uuid = uuid.UUID(equipment_type_id)
                query = query.filter(Equipment.equipment_type_id == eq_type_uuid)
            except ValueError:
                return _json_response({"error": "Invalid equipment_type_id"}, 400)

        if status:
            query = query.filter(Equipment.status == status)

        rows = query.order_by(Equipment.code).limit(100).all()

        data = [
            {
                "id": str(eq.id),
                "code": eq.code,
                "name": eq.name,
                "equipment_type": {
                    "id": str(eq_type.id),
                    "code": eq_type.code,
                    "name": eq_type.name,
                },
                "manufacturer": eq.manufacturer,
                "model": eq.model,
                "serial_number": eq.serial_number,
                "location": eq.location,
                "status": eq.status,
            }
            for eq, eq_type in rows
        ]

        return _json_response(data)


def create_equipment(request: Request) -> Response:
    """POST /api/equipment - Tạo thiết bị mới."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["code", "name", "equipment_type_id"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        existing = db.query(Equipment).filter(Equipment.code == data["code"]).first()
        if existing:
            return _json_response({"error": "Mã thiết bị đã tồn tại"}, 400)

        try:
            eq_type_id = uuid.UUID(data["equipment_type_id"])
            eq_type = db.query(EquipmentType).filter(EquipmentType.id == eq_type_id).first()
            if not eq_type:
                return _json_response({"error": "Loại thiết bị không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid equipment_type_id"}, 400)

        purchase_date = None
        if data.get("purchase_date"):
            try:
                purchase_date = _parse_date(data["purchase_date"])
            except ValueError:
                return _json_response({"error": "Invalid purchase_date format"}, 400)

        warranty_expiry = None
        if data.get("warranty_expiry"):
            try:
                warranty_expiry = _parse_date(data["warranty_expiry"])
            except ValueError:
                return _json_response({"error": "Invalid warranty_expiry format"}, 400)

        equipment = Equipment(
            code=data["code"],
            name=data["name"],
            equipment_type_id=eq_type_id,
            manufacturer=data.get("manufacturer"),
            model=data.get("model"),
            serial_number=data.get("serial_number"),
            purchase_date=purchase_date,
            warranty_expiry=warranty_expiry,
            location=data.get("location"),
            status=data.get("status", "active"),
            note=data.get("note"),
        )
        db.add(equipment)
        db.flush()

        return _json_response({
            "id": str(equipment.id),
            "code": equipment.code,
            "name": equipment.name,
        }, 201)


# Fuel Consumption Norm APIs
def list_fuel_norms(request: Request) -> Response:
    """GET /api/equipment/:id/fuel-norms - Danh sách định mức nhiên liệu của thiết bị."""
    equipment_id = request.path_params.get("id", "")
    try:
        eq_id = uuid.UUID(equipment_id)
    except ValueError:
        return _json_response({"error": "Invalid equipment_id"}, 400)

    with get_session() as db:
        equipment = db.query(Equipment).filter(Equipment.id == eq_id).first()
        if not equipment:
            return _json_response({"error": "Thiết bị không tồn tại"}, 404)

        norms = (
            db.query(FuelConsumptionNorm)
            .filter(FuelConsumptionNorm.equipment_id == eq_id)
            .order_by(FuelConsumptionNorm.effective_date.desc())
            .all()
        )

        data = [
            {
                "id": str(n.id),
                "fuel_type": n.fuel_type,
                "consumption_rate": float(n.consumption_rate),
                "unit": n.unit,
                "effective_date": n.effective_date.isoformat(),
                "note": n.note,
            }
            for n in norms
        ]

        return _json_response(data)


def create_fuel_norm(equipment_id: str, request: Request) -> Response:
    """POST /api/equipment/:id/fuel-norms - Tạo định mức nhiên liệu."""
    try:
        eq_id = uuid.UUID(equipment_id)
    except ValueError:
        return _json_response({"error": "Invalid equipment_id"}, 400)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["fuel_type", "consumption_rate", "unit", "effective_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        equipment = db.query(Equipment).filter(Equipment.id == eq_id).first()
        if not equipment:
            return _json_response({"error": "Thiết bị không tồn tại"}, 404)

        try:
            effective_date = _parse_date(data["effective_date"])
        except ValueError:
            return _json_response({"error": "Invalid effective_date format"}, 400)

        norm = FuelConsumptionNorm(
            equipment_id=eq_id,
            fuel_type=data["fuel_type"],
            consumption_rate=float(data["consumption_rate"]),
            unit=data["unit"],
            effective_date=effective_date,
            note=data.get("note"),
        )
        db.add(norm)
        db.flush()

        return _json_response({
            "id": str(norm.id),
            "fuel_type": norm.fuel_type,
            "consumption_rate": float(norm.consumption_rate),
        }, 201)


# Equipment Repair APIs
def list_equipment_repairs(request: Request) -> Response:
    """GET /api/equipment/repairs - Danh sách phiếu sửa chữa."""
    equipment_id = request.query_params.get("equipment_id")
    status = request.query_params.get("status")

    with get_session() as db:
        query = db.query(EquipmentRepair, Equipment).join(Equipment)

        if equipment_id:
            try:
                eq_id = uuid.UUID(equipment_id)
                query = query.filter(EquipmentRepair.equipment_id == eq_id)
            except ValueError:
                return _json_response({"error": "Invalid equipment_id"}, 400)

        if status:
            query = query.filter(EquipmentRepair.status == status)

        rows = query.order_by(EquipmentRepair.request_date.desc()).limit(100).all()

        data = [
            {
                "id": str(repair.id),
                "code": repair.code,
                "equipment_code": eq.code,
                "equipment_name": eq.name,
                "request_date": repair.request_date.isoformat(),
                "repair_date": repair.repair_date.isoformat() if repair.repair_date else None,
                "status": repair.status,
                "cost": float(repair.cost) if repair.cost else None,
            }
            for repair, eq in rows
        ]

        return _json_response(data)


def create_equipment_repair(request: Request) -> Response:
    """POST /api/equipment/repairs - Tạo phiếu sửa chữa."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["equipment_id", "request_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        try:
            eq_id = uuid.UUID(data["equipment_id"])
            equipment = db.query(Equipment).filter(Equipment.id == eq_id).first()
            if not equipment:
                return _json_response({"error": "Thiết bị không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid equipment_id"}, 400)

        request_date = _parse_date(data["request_date"])

        count_today = (
            db.query(EquipmentRepair)
            .filter(EquipmentRepair.request_date == request_date)
            .count()
        )
        code = f"SC{request_date.strftime('%Y%m%d')}-{count_today + 1:03d}"

        repair_date = None
        if data.get("repair_date"):
            try:
                repair_date = _parse_date(data["repair_date"])
            except ValueError:
                return _json_response({"error": "Invalid repair_date format"}, 400)

        repair = EquipmentRepair(
            code=code,
            equipment_id=eq_id,
            request_date=request_date,
            repair_date=repair_date,
            description=data.get("description"),
            issue_description=data.get("issue_description"),
            repair_description=data.get("repair_description"),
            cost=float(data["cost"]) if data.get("cost") else None,
            status=data.get("status", "requested"),
            repaired_by=data.get("repaired_by"),
            note=data.get("note"),
        )
        db.add(repair)
        db.flush()

        # Tạo các dòng chi tiết
        lines_data = data.get("lines", [])
        total_cost = 0.0
        for line_data in lines_data:
            line = EquipmentRepairLine(
                repair_id=repair.id,
                item_description=line_data.get("item_description", ""),
                quantity=float(line_data.get("quantity", 0)),
                unit_price=float(line_data.get("unit_price", 0)),
                line_amount=float(line_data.get("quantity", 0))
                * float(line_data.get("unit_price", 0)),
                note=line_data.get("note"),
            )
            db.add(line)
            total_cost += line.line_amount

        if total_cost > 0 and not repair.cost:
            repair.cost = total_cost

        return _json_response({
            "id": str(repair.id),
            "code": repair.code,
        }, 201)


# Maintenance APIs
def list_maintenance_records(request: Request) -> Response:
    """GET /api/equipment/maintenance - Danh sách lịch sử bảo dưỡng."""
    equipment_id = request.query_params.get("equipment_id")
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
        query = db.query(MaintenanceRecord, Equipment).join(Equipment)

        if equipment_id:
            try:
                eq_id = uuid.UUID(equipment_id)
                query = query.filter(MaintenanceRecord.equipment_id == eq_id)
            except ValueError:
                return _json_response({"error": "Invalid equipment_id"}, 400)

        if start_date:
            query = query.filter(MaintenanceRecord.maintenance_date >= start_date)
        if end_date:
            query = query.filter(MaintenanceRecord.maintenance_date <= end_date)

        rows = query.order_by(MaintenanceRecord.maintenance_date.desc()).limit(100).all()

        data = [
            {
                "id": str(record.id),
                "equipment_code": eq.code,
                "equipment_name": eq.name,
                "maintenance_date": record.maintenance_date.isoformat(),
                "maintenance_type": record.maintenance_type,
                "performed_by": record.performed_by,
                "cost": float(record.cost) if record.cost else None,
                "next_maintenance_date": record.next_maintenance_date.isoformat()
                if record.next_maintenance_date
                else None,
            }
            for record, eq in rows
        ]

        return _json_response(data)


def create_maintenance_record(request: Request) -> Response:
    """POST /api/equipment/maintenance - Tạo bản ghi bảo dưỡng."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["equipment_id", "maintenance_date", "maintenance_type"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        try:
            eq_id = uuid.UUID(data["equipment_id"])
            equipment = db.query(Equipment).filter(Equipment.id == eq_id).first()
            if not equipment:
                return _json_response({"error": "Thiết bị không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid equipment_id"}, 400)

        maintenance_date = _parse_date(data["maintenance_date"])

        next_maintenance_date = None
        if data.get("next_maintenance_date"):
            try:
                next_maintenance_date = _parse_date(data["next_maintenance_date"])
            except ValueError:
                return _json_response({"error": "Invalid next_maintenance_date format"}, 400)

        record = MaintenanceRecord(
            equipment_id=eq_id,
            schedule_id=uuid.UUID(data["schedule_id"]) if data.get("schedule_id") else None,
            maintenance_date=maintenance_date,
            maintenance_hours=float(data["maintenance_hours"])
            if data.get("maintenance_hours")
            else None,
            maintenance_type=data["maintenance_type"],
            description=data.get("description"),
            performed_by=data.get("performed_by"),
            cost=float(data["cost"]) if data.get("cost") else None,
            next_maintenance_date=next_maintenance_date,
            next_maintenance_hours=float(data["next_maintenance_hours"])
            if data.get("next_maintenance_hours")
            else None,
            note=data.get("note"),
        )
        db.add(record)
        db.flush()

        return _json_response({
            "id": str(record.id),
            "equipment_id": str(record.equipment_id),
            "maintenance_date": record.maintenance_date.isoformat(),
        }, 201)


def create_maintenance_schedule(request: Request) -> Response:
    """POST /api/equipment/maintenance/schedules - Tạo lịch bảo dưỡng."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["equipment_id", "maintenance_type"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        try:
            eq_id = uuid.UUID(data["equipment_id"])
            equipment = db.query(Equipment).filter(Equipment.id == eq_id).first()
            if not equipment:
                return _json_response({"error": "Thiết bị không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid equipment_id"}, 400)

        next_maintenance_date = None
        if data.get("next_maintenance_date"):
            try:
                next_maintenance_date = _parse_date(data["next_maintenance_date"])
            except ValueError:
                return _json_response({"error": "Invalid next_maintenance_date format"}, 400)

        schedule = MaintenanceSchedule(
            equipment_id=eq_id,
            maintenance_type=data["maintenance_type"],
            interval_days=int(data["interval_days"]) if data.get("interval_days") else None,
            interval_hours=float(data["interval_hours"])
            if data.get("interval_hours")
            else None,
            next_maintenance_date=next_maintenance_date,
            next_maintenance_hours=float(data["next_maintenance_hours"])
            if data.get("next_maintenance_hours")
            else None,
            is_active=data.get("is_active", True),
            note=data.get("note"),
        )
        db.add(schedule)
        db.flush()

        return _json_response({
            "id": str(schedule.id),
            "equipment_id": str(schedule.equipment_id),
            "maintenance_type": schedule.maintenance_type,
        }, 201)

