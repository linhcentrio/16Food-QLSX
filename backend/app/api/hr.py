"""
API cho module Hành chính Nhân sự: Time tracking và tính lương.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime

from robyn import Request, Response

from ..core.db import get_session
from ..core.error_handler import json_response as _json_response, ValidationError, NotFoundError
from ..models.entities import TimeSheet, Employee, Department, JobTitle


def _parse_date(value: str) -> date:
    """Parse date từ string."""
    return date.fromisoformat(value)


def create_timesheet(request: Request) -> Response:
    """
    POST /api/hr/timesheets
    
    Tạo bản ghi chấm công.
    
    Payload:
    {
      "employee_code": "NV001",
      "work_date": "2025-01-15",
      "shift": "Ca sáng",
      "working_hours": 8.0,
      "overtime_hours": 0.0
    }
    """
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)
    
    required_fields = ["employee_code", "work_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )
    
    with get_session() as db:
        employee = (
            db.query(Employee)
            .filter(Employee.code == data["employee_code"])
            .first()
        )
        if not employee:
            return _json_response({"error": "Nhân viên không tồn tại"}, 404)
        
        work_date = _parse_date(data["work_date"])
        
        # Kiểm tra xem đã có bản ghi chấm công chưa
        existing = (
            db.query(TimeSheet)
            .filter(
                TimeSheet.employee_id == employee.id,
                TimeSheet.work_date == work_date,
            )
            .first()
        )
        if existing:
            return _json_response(
                {"error": "Đã có bản ghi chấm công cho ngày này"}, 400
            )
        
        timesheet = TimeSheet(
            work_date=work_date,
            employee_id=employee.id,
            shift=data.get("shift"),
            working_hours=float(data.get("working_hours", 0)),
            overtime_hours=float(data.get("overtime_hours", 0)),
        )
        db.add(timesheet)
        db.flush()
        
        return _json_response({
            "id": str(timesheet.id),
            "employee_code": employee.code,
            "employee_name": employee.full_name,
            "work_date": work_date.isoformat(),
            "working_hours": float(timesheet.working_hours),
            "overtime_hours": float(timesheet.overtime_hours),
        }, 201)


def list_timesheets(request: Request) -> Response:
    """
    GET /api/hr/timesheets
    
    Danh sách chấm công.
    
    Query params:
    - employee_code: Lọc theo mã nhân viên
    - start_date: Ngày bắt đầu
    - end_date: Ngày kết thúc
    """
    employee_code = request.query_params.get("employee_code")
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
            db.query(TimeSheet, Employee)
            .join(Employee, TimeSheet.employee_id == Employee.id)
        )
        
        if employee_code:
            query = query.filter(Employee.code == employee_code)
        if start_date:
            query = query.filter(TimeSheet.work_date >= start_date)
        if end_date:
            query = query.filter(TimeSheet.work_date <= end_date)
        
        rows = query.order_by(TimeSheet.work_date.desc()).limit(100).all()
        
        data = [
            {
                "id": str(ts.id),
                "employee_code": emp.code,
                "employee_name": emp.full_name,
                "work_date": ts.work_date.isoformat(),
                "shift": ts.shift,
                "working_hours": float(ts.working_hours),
                "overtime_hours": float(ts.overtime_hours),
            }
            for ts, emp in rows
        ]
        
        return _json_response(data)


def calculate_salary(request: Request) -> Response:
    """
    POST /api/hr/salary/calculate
    
    Tính lương cho nhân viên trong kỳ.
    
    Payload:
    {
      "employee_code": "NV001",
      "start_date": "2025-01-01",
      "end_date": "2025-01-31"
    }
    """
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)
    
    required_fields = ["employee_code", "start_date", "end_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )
    
    with get_session() as db:
        employee = (
            db.query(Employee, JobTitle)
            .join(JobTitle, Employee.job_title_id == JobTitle.id)
            .filter(Employee.code == data["employee_code"])
            .first()
        )
        if not employee:
            return _json_response({"error": "Nhân viên không tồn tại"}, 404)
        
        emp, job_title = employee
        
        start_date = _parse_date(data["start_date"])
        end_date = _parse_date(data["end_date"])
        
        # Lấy tất cả chấm công trong kỳ
        timesheets = (
            db.query(TimeSheet)
            .filter(
                TimeSheet.employee_id == emp.id,
                TimeSheet.work_date >= start_date,
                TimeSheet.work_date <= end_date,
            )
            .all()
        )
        
        total_working_hours = sum(float(ts.working_hours) for ts in timesheets)
        total_overtime_hours = sum(float(ts.overtime_hours) for ts in timesheets)
        
        # Tính lương cơ bản
        base_salary = float(job_title.base_salary or 0)
        hourly_rate = base_salary / 176 if base_salary > 0 else 0  # Giả sử 176 giờ/tháng
        regular_salary = total_working_hours * hourly_rate
        overtime_rate = hourly_rate * 1.5  # Tăng ca 1.5 lần
        overtime_salary = total_overtime_hours * overtime_rate
        total_salary = regular_salary + overtime_salary
        
        return _json_response({
            "employee_code": emp.code,
            "employee_name": emp.full_name,
            "job_title": job_title.name,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "attendance": {
                "total_days": len(timesheets),
                "total_working_hours": total_working_hours,
                "total_overtime_hours": total_overtime_hours,
            },
            "salary": {
                "base_salary": base_salary,
                "hourly_rate": hourly_rate,
                "regular_salary": regular_salary,
                "overtime_salary": overtime_salary,
                "total_salary": total_salary,
            },
        })

