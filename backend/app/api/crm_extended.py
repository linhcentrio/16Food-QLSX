"""
API mở rộng cho Module CRM.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta

from robyn import Request, Response

from ..core.db import get_session
from ..core.error_handler import json_response as _json_response, ValidationError, NotFoundError
from ..models.crm_extended import (
    AccountsReceivable,
    AccountsPayable,
    SupplierContract,
    SupplierEvaluation,
    CustomerSegment,
    CustomerFeedback,
    KpiMetric,
    KpiRecord,
)
from ..models.entities import Customer, Supplier, SalesOrder, PurchaseOrder
from ..services.crm_analytics import (
    analyze_customer_purchase_behavior,
    get_customer_segmentation,
    get_customer_product_preferences,
)


def _parse_date(value: str) -> date:
    """Parse date từ string."""
    return date.fromisoformat(value)


# Accounts Receivable APIs
def list_accounts_receivable(request: Request) -> Response:
    """GET /api/crm/accounts-receivable - Danh sách công nợ phải thu."""
    customer_id = request.query_params.get("customer_id")
    status = request.query_params.get("status")
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
        query = db.query(AccountsReceivable, Customer).join(Customer)

        if customer_id:
            try:
                cust_id = uuid.UUID(customer_id)
                query = query.filter(AccountsReceivable.customer_id == cust_id)
            except ValueError:
                return _json_response({"error": "Invalid customer_id"}, 400)

        if status:
            query = query.filter(AccountsReceivable.status == status)
        if start_date:
            query = query.filter(AccountsReceivable.transaction_date >= start_date)
        if end_date:
            query = query.filter(AccountsReceivable.transaction_date <= end_date)

        rows = query.order_by(AccountsReceivable.due_date).limit(200).all()

        data = [
            {
                "id": str(ar.id),
                "customer_code": cust.code,
                "customer_name": cust.name,
                "transaction_date": ar.transaction_date.isoformat(),
                "due_date": ar.due_date.isoformat(),
                "amount": float(ar.amount),
                "paid_amount": float(ar.paid_amount),
                "remaining_amount": float(ar.remaining_amount),
                "status": ar.status,
                "invoice_number": ar.invoice_number,
            }
            for ar, cust in rows
        ]

        return _json_response(data)


def create_accounts_receivable(request: Request) -> Response:
    """POST /api/crm/accounts-receivable - Tạo công nợ phải thu."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["customer_id", "transaction_date", "due_date", "amount"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        try:
            cust_id = uuid.UUID(data["customer_id"])
            customer = db.query(Customer).filter(Customer.id == cust_id).first()
            if not customer:
                return _json_response({"error": "Khách hàng không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid customer_id"}, 400)

        transaction_date = _parse_date(data["transaction_date"])
        due_date = _parse_date(data["due_date"])
        amount = float(data["amount"])
        paid_amount = float(data.get("paid_amount", 0))
        remaining_amount = amount - paid_amount

        sales_order_id = None
        if data.get("sales_order_id"):
            try:
                sales_order_id = uuid.UUID(data["sales_order_id"])
            except ValueError:
                return _json_response({"error": "Invalid sales_order_id"}, 400)

        ar = AccountsReceivable(
            customer_id=cust_id,
            sales_order_id=sales_order_id,
            transaction_date=transaction_date,
            due_date=due_date,
            invoice_number=data.get("invoice_number"),
            amount=amount,
            paid_amount=paid_amount,
            remaining_amount=remaining_amount,
            status="paid" if remaining_amount == 0 else ("partial" if paid_amount > 0 else "unpaid"),
            payment_terms=data.get("payment_terms"),
            note=data.get("note"),
        )
        db.add(ar)
        db.flush()

        return _json_response({
            "id": str(ar.id),
            "customer_id": str(ar.customer_id),
            "remaining_amount": float(ar.remaining_amount),
        }, 201)


# Accounts Payable APIs
def list_accounts_payable(request: Request) -> Response:
    """GET /api/crm/accounts-payable - Danh sách công nợ phải trả."""
    supplier_id = request.query_params.get("supplier_id")
    status = request.query_params.get("status")

    with get_session() as db:
        query = db.query(AccountsPayable, Supplier).join(Supplier)

        if supplier_id:
            try:
                sup_id = uuid.UUID(supplier_id)
                query = query.filter(AccountsPayable.supplier_id == sup_id)
            except ValueError:
                return _json_response({"error": "Invalid supplier_id"}, 400)

        if status:
            query = query.filter(AccountsPayable.status == status)

        rows = query.order_by(AccountsPayable.due_date).limit(200).all()

        data = [
            {
                "id": str(ap.id),
                "supplier_code": sup.code,
                "supplier_name": sup.name,
                "transaction_date": ap.transaction_date.isoformat(),
                "due_date": ap.due_date.isoformat(),
                "amount": float(ap.amount),
                "paid_amount": float(ap.paid_amount),
                "remaining_amount": float(ap.remaining_amount),
                "status": ap.status,
            }
            for ap, sup in rows
        ]

        return _json_response(data)


# Supplier Contract APIs
def list_supplier_contracts(request: Request) -> Response:
    """GET /api/crm/supplier-contracts - Danh sách hợp đồng nhà cung cấp."""
    supplier_id = request.query_params.get("supplier_id")
    status = request.query_params.get("status")

    with get_session() as db:
        query = db.query(SupplierContract, Supplier).join(Supplier)

        if supplier_id:
            try:
                sup_id = uuid.UUID(supplier_id)
                query = query.filter(SupplierContract.supplier_id == sup_id)
            except ValueError:
                return _json_response({"error": "Invalid supplier_id"}, 400)

        if status:
            query = query.filter(SupplierContract.status == status)

        rows = query.order_by(SupplierContract.start_date.desc()).limit(100).all()

        data = [
            {
                "id": str(contract.id),
                "contract_number": contract.contract_number,
                "supplier_code": sup.code,
                "supplier_name": sup.name,
                "contract_type": contract.contract_type,
                "start_date": contract.start_date.isoformat(),
                "end_date": contract.end_date.isoformat() if contract.end_date else None,
                "status": contract.status,
            }
            for contract, sup in rows
        ]

        return _json_response(data)


def create_supplier_contract(request: Request) -> Response:
    """POST /api/crm/supplier-contracts - Tạo hợp đồng nhà cung cấp."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["supplier_id", "contract_number", "contract_type", "start_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        try:
            sup_id = uuid.UUID(data["supplier_id"])
            supplier = db.query(Supplier).filter(Supplier.id == sup_id).first()
            if not supplier:
                return _json_response({"error": "Nhà cung cấp không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid supplier_id"}, 400)

        existing = (
            db.query(SupplierContract)
            .filter(SupplierContract.contract_number == data["contract_number"])
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

        contract = SupplierContract(
            supplier_id=sup_id,
            contract_number=data["contract_number"],
            contract_type=data["contract_type"],
            start_date=start_date,
            end_date=end_date,
            payment_terms=data.get("payment_terms"),
            delivery_terms=data.get("delivery_terms"),
            quality_requirements=data.get("quality_requirements"),
            penalty_clause=data.get("penalty_clause"),
            contract_terms=data.get("contract_terms"),
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


# Supplier Evaluation APIs
def list_supplier_evaluations(request: Request) -> Response:
    """GET /api/crm/supplier-evaluations - Danh sách đánh giá nhà cung cấp."""
    supplier_id = request.query_params.get("supplier_id")

    with get_session() as db:
        query = db.query(SupplierEvaluation, Supplier).join(Supplier)

        if supplier_id:
            try:
                sup_id = uuid.UUID(supplier_id)
                query = query.filter(SupplierEvaluation.supplier_id == sup_id)
            except ValueError:
                return _json_response({"error": "Invalid supplier_id"}, 400)

        rows = query.order_by(SupplierEvaluation.evaluation_date.desc()).limit(100).all()

        data = [
            {
                "id": str(eval.id),
                "supplier_code": sup.code,
                "supplier_name": sup.name,
                "evaluation_date": eval.evaluation_date.isoformat(),
                "overall_score": float(eval.overall_score),
                "rating": eval.rating,
                "quality_score": float(eval.quality_score) if eval.quality_score else None,
                "delivery_score": float(eval.delivery_score) if eval.delivery_score else None,
            }
            for eval, sup in rows
        ]

        return _json_response(data)


def create_supplier_evaluation(request: Request) -> Response:
    """POST /api/crm/supplier-evaluations - Tạo đánh giá nhà cung cấp."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["supplier_id", "evaluation_date", "evaluation_period_start", "evaluation_period_end"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        try:
            sup_id = uuid.UUID(data["supplier_id"])
            supplier = db.query(Supplier).filter(Supplier.id == sup_id).first()
            if not supplier:
                return _json_response({"error": "Nhà cung cấp không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid supplier_id"}, 400)

        evaluation_date = _parse_date(data["evaluation_date"])
        period_start = _parse_date(data["evaluation_period_start"])
        period_end = _parse_date(data["evaluation_period_end"])

        # Tính điểm trung bình
        scores = []
        if data.get("quality_score"):
            scores.append(float(data["quality_score"]))
        if data.get("delivery_score"):
            scores.append(float(data["delivery_score"]))
        if data.get("price_score"):
            scores.append(float(data["price_score"]))
        if data.get("service_score"):
            scores.append(float(data["service_score"]))

        overall_score = sum(scores) / len(scores) if scores else 0.0

        # Xác định rating
        if overall_score >= 90:
            rating = "Excellent"
        elif overall_score >= 75:
            rating = "Good"
        elif overall_score >= 60:
            rating = "Fair"
        else:
            rating = "Poor"

        contract_id = None
        if data.get("contract_id"):
            try:
                contract_id = uuid.UUID(data["contract_id"])
            except ValueError:
                return _json_response({"error": "Invalid contract_id"}, 400)

        evaluation = SupplierEvaluation(
            supplier_id=sup_id,
            contract_id=contract_id,
            evaluation_date=evaluation_date,
            evaluation_period_start=period_start,
            evaluation_period_end=period_end,
            evaluated_by=data.get("evaluated_by"),
            quality_score=float(data["quality_score"]) if data.get("quality_score") else None,
            delivery_score=float(data["delivery_score"]) if data.get("delivery_score") else None,
            price_score=float(data["price_score"]) if data.get("price_score") else None,
            service_score=float(data["service_score"]) if data.get("service_score") else None,
            overall_score=overall_score,
            on_time_delivery_rate=float(data["on_time_delivery_rate"]) if data.get("on_time_delivery_rate") else None,
            defect_rate=float(data["defect_rate"]) if data.get("defect_rate") else None,
            total_orders=int(data["total_orders"]) if data.get("total_orders") else None,
            total_value=float(data["total_value"]) if data.get("total_value") else None,
            rating=rating,
            comments=data.get("comments"),
            recommendations=data.get("recommendations"),
        )
        db.add(evaluation)
        db.flush()

        # Cập nhật rating của supplier
        supplier.rating = overall_score

        return _json_response({
            "id": str(evaluation.id),
            "supplier_id": str(evaluation.supplier_id),
            "overall_score": float(overall_score),
            "rating": rating,
        }, 201)


# Customer Segmentation APIs
def get_customer_segmentation_analysis(request: Request) -> Response:
    """GET /api/crm/customer-segmentation - Phân khúc khách hàng."""
    with get_session() as db:
        segments = get_customer_segmentation(db)
        return _json_response(segments)


# Customer Purchase Behavior Analysis
def get_customer_purchase_behavior(request: Request) -> Response:
    """GET /api/crm/customer-behavior - Phân tích hành vi mua hàng."""
    customer_id = request.query_params.get("customer_id")
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
        behavior = analyze_customer_purchase_behavior(db, customer_id, start_date, end_date)
        return _json_response(behavior)


def get_customer_product_preferences_api(request: Request) -> Response:
    """GET /api/crm/customer-product-preferences - Sản phẩm ưa thích của khách hàng."""
    customer_id = request.query_params.get("customer_id")
    if not customer_id:
        return _json_response({"error": "customer_id is required"}, 400)

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
        preferences = get_customer_product_preferences(db, customer_id, start_date, end_date)
        return _json_response(preferences)


# Customer Feedback APIs
def list_customer_feedback(request: Request) -> Response:
    """GET /api/crm/customer-feedback - Danh sách phản hồi khách hàng."""
    customer_id = request.query_params.get("customer_id")
    status = request.query_params.get("status")
    feedback_type = request.query_params.get("feedback_type")

    with get_session() as db:
        query = db.query(CustomerFeedback, Customer).join(Customer)

        if customer_id:
            try:
                cust_id = uuid.UUID(customer_id)
                query = query.filter(CustomerFeedback.customer_id == cust_id)
            except ValueError:
                return _json_response({"error": "Invalid customer_id"}, 400)

        if status:
            query = query.filter(CustomerFeedback.status == status)
        if feedback_type:
            query = query.filter(CustomerFeedback.feedback_type == feedback_type)

        rows = query.order_by(CustomerFeedback.feedback_date.desc()).limit(100).all()

        data = [
            {
                "id": str(fb.id),
                "customer_code": cust.code,
                "customer_name": cust.name,
                "feedback_date": fb.feedback_date.isoformat(),
                "feedback_type": fb.feedback_type,
                "category": fb.category,
                "rating": fb.rating,
                "subject": fb.subject,
                "status": fb.status,
            }
            for fb, cust in rows
        ]

        return _json_response(data)


def create_customer_feedback(request: Request) -> Response:
    """POST /api/crm/customer-feedback - Tạo phản hồi khách hàng."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["customer_id", "feedback_date", "feedback_type", "content"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        try:
            cust_id = uuid.UUID(data["customer_id"])
            customer = db.query(Customer).filter(Customer.id == cust_id).first()
            if not customer:
                return _json_response({"error": "Khách hàng không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid customer_id"}, 400)

        feedback_date = _parse_date(data["feedback_date"])

        sales_order_id = None
        if data.get("sales_order_id"):
            try:
                sales_order_id = uuid.UUID(data["sales_order_id"])
            except ValueError:
                return _json_response({"error": "Invalid sales_order_id"}, 400)

        feedback = CustomerFeedback(
            customer_id=cust_id,
            sales_order_id=sales_order_id,
            feedback_date=feedback_date,
            feedback_type=data["feedback_type"],
            category=data.get("category"),
            rating=int(data["rating"]) if data.get("rating") else None,
            subject=data.get("subject"),
            content=data["content"],
            status=data.get("status", "new"),
            assigned_to=data.get("assigned_to"),
        )
        db.add(feedback)
        db.flush()

        return _json_response({
            "id": str(feedback.id),
            "customer_id": str(feedback.customer_id),
            "feedback_type": feedback.feedback_type,
        }, 201)


# KPI APIs
def list_kpi_metrics() -> Response:
    """GET /api/crm/kpi-metrics - Danh sách KPI metrics."""
    with get_session() as db:
        metrics = db.query(KpiMetric).filter(KpiMetric.is_active == True).order_by(KpiMetric.code).all()

        data = [
            {
                "id": str(m.id),
                "code": m.code,
                "name": m.name,
                "category": m.category,
                "unit": m.unit,
                "target_value": float(m.target_value) if m.target_value else None,
                "current_value": float(m.current_value) if m.current_value else None,
            }
            for m in metrics
        ]

        return _json_response(data)


def create_kpi_metric(request: Request) -> Response:
    """POST /api/crm/kpi-metrics - Tạo KPI metric mới."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["code", "name", "category"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        existing = db.query(KpiMetric).filter(KpiMetric.code == data["code"]).first()
        if existing:
            return _json_response({"error": "Mã KPI đã tồn tại"}, 400)

        metric = KpiMetric(
            code=data["code"],
            name=data["name"],
            category=data["category"],
            unit=data.get("unit"),
            target_value=float(data["target_value"]) if data.get("target_value") else None,
            current_value=float(data["current_value"]) if data.get("current_value") else None,
            calculation_formula=data.get("calculation_formula"),
            is_active=data.get("is_active", True),
            note=data.get("note"),
        )
        db.add(metric)
        db.flush()

        return _json_response({
            "id": str(metric.id),
            "code": metric.code,
            "name": metric.name,
        }, 201)


def list_kpi_records(request: Request) -> Response:
    """GET /api/crm/kpi-records - Danh sách ghi nhận KPI."""
    kpi_metric_id = request.query_params.get("kpi_metric_id")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")
    period_type = request.query_params.get("period_type")

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
        query = db.query(KpiRecord, KpiMetric).join(KpiMetric)

        if kpi_metric_id:
            try:
                kpi_id = uuid.UUID(kpi_metric_id)
                query = query.filter(KpiRecord.kpi_metric_id == kpi_id)
            except ValueError:
                return _json_response({"error": "Invalid kpi_metric_id"}, 400)

        if period_type:
            query = query.filter(KpiRecord.period_type == period_type)
        if start_date:
            query = query.filter(KpiRecord.record_date >= start_date)
        if end_date:
            query = query.filter(KpiRecord.record_date <= end_date)

        rows = query.order_by(KpiRecord.record_date.desc()).limit(200).all()

        data = [
            {
                "id": str(record.id),
                "kpi_code": metric.code,
                "kpi_name": metric.name,
                "record_date": record.record_date.isoformat(),
                "period_type": record.period_type,
                "value": float(record.value),
                "target_value": float(record.target_value) if record.target_value else None,
                "variance": float(record.variance) if record.variance else None,
                "variance_percentage": float(record.variance_percentage) if record.variance_percentage else None,
            }
            for record, metric in rows
        ]

        return _json_response(data)


def create_kpi_record(request: Request) -> Response:
    """POST /api/crm/kpi-records - Tạo ghi nhận KPI."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["kpi_metric_id", "record_date", "period_type", "value"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        try:
            kpi_id = uuid.UUID(data["kpi_metric_id"])
            metric = db.query(KpiMetric).filter(KpiMetric.id == kpi_id).first()
            if not metric:
                return _json_response({"error": "KPI metric không tồn tại"}, 404)
        except ValueError:
            return _json_response({"error": "Invalid kpi_metric_id"}, 400)

        record_date = _parse_date(data["record_date"])
        value = float(data["value"])
        target_value = float(data["target_value"]) if data.get("target_value") else metric.target_value

        variance = None
        variance_percentage = None
        if target_value:
            variance = value - target_value
            variance_percentage = (variance / target_value) * 100 if target_value != 0 else None

        record = KpiRecord(
            kpi_metric_id=kpi_id,
            record_date=record_date,
            period_type=data["period_type"],
            value=value,
            target_value=target_value,
            variance=variance,
            variance_percentage=variance_percentage,
            note=data.get("note"),
        )
        db.add(record)
        db.flush()

        # Cập nhật current_value của metric
        metric.current_value = value

        return _json_response({
            "id": str(record.id),
            "kpi_metric_id": str(record.kpi_metric_id),
            "value": float(record.value),
        }, 201)

