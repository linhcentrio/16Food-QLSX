"""
API cho Module Chất Lượng (Quality).
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime

from robyn import Request, Response

from ..core.db import get_session
from ..core.error_handler import json_response as _json_response, ValidationError, NotFoundError
from ..models.quality import (
    NonConformity,
    NonConformityAction,
    IsoDocument,
    IsoDocumentVersion,
)
from ..models.entities import ProductionOrder, Product


def _parse_date(value: str) -> date:
    """Parse date từ string."""
    return date.fromisoformat(value)


# Non-Conformity APIs
def list_non_conformities(request: Request) -> Response:
    """GET /api/quality/non-conformities - Danh sách sự không phù hợp."""
    status = request.query_params.get("status")
    category = request.query_params.get("category")
    severity = request.query_params.get("severity")
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
        query = db.query(NonConformity)

        if status:
            query = query.filter(NonConformity.status == status)
        if category:
            query = query.filter(NonConformity.category == category)
        if severity:
            query = query.filter(NonConformity.severity == severity)
        if start_date:
            query = query.filter(NonConformity.detected_date >= start_date)
        if end_date:
            query = query.filter(NonConformity.detected_date <= end_date)

        non_conformities = query.order_by(NonConformity.detected_date.desc()).limit(100).all()

        data = []
        for nc in non_conformities:
            actions = (
                db.query(NonConformityAction)
                .filter(NonConformityAction.non_conformity_id == nc.id)
                .all()
            )

            data.append({
                "id": str(nc.id),
                "code": nc.code,
                "detected_date": nc.detected_date.isoformat(),
                "detected_by": nc.detected_by,
                "category": nc.category,
                "severity": nc.severity,
                "description": nc.description,
                "status": nc.status,
                "actions_count": len(actions),
            })

        return _json_response(data)


def create_non_conformity(request: Request) -> Response:
    """POST /api/quality/non-conformities - Tạo sự không phù hợp mới."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["detected_date", "category", "severity", "description"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        detected_date = _parse_date(data["detected_date"])

        count_today = (
            db.query(NonConformity)
            .filter(NonConformity.detected_date == detected_date)
            .count()
        )
        code = f"KPH{detected_date.strftime('%Y%m%d')}-{count_today + 1:03d}"

        production_order_id = None
        if data.get("production_order_id"):
            try:
                production_order_id = uuid.UUID(data["production_order_id"])
            except ValueError:
                return _json_response({"error": "Invalid production_order_id"}, 400)

        product_id = None
        if data.get("product_id"):
            try:
                product_id = uuid.UUID(data["product_id"])
            except ValueError:
                return _json_response({"error": "Invalid product_id"}, 400)

        non_conformity = NonConformity(
            code=code,
            detected_date=detected_date,
            detected_by=data.get("detected_by"),
            production_order_id=production_order_id,
            product_id=product_id,
            category=data["category"],
            severity=data["severity"],
            description=data["description"],
            root_cause=data.get("root_cause"),
            status=data.get("status", "detected"),
            note=data.get("note"),
        )
        db.add(non_conformity)
        db.flush()

        return _json_response({
            "id": str(non_conformity.id),
            "code": non_conformity.code,
        }, 201)


def add_non_conformity_action(non_conformity_id: str, request: Request) -> Response:
    """POST /api/quality/non-conformities/:id/actions - Thêm hành động khắc phục."""
    try:
        nc_id = uuid.UUID(non_conformity_id)
    except ValueError:
        return _json_response({"error": "Invalid non_conformity_id"}, 400)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["action_type", "description"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        non_conformity = (
            db.query(NonConformity).filter(NonConformity.id == nc_id).first()
        )
        if not non_conformity:
            return _json_response({"error": "Sự không phù hợp không tồn tại"}, 404)

        planned_date = None
        if data.get("planned_date"):
            try:
                planned_date = _parse_date(data["planned_date"])
            except ValueError:
                return _json_response({"error": "Invalid planned_date format"}, 400)

        completed_date = None
        if data.get("completed_date"):
            try:
                completed_date = _parse_date(data["completed_date"])
            except ValueError:
                return _json_response({"error": "Invalid completed_date format"}, 400)

        action = NonConformityAction(
            non_conformity_id=nc_id,
            action_type=data["action_type"],
            description=data["description"],
            responsible_person=data.get("responsible_person"),
            planned_date=planned_date,
            completed_date=completed_date,
            status=data.get("status", "planned"),
            effectiveness=data.get("effectiveness"),
            note=data.get("note"),
        )
        db.add(action)
        db.flush()

        return _json_response({
            "id": str(action.id),
            "action_type": action.action_type,
            "status": action.status,
        }, 201)


# ISO Document APIs
def list_iso_documents(request: Request) -> Response:
    """GET /api/quality/iso-documents - Danh sách tài liệu ISO."""
    document_type = request.query_params.get("document_type")
    iso_standard = request.query_params.get("iso_standard")
    status = request.query_params.get("status")

    with get_session() as db:
        query = db.query(IsoDocument)

        if document_type:
            query = query.filter(IsoDocument.document_type == document_type)
        if iso_standard:
            query = query.filter(IsoDocument.iso_standard == iso_standard)
        if status:
            query = query.filter(IsoDocument.status == status)

        documents = query.order_by(IsoDocument.code).all()

        data = []
        for doc in documents:
            versions = (
                db.query(IsoDocumentVersion)
                .filter(IsoDocumentVersion.document_id == doc.id)
                .order_by(IsoDocumentVersion.effective_date.desc())
                .all()
            )

            data.append({
                "id": str(doc.id),
                "code": doc.code,
                "title": doc.title,
                "document_type": doc.document_type,
                "iso_standard": doc.iso_standard,
                "version": doc.version,
                "effective_date": doc.effective_date.isoformat(),
                "expiry_date": doc.expiry_date.isoformat() if doc.expiry_date else None,
                "status": doc.status,
                "versions_count": len(versions),
            })

        return _json_response(data)


def create_iso_document(request: Request) -> Response:
    """POST /api/quality/iso-documents - Tạo tài liệu ISO mới."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["code", "title", "document_type", "version", "effective_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        existing = (
            db.query(IsoDocument).filter(IsoDocument.code == data["code"]).first()
        )
        if existing:
            return _json_response({"error": "Mã tài liệu đã tồn tại"}, 400)

        effective_date = _parse_date(data["effective_date"])

        expiry_date = None
        if data.get("expiry_date"):
            try:
                expiry_date = _parse_date(data["expiry_date"])
            except ValueError:
                return _json_response({"error": "Invalid expiry_date format"}, 400)

        approved_date = None
        if data.get("approved_date"):
            try:
                approved_date = _parse_date(data["approved_date"])
            except ValueError:
                return _json_response({"error": "Invalid approved_date format"}, 400)

        document = IsoDocument(
            code=data["code"],
            title=data["title"],
            document_type=data["document_type"],
            iso_standard=data.get("iso_standard"),
            version=data["version"],
            effective_date=effective_date,
            expiry_date=expiry_date,
            status=data.get("status", "draft"),
            approved_by=data.get("approved_by"),
            approved_date=approved_date,
            file_url=data.get("file_url"),
            description=data.get("description"),
        )
        db.add(document)
        db.flush()

        # Tạo version đầu tiên
        version = IsoDocumentVersion(
            document_id=document.id,
            version=data["version"],
            effective_date=effective_date,
            file_url=data.get("file_url"),
            change_description=data.get("change_description", "Version ban đầu"),
            created_by=data.get("created_by"),
        )
        db.add(version)

        return _json_response({
            "id": str(document.id),
            "code": document.code,
            "title": document.title,
        }, 201)


def create_iso_document_version(document_id: str, request: Request) -> Response:
    """POST /api/quality/iso-documents/:id/versions - Tạo phiên bản mới của tài liệu ISO."""
    try:
        doc_id = uuid.UUID(document_id)
    except ValueError:
        return _json_response({"error": "Invalid document_id"}, 400)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["version", "effective_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return _json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    with get_session() as db:
        document = db.query(IsoDocument).filter(IsoDocument.id == doc_id).first()
        if not document:
            return _json_response({"error": "Tài liệu ISO không tồn tại"}, 404)

        effective_date = _parse_date(data["effective_date"])

        version = IsoDocumentVersion(
            document_id=doc_id,
            version=data["version"],
            effective_date=effective_date,
            file_url=data.get("file_url"),
            change_description=data.get("change_description"),
            created_by=data.get("created_by"),
        )
        db.add(version)

        # Cập nhật version và effective_date của document
        document.version = data["version"]
        document.effective_date = effective_date
        if data.get("file_url"):
            document.file_url = data["file_url"]

        return _json_response({
            "id": str(version.id),
            "version": version.version,
            "effective_date": version.effective_date.isoformat(),
        }, 201)

