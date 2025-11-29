"""
API mở rộng cho Module HCNS.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime

from robyn import Request, Response

from ..core.db import get_session
from ..core.error_handler import json_response as _json_response, ValidationError, NotFoundError
from ..models.hr_extended import (
    EmploymentContract,
    PerformanceReview,
    TrainingRecord,
    ExitProcess,
)
from ..models.entities import Employee


def _parse_date(value: str) -> date:
    """Parse date từ string."""
    return date.fromisoformat(value)


# Employment Contract APIs
def list_employment_contracts(request: Request) -> Response:
    """GET /api/hr/contracts - Danh sách hợp đồng lao động."""
    employee_id = request.query_params.get("employee_id")
    status = request.query_params.get("status")

    with get_session() as db:
        query = db.query(EmploymentContract, Employee).join(Employee)

        if employee_id:
            try:
                emp_id = uuid.UUID(employee_id)
                query = query.filter(EmploymentContract.employee_id == emp_id)
            except ValueError:
                return _json_response({"error": "Invalid employee_id"}, 400)

        if status:
            query = query.filter(EmploymentContract.status == status)

        rows = query.order_by(EmploymentContract.start_date.desc()).limit(100).all()

        data = [
            {
                "id": str(contract.id),
                "contract_number": contract.contract_number,
                "employee_code": emp.code,
                "employee_name": emp.full_name,
                "contract_type": contract.contract_type,
                "start_date": contract.start_date.isoformat(),
                "end_date": contract.end_date.isoformat() if contract.end_date else None,
                "salary": float(contract.salary) if contract.salary else None,
                "status": contract.status,
            }
            for contract, emp in rows
        ]

        return _json_response(data)


def create_employment_contract(request: Request) -> Response:
    """POST /api/hr/contracts - Tạo hợp đồng lao động."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["employee_id", "contract_number", "contract_type", "start_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        try:
            emp_id = uuid.UUID(data["employee_id"])
            employee = db.query(Employee).filter(Employee.id == emp_id).first()
            if not employee:
                return _json_response({"error": "Nhân viên không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid employee_id"}, 400)

        existing = (
            db.query(EmploymentContract)
            .filter(EmploymentContract.contract_number == data["contract_number"])
            .first()
        )
        if existing:
            return _json_response({"error": "Số hợp đồng đã tồn tại"}, 400)

        start_date = _parse_date(data["start_date"])
        end_date = None
        if data.get("end_date"):
            try:
                end_date = _parse_date(data["end_date"])
            except ValueError:
                return _json_response({"error": "Invalid end_date format"}, 400)

        contract = EmploymentContract(
            employee_id=emp_id,
            contract_number=data["contract_number"],
            contract_type=data["contract_type"],
            start_date=start_date,
            end_date=end_date,
            salary=float(data["salary"]) if data.get("salary") else None,
            position=data.get("position"),
            department=data.get("department"),
            status=data.get("status", "active"),
            file_url=data.get("file_url"),
            note=data.get("note"),
        )
        db.add(contract)
        db.flush()

        return _json_response({
            "id": str(contract.id),
            "contract_number": contract.contract_number,
        }, 201)


# Performance Review APIs
def list_performance_reviews(request: Request) -> Response:
    """GET /api/hr/performance-reviews - Danh sách đánh giá hiệu suất."""
    employee_id = request.query_params.get("employee_id")

    with get_session() as db:
        query = db.query(PerformanceReview, Employee).join(Employee)

        if employee_id:
            try:
                emp_id = uuid.UUID(employee_id)
                query = query.filter(PerformanceReview.employee_id == emp_id)
            except ValueError:
                return _json_response({"error": "Invalid employee_id"}, 400)

        rows = query.order_by(PerformanceReview.review_date.desc()).limit(100).all()

        data = [
            {
                "id": str(review.id),
                "employee_code": emp.code,
                "employee_name": emp.full_name,
                "review_date": review.review_date.isoformat(),
                "review_period": f"{review.review_period_start.isoformat()} - {review.review_period_end.isoformat()}",
                "overall_score": float(review.overall_score),
                "rating": review.rating,
            }
            for review, emp in rows
        ]

        return _json_response(data)


def create_performance_review(request: Request) -> Response:
    """POST /api/hr/performance-reviews - Tạo đánh giá hiệu suất."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["employee_id", "review_period_start", "review_period_end", "review_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        try:
            emp_id = uuid.UUID(data["employee_id"])
            employee = db.query(Employee).filter(Employee.id == emp_id).first()
            if not employee:
                return _json_response({"error": "Nhân viên không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid employee_id"}, 400)

        period_start = _parse_date(data["review_period_start"])
        period_end = _parse_date(data["review_period_end"])
        review_date = _parse_date(data["review_date"])

        # Tính điểm trung bình
        scores = []
        if data.get("work_quality_score"):
            scores.append(float(data["work_quality_score"]))
        if data.get("productivity_score"):
            scores.append(float(data["productivity_score"]))
        if data.get("teamwork_score"):
            scores.append(float(data["teamwork_score"]))
        if data.get("communication_score"):
            scores.append(float(data["communication_score"]))

        overall_score = sum(scores) / len(scores) if scores else 0.0

        # Xác định rating
        if overall_score >= 90:
            rating = "Excellent"
        elif overall_score >= 75:
            rating = "Good"
        elif overall_score >= 60:
            rating = "Satisfactory"
        else:
            rating = "Needs Improvement"

        review = PerformanceReview(
            employee_id=emp_id,
            review_period_start=period_start,
            review_period_end=period_end,
            review_date=review_date,
            reviewed_by=data.get("reviewed_by"),
            work_quality_score=float(data["work_quality_score"]) if data.get("work_quality_score") else None,
            productivity_score=float(data["productivity_score"]) if data.get("productivity_score") else None,
            teamwork_score=float(data["teamwork_score"]) if data.get("teamwork_score") else None,
            communication_score=float(data["communication_score"]) if data.get("communication_score") else None,
            overall_score=overall_score,
            rating=rating,
            strengths=data.get("strengths"),
            areas_for_improvement=data.get("areas_for_improvement"),
            goals=data.get("goals"),
            comments=data.get("comments"),
        )
        db.add(review)
        db.flush()

        return _json_response({
            "id": str(review.id),
            "employee_id": str(review.employee_id),
            "overall_score": float(overall_score),
            "rating": rating,
        }, 201)


# Training Record APIs
def list_training_records(request: Request) -> Response:
    """GET /api/hr/training-records - Danh sách ghi nhận đào tạo."""
    employee_id = request.query_params.get("employee_id")
    training_type = request.query_params.get("training_type")

    with get_session() as db:
        query = db.query(TrainingRecord, Employee).join(Employee)

        if employee_id:
            try:
                emp_id = uuid.UUID(employee_id)
                query = query.filter(TrainingRecord.employee_id == emp_id)
            except ValueError:
                return _json_response({"error": "Invalid employee_id"}, 400)

        if training_type:
            query = query.filter(TrainingRecord.training_type == training_type)

        rows = query.order_by(TrainingRecord.training_date.desc()).limit(100).all()

        data = [
            {
                "id": str(record.id),
                "employee_code": emp.code,
                "employee_name": emp.full_name,
                "training_name": record.training_name,
                "training_type": record.training_type,
                "training_date": record.training_date.isoformat(),
                "duration_hours": float(record.duration_hours) if record.duration_hours else None,
                "status": record.status,
            }
            for record, emp in rows
        ]

        return _json_response(data)


def create_training_record(request: Request) -> Response:
    """POST /api/hr/training-records - Tạo ghi nhận đào tạo."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["employee_id", "training_name", "training_type", "training_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        try:
            emp_id = uuid.UUID(data["employee_id"])
            employee = db.query(Employee).filter(Employee.id == emp_id).first()
            if not employee:
                return _json_response({"error": "Nhân viên không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid employee_id"}, 400)

        training_date = _parse_date(data["training_date"])

        record = TrainingRecord(
            employee_id=emp_id,
            training_name=data["training_name"],
            training_type=data["training_type"],
            training_date=training_date,
            duration_hours=float(data["duration_hours"]) if data.get("duration_hours") else None,
            trainer=data.get("trainer"),
            location=data.get("location"),
            certificate_number=data.get("certificate_number"),
            score=float(data["score"]) if data.get("score") else None,
            status=data.get("status", "completed"),
            description=data.get("description"),
            file_url=data.get("file_url"),
        )
        db.add(record)
        db.flush()

        return _json_response({
            "id": str(record.id),
            "employee_id": str(record.employee_id),
            "training_name": record.training_name,
        }, 201)


# Exit Process APIs
def list_exit_processes(request: Request) -> Response:
    """GET /api/hr/exit-processes - Danh sách quy trình nghỉ việc."""
    employee_id = request.query_params.get("employee_id")
    status = request.query_params.get("status")

    with get_session() as db:
        query = db.query(ExitProcess, Employee).join(Employee)

        if employee_id:
            try:
                emp_id = uuid.UUID(employee_id)
                query = query.filter(ExitProcess.employee_id == emp_id)
            except ValueError:
                return _json_response({"error": "Invalid employee_id"}, 400)

        if status:
            query = query.filter(ExitProcess.status == status)

        rows = query.order_by(ExitProcess.resignation_date.desc()).limit(100).all()

        data = [
            {
                "id": str(process.id),
                "employee_code": emp.code,
                "employee_name": emp.full_name,
                "resignation_date": process.resignation_date.isoformat(),
                "last_working_date": process.last_working_date.isoformat(),
                "exit_type": process.exit_type,
                "status": process.status,
                "handover_completed": process.handover_completed,
                "assets_returned": process.assets_returned,
                "final_settlement": process.final_settlement,
            }
            for process, emp in rows
        ]

        return _json_response(data)


def create_exit_process(request: Request) -> Response:
    """POST /api/hr/exit-processes - Tạo quy trình nghỉ việc."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["employee_id", "resignation_date", "last_working_date", "exit_type"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        try:
            emp_id = uuid.UUID(data["employee_id"])
            employee = db.query(Employee).filter(Employee.id == emp_id).first()
            if not employee:
                return _json_response({"error": "Nhân viên không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid employee_id"}, 400)

        resignation_date = _parse_date(data["resignation_date"])
        last_working_date = _parse_date(data["last_working_date"])

        exit_interview_date = None
        if data.get("exit_interview_date"):
            try:
                exit_interview_date = _parse_date(data["exit_interview_date"])
            except ValueError:
                return _json_response({"error": "Invalid exit_interview_date format"}, 400)

        process = ExitProcess(
            employee_id=emp_id,
            resignation_date=resignation_date,
            last_working_date=last_working_date,
            exit_type=data["exit_type"],
            reason=data.get("reason"),
            exit_interview_date=exit_interview_date,
            exit_interview_notes=data.get("exit_interview_notes"),
            handover_completed=data.get("handover_completed", False),
            handover_notes=data.get("handover_notes"),
            assets_returned=data.get("assets_returned", False),
            final_settlement=data.get("final_settlement", False),
            final_settlement_amount=float(data["final_settlement_amount"]) if data.get("final_settlement_amount") else None,
            status=data.get("status", "initiated"),
            note=data.get("note"),
        )
        db.add(process)
        db.flush()

        # Cập nhật trạng thái nhân viên
        employee.status = "inactive"
        employee.leave_date = last_working_date

        return _json_response({
            "id": str(process.id),
            "employee_id": str(process.employee_id),
            "exit_type": process.exit_type,
        }, 201)

