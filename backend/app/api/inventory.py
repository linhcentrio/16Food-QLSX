"""
API đơn giản cho module Kho:
- Tạo phiếu nhập/xuất kho.
- Tính tồn kho realtime từ bảng inventorysnapshot.

Logic chi tiết NXT, kiểm kê sẽ được mở rộng thêm sau.
"""

from __future__ import annotations

import json
from datetime import date

from robyn import Request, Response

from ..core.db import get_session
from ..models.entities import (
    StockDocument,
    StockDocumentLine,
    InventorySnapshot,
    Warehouse,
    Product,
    StockTaking,
    StockTakingLine,
)
from ..services.qr_service import (
    generate_qr_code_base64,
    generate_qr_code_data_url,
    create_stock_document_qr_data,
)
from ..services.inventory_service import (
    create_stock_document_from_production_order,
    create_stock_document_from_production_date,
    query_inventory_with_filters,
)


def json_response(data: object, status_code: int = 200) -> Response:
    return Response(
        status_code=status_code,
        headers={"Content-Type": "application/json"},
        body=json.dumps(data, default=str),
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def get_inventory() -> Response:
    """Tồn kho realtime đơn giản theo từng kho + sản phẩm."""

    with get_session() as db:
        rows = (
            db.query(InventorySnapshot, Product, Warehouse)
            .join(Product, InventorySnapshot.product_id == Product.id)
            .join(Warehouse, InventorySnapshot.warehouse_id == Warehouse.id)
            .order_by(Product.code, Warehouse.code)
            .all()
        )
        data = [
            {
                "product_code": p.code,
                "product_name": p.name,
                "warehouse_code": w.code,
                "warehouse_name": w.name,
                "qty": float(inv.current_qty),
            }
            for inv, p, w in rows
        ]
    return json_response(data)


def query_inventory(request: Request) -> Response:  # type: ignore[override]
    """
    GET /api/inventory/query
    
    Query inventory với nhiều filters.
    
    Query params:
    - product_group: Loại sản phẩm (NVL, BTP, TP, Phu_lieu)
    - product_code: Mã sản phẩm
    - product_name: Tên sản phẩm (partial match)
    - warehouse_code: Mã kho
    - warehouse_type: Loại kho (TP, BTP, NVL)
    - min_qty: Số lượng tối thiểu
    - max_qty: Số lượng tối đa
    """
    params = request.query_params
    
    product_group = params.get("product_group")
    product_code = params.get("product_code")
    product_name = params.get("product_name")
    warehouse_code = params.get("warehouse_code")
    warehouse_type = params.get("warehouse_type")
    
    min_qty = None
    max_qty = None
    
    if "min_qty" in params:
        try:
            min_qty = float(params["min_qty"])
        except (ValueError, TypeError):
            return json_response({"error": "min_qty phải là số hợp lệ"}, 400)
    
    if "max_qty" in params:
        try:
            max_qty = float(params["max_qty"])
        except (ValueError, TypeError):
            return json_response({"error": "max_qty phải là số hợp lệ"}, 400)
    
    try:
        with get_session() as db:
            results = query_inventory_with_filters(
                db,
                product_group=product_group,
                product_code=product_code,
                product_name=product_name,
                warehouse_code=warehouse_code,
                warehouse_type=warehouse_type,
                min_qty=min_qty,
                max_qty=max_qty,
            )
            return json_response({
                "count": len(results),
                "items": results,
            })
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi query inventory: {str(e)}"}, 500
        )


def create_stock_document(request: Request) -> Response:  # type: ignore[override]
    """Tạo phiếu nhập/xuất kho đơn giản từ JSON body.

    Payload gợi ý:
    {
      "doc_type": "N" | "X",
      "warehouse_code": "NVL",
      "posting_date": "2025-01-01",
      "lines": [
        {"product_code": "NVL001", "uom": "kg", "quantity": 10},
        ...
      ]
    }

    Ràng buộc:
    - Nếu là phiếu xuất (X): không cho phép làm cho tồn kho < 0.
    """

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return json_response({"error": "Body không phải JSON hợp lệ"}, 400)

    required_fields = ["doc_type", "warehouse_code", "posting_date", "lines"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )

    if data["doc_type"] not in {"N", "X"}:
        return json_response({"error": "doc_type phải là 'N' hoặc 'X'"}, 400)

    if not isinstance(data["lines"], list) or not data["lines"]:
        return json_response({"error": "Phiếu phải có ít nhất 1 dòng"}, 400)

    with get_session() as db:
        wh = (
            db.query(Warehouse)
            .filter(Warehouse.code == data["warehouse_code"])
            .first()
        )
        if not wh:
            return json_response({"error": "Kho không tồn tại"}, 400)

        posting_date = _parse_date(data["posting_date"])

        lines_entities: list[StockDocumentLine] = []

        for line in data["lines"]:
            product_code = line.get("product_code")
            quantity = float(line.get("quantity") or 0)
            uom = line.get("uom") or ""
            if not product_code or quantity <= 0 or not uom:
                continue

            product = (
                db.query(Product).filter(Product.code == product_code).first()
            )
            if not product:
                return json_response(
                    {"error": f"Sản phẩm không tồn tại: {product_code}"}, 400
                )

            signed_qty = quantity if data["doc_type"] == "N" else -quantity

            # Check tồn kho khi xuất
            if signed_qty < 0:
                inv = (
                    db.query(InventorySnapshot)
                    .filter(
                        InventorySnapshot.product_id == product.id,
                        InventorySnapshot.warehouse_id == wh.id,
                    )
                    .first()
                )
                current_qty = float(inv.current_qty if inv else 0)
                if current_qty + signed_qty < 0:
                    return json_response(
                        {
                            "error": "Xuất kho sẽ làm tồn âm",
                            "product_code": product_code,
                            "current_qty": current_qty,
                            "request_qty": quantity,
                        },
                        400,
                    )

            lines_entities.append(
                StockDocumentLine(
                    product_id=product.id,
                    product_name=product.name,
                    uom=uom,
                    quantity=quantity,
                    signed_qty=signed_qty,
                )
            )

        if not lines_entities:
            return json_response({"error": "Không có dòng hợp lệ"}, 400)

        # Sinh mã phiếu đơn giản PN/PX + ngày + số thứ tự
        prefix = "PN" if data["doc_type"] == "N" else "PX"
        count_today = (
            db.query(StockDocument)
            .filter(
                StockDocument.posting_date == posting_date,
                StockDocument.doc_type == data["doc_type"],
            )
            .count()
        )
        code = f"{prefix}{posting_date.strftime('%Y%m%d')}-{count_today + 1:03d}"

        doc = StockDocument(
            code=code,
            posting_date=posting_date,
            doc_type=data["doc_type"],
            warehouse_id=wh.id,
            storekeeper=data.get("storekeeper"),
            partner_name=data.get("partner_name"),
            description=data.get("description"),
        )
        db.add(doc)
        db.flush()

        # Cập nhật InventorySnapshot
        for line in lines_entities:
            line.document_id = doc.id
            db.add(line)

            inv = (
                db.query(InventorySnapshot)
                .filter(
                    InventorySnapshot.product_id == line.product_id,
                    InventorySnapshot.warehouse_id == wh.id,
                )
                .first()
            )
            if not inv:
                inv = InventorySnapshot(
                    product_id=line.product_id,
                    warehouse_id=wh.id,
                    total_in=0,
                    total_out=0,
                    current_qty=0,
                )
                db.add(inv)
                db.flush()

            if doc.doc_type == "N":
                inv.total_in = (inv.total_in or 0) + line.quantity
            else:
                inv.total_out = (inv.total_out or 0) + abs(line.quantity)

            inv.current_qty = (inv.total_in or 0) - (inv.total_out or 0)

        return json_response({"code": doc.code}, 201)


# Stock Taking APIs
def list_stock_taking(request: Request) -> Response:  # type: ignore[override]
    """
    GET /api/inventory/stock-taking
    
    Danh sách phiếu kiểm kê.
    
    Query params:
    - warehouse_code: Lọc theo kho
    - status: Lọc theo trạng thái (draft, locked)
    - start_date: Ngày bắt đầu
    - end_date: Ngày kết thúc
    """
    with get_session() as db:
        query = db.query(StockTaking, Warehouse)
        
        if "warehouse_code" in request.query_params:
            warehouse_code = request.query_params["warehouse_code"]
            query = query.join(Warehouse).filter(Warehouse.code == warehouse_code)
        else:
            query = query.join(Warehouse)
        
        if "status" in request.query_params:
            query = query.filter(StockTaking.status == request.query_params["status"])
        
        if "start_date" in request.query_params:
            try:
                start_date = _parse_date(request.query_params["start_date"])
                query = query.filter(StockTaking.stocktaking_date >= start_date)
            except ValueError:
                pass
        
        if "end_date" in request.query_params:
            try:
                end_date = _parse_date(request.query_params["end_date"])
                query = query.filter(StockTaking.stocktaking_date <= end_date)
            except ValueError:
                pass
        
        rows = query.order_by(StockTaking.stocktaking_date.desc()).limit(100).all()
        
        data = [
            {
                "id": str(st.id),
                "code": st.code,
                "warehouse_code": w.code,
                "warehouse_name": w.name,
                "stocktaking_date": st.stocktaking_date.isoformat(),
                "status": st.status,
            }
            for st, w in rows
        ]
        
        return json_response(data)


def get_stock_taking_detail(stocktaking_id: str, request: Request) -> Response:  # type: ignore[override]
    """
    GET /api/inventory/stock-taking/{id}
    
    Chi tiết phiếu kiểm kê.
    """
    try:
        import uuid
        st_id = uuid.UUID(stocktaking_id)
    except ValueError:
        return json_response({"error": "ID phiếu kiểm kê không hợp lệ"}, 400)
    
    with get_session() as db:
        st = (
            db.query(StockTaking, Warehouse)
            .join(Warehouse)
            .filter(StockTaking.id == st_id)
            .first()
        )
        
        if not st:
            return json_response({"error": "Phiếu kiểm kê không tồn tại"}, 404)
        
        stocktaking, warehouse = st
        
        lines = (
            db.query(StockTakingLine, Product)
            .join(Product)
            .filter(StockTakingLine.stocktaking_id == st_id)
            .all()
        )
        
        return json_response({
            "id": str(stocktaking.id),
            "code": stocktaking.code,
            "warehouse_id": str(warehouse.id),
            "warehouse_code": warehouse.code,
            "warehouse_name": warehouse.name,
            "stocktaking_date": stocktaking.stocktaking_date.isoformat(),
            "status": stocktaking.status,
            "lines": [
                {
                    "id": str(line.id),
                    "product_code": product.code,
                    "product_name": product.name,
                    "book_qty": float(line.book_qty),
                    "counted_qty": float(line.counted_qty),
                    "difference_qty": float(line.difference_qty),
                    "adjustment_created": line.adjustment_created,
                }
                for line, product in lines
            ],
        })


def create_stock_taking(request: Request) -> Response:  # type: ignore[override]
    """
    POST /api/inventory/stock-taking
    
    Tạo phiếu kiểm kê mới.
    
    Payload:
    {
      "warehouse_code": "NVL",
      "stocktaking_date": "2025-01-01",
      "lines": [
        {
          "product_code": "NVL001",
          "counted_qty": 100
        }
      ]
    }
    """
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return json_response({"error": "Body không phải JSON hợp lệ"}, 400)
    
    required_fields = ["warehouse_code", "stocktaking_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )
    
    with get_session() as db:
        warehouse = (
            db.query(Warehouse)
            .filter(Warehouse.code == data["warehouse_code"])
            .first()
        )
        if not warehouse:
            return json_response({"error": "Kho không tồn tại"}, 400)
        
        stocktaking_date = _parse_date(data["stocktaking_date"])
        
        # Sinh mã phiếu kiểm kê: KK-yyyyMMdd-xxx
        count_today = (
            db.query(StockTaking)
            .filter(StockTaking.stocktaking_date == stocktaking_date)
            .count()
        )
        code = f"KK{stocktaking_date.strftime('%Y%m%d')}-{count_today + 1:03d}"
        
        stocktaking = StockTaking(
            code=code,
            warehouse_id=warehouse.id,
            stocktaking_date=stocktaking_date,
            status="draft",
        )
        db.add(stocktaking)
        db.flush()
        
        # Tạo các dòng kiểm kê
        lines_data = data.get("lines", [])
        for line_data in lines_data:
            product_code = line_data.get("product_code")
            counted_qty = float(line_data.get("counted_qty", 0))
            
            if not product_code:
                continue
            
            product = (
                db.query(Product).filter(Product.code == product_code).first()
            )
            if not product:
                continue
            
            # Lấy tồn sổ sách từ InventorySnapshot
            inv = (
                db.query(InventorySnapshot)
                .filter(
                    InventorySnapshot.product_id == product.id,
                    InventorySnapshot.warehouse_id == warehouse.id,
                )
                .first()
            )
            book_qty = float(inv.current_qty) if inv else 0.0
            difference_qty = counted_qty - book_qty
            
            line = StockTakingLine(
                stocktaking_id=stocktaking.id,
                product_id=product.id,
                book_qty=book_qty,
                counted_qty=counted_qty,
                difference_qty=difference_qty,
                adjustment_created=False,
            )
            db.add(line)
        
        return json_response({
            "id": str(stocktaking.id),
            "code": stocktaking.code,
        }, 201)


def update_stock_taking(stocktaking_id: str, request: Request) -> Response:  # type: ignore[override]
    """
    PUT /api/inventory/stock-taking/{id}
    
    Cập nhật phiếu kiểm kê.
    
    Payload:
    {
      "stocktaking_date": "2025-01-01",  // optional
      "lines": [
        {
          "product_code": "NVL001",
          "counted_qty": 100
        }
      ]
    }
    """
    try:
        import uuid
        st_id = uuid.UUID(stocktaking_id)
    except ValueError:
        return json_response({"error": "ID phiếu kiểm kê không hợp lệ"}, 400)
    
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return json_response({"error": "Body không phải JSON hợp lệ"}, 400)
    
    with get_session() as db:
        stocktaking = db.query(StockTaking).filter(StockTaking.id == st_id).first()
        if not stocktaking:
            return json_response({"error": "Phiếu kiểm kê không tồn tại"}, 404)
        
        if stocktaking.status == "locked":
            return json_response(
                {"error": "Không thể cập nhật phiếu kiểm kê đã khóa"}, 400
            )
        
        if "stocktaking_date" in data:
            stocktaking.stocktaking_date = _parse_date(data["stocktaking_date"])
        
        # Cập nhật/xóa/thêm dòng
        if "lines" in data:
            # Xóa các dòng cũ
            db.query(StockTakingLine).filter(
                StockTakingLine.stocktaking_id == st_id
            ).delete()
            
            warehouse_id = stocktaking.warehouse_id
            for line_data in data["lines"]:
                product_code = line_data.get("product_code")
                counted_qty = float(line_data.get("counted_qty", 0))
                
                if not product_code:
                    continue
                
                product = (
                    db.query(Product).filter(Product.code == product_code).first()
                )
                if not product:
                    continue
                
                # Lấy tồn sổ sách
                inv = (
                    db.query(InventorySnapshot)
                    .filter(
                        InventorySnapshot.product_id == product.id,
                        InventorySnapshot.warehouse_id == warehouse_id,
                    )
                    .first()
                )
                book_qty = float(inv.current_qty) if inv else 0.0
                difference_qty = counted_qty - book_qty
                
                line = StockTakingLine(
                    stocktaking_id=st_id,
                    product_id=product.id,
                    book_qty=book_qty,
                    counted_qty=counted_qty,
                    difference_qty=difference_qty,
                    adjustment_created=False,
                )
                db.add(line)
        
        return json_response({
            "id": str(stocktaking.id),
            "code": stocktaking.code,
        })


def lock_stock_taking(stocktaking_id: str, request: Request) -> Response:  # type: ignore[override]
    """
    POST /api/inventory/stock-taking/{id}/lock
    
    Khóa phiếu kiểm kê và tự động tạo phiếu điều chỉnh.
    """
    try:
        import uuid
        st_id = uuid.UUID(stocktaking_id)
    except ValueError:
        return json_response({"error": "ID phiếu kiểm kê không hợp lệ"}, 400)
    
    with get_session() as db:
        stocktaking = db.query(StockTaking).filter(StockTaking.id == st_id).first()
        if not stocktaking:
            return json_response({"error": "Phiếu kiểm kê không tồn tại"}, 404)
        
        if stocktaking.status == "locked":
            return json_response(
                {"error": "Phiếu kiểm kê đã được khóa"}, 400
            )
        
        # Lấy các dòng kiểm kê có chênh lệch
        lines = (
            db.query(StockTakingLine)
            .filter(
                StockTakingLine.stocktaking_id == st_id,
                StockTakingLine.difference_qty != 0,
                StockTakingLine.adjustment_created == False,
            )
            .all()
        )
        
        if not lines:
            stocktaking.status = "locked"
            return json_response({
                "id": str(stocktaking.id),
                "code": stocktaking.code,
                "status": "locked",
                "adjustments_created": 0,
            })
        
        # Tạo phiếu điều chỉnh
        adjustment_lines: list[StockDocumentLine] = []
        for line in lines:
            if abs(float(line.difference_qty)) < 0.001:
                continue
            
            product = db.query(Product).filter(Product.id == line.product_id).first()
            if not product:
                continue
            
            # Nếu chênh lệch dương: tạo phiếu nhập, nếu âm: tạo phiếu xuất
            doc_type = "N" if line.difference_qty > 0 else "X"
            quantity = abs(float(line.difference_qty))
            signed_qty = quantity if doc_type == "N" else -quantity
            
            adjustment_lines.append({
                "product_id": line.product_id,
                "product_name": product.name,
                "quantity": quantity,
                "signed_qty": signed_qty,
                "uom": product.main_uom,
            })
            
            line.adjustment_created = True
        
        if adjustment_lines:
            # Nhóm theo doc_type và tạo phiếu
            by_doc_type: dict[str, list] = {}
            for line in adjustment_lines:
                doc_type = "N" if line["signed_qty"] > 0 else "X"
                if doc_type not in by_doc_type:
                    by_doc_type[doc_type] = []
                by_doc_type[doc_type].append(line)
            
            created_docs = []
            for doc_type, lines_list in by_doc_type.items():
                # Sinh mã phiếu điều chỉnh
                prefix = "PN" if doc_type == "N" else "PX"
                count_today = (
                    db.query(StockDocument)
                    .filter(
                        StockDocument.posting_date == stocktaking.stocktaking_date,
                        StockDocument.doc_type == doc_type,
                    )
                    .count()
                )
                code = f"{prefix}{stocktaking.stocktaking_date.strftime('%Y%m%d')}-{count_today + 1:03d}"
                
                doc = StockDocument(
                    code=code,
                    posting_date=stocktaking.stocktaking_date,
                    doc_type=doc_type,
                    warehouse_id=stocktaking.warehouse_id,
                    description=f"Điều chỉnh từ kiểm kê {stocktaking.code}",
                )
                db.add(doc)
                db.flush()
                
                # Tạo dòng phiếu và cập nhật tồn kho
                for line_data in lines_list:
                    doc_line = StockDocumentLine(
                        document_id=doc.id,
                        product_id=line_data["product_id"],
                        product_name=line_data["product_name"],
                        uom=line_data["uom"],
                        quantity=line_data["quantity"],
                        signed_qty=line_data["signed_qty"],
                    )
                    db.add(doc_line)
                    
                    # Cập nhật InventorySnapshot
                    inv = (
                        db.query(InventorySnapshot)
                        .filter(
                            InventorySnapshot.product_id == line_data["product_id"],
                            InventorySnapshot.warehouse_id == stocktaking.warehouse_id,
                        )
                        .first()
                    )
                    if not inv:
                        inv = InventorySnapshot(
                            product_id=line_data["product_id"],
                            warehouse_id=stocktaking.warehouse_id,
                            total_in=0,
                            total_out=0,
                            current_qty=0,
                        )
                        db.add(inv)
                        db.flush()
                    
                    if doc_type == "N":
                        inv.total_in = (inv.total_in or 0) + line_data["quantity"]
                    else:
                        inv.total_out = (inv.total_out or 0) + line_data["quantity"]
                    
                    inv.current_qty = (inv.total_in or 0) - (inv.total_out or 0)
                
                created_docs.append(code)
        
        stocktaking.status = "locked"
        db.commit()
        
        return json_response({
            "id": str(stocktaking.id),
            "code": stocktaking.code,
            "status": "locked",
            "adjustments_created": len(created_docs),
            "adjustment_documents": created_docs,
        })


def get_stock_taking_adjustments(stocktaking_id: str, request: Request) -> Response:  # type: ignore[override]
    """
    GET /api/inventory/stock-taking/{id}/adjustments
    
    Xem các phiếu điều chỉnh đã tạo từ kiểm kê.
    """
    try:
        import uuid
        st_id = uuid.UUID(stocktaking_id)
    except ValueError:
        return json_response({"error": "ID phiếu kiểm kê không hợp lệ"}, 400)
    
    with get_session() as db:
        stocktaking = db.query(StockTaking).filter(StockTaking.id == st_id).first()
        if not stocktaking:
            return json_response({"error": "Phiếu kiểm kê không tồn tại"}, 404)
        
        # Tìm các phiếu điều chỉnh từ description
        adjustment_docs = (
            db.query(StockDocument)
            .filter(
                StockDocument.warehouse_id == stocktaking.warehouse_id,
                StockDocument.posting_date == stocktaking.stocktaking_date,
                StockDocument.description.like(f"%{stocktaking.code}%"),
            )
            .all()
        )
        
        data = []
        for doc in adjustment_docs:
            lines = (
                db.query(StockDocumentLine, Product)
                .join(Product)
                .filter(StockDocumentLine.document_id == doc.id)
                .all()
            )
            
            data.append({
                "code": doc.code,
                "doc_type": doc.doc_type,
                "posting_date": doc.posting_date.isoformat(),
                "description": doc.description,
                "lines": [
                    {
                        "product_code": product.code,
                        "product_name": product.name,
                        "quantity": float(line.quantity),
                        "uom": line.uom,
                    }
                    for line, product in lines
                ],
            })
        
        return json_response({
            "stocktaking_code": stocktaking.code,
            "adjustments": data,
        })


def get_stock_document_qr_code(document_id: str, request: Request) -> Response:  # type: ignore[override]
    """
    GET /api/inventory/documents/{id}/qr-code
    
    Lấy QR code của phiếu kho.
    
    Query params:
    - format: "base64" hoặc "data_url" (default: "data_url")
    - size: Kích thước QR code (1-40, default: 10)
    """
    try:
        import uuid
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        return json_response({"error": "ID phiếu kho không hợp lệ"}, 400)
    
    format_type = request.query_params.get("format", "data_url")
    size = int(request.query_params.get("size", "10"))
    
    try:
        with get_session() as db:
            doc = (
                db.query(StockDocument, Warehouse)
                .join(Warehouse)
                .filter(StockDocument.id == doc_uuid)
                .first()
            )
            if not doc:
                return json_response({"error": "Phiếu kho không tồn tại"}, 404)
            
            document, warehouse = doc
            
            qr_data = create_stock_document_qr_data(
                document_code=document.code,
                doc_type=document.doc_type,
                posting_date=document.posting_date.isoformat(),
                warehouse_code=warehouse.code,
            )
            
            if format_type == "base64":
                qr_code = generate_qr_code_base64(qr_data, size=size)
                return json_response({
                    "qr_code": qr_code,
                    "format": "base64",
                })
            else:
                qr_code = generate_qr_code_data_url(qr_data, size=size)
                return json_response({
                    "qr_code": qr_code,
                    "format": "data_url",
                })
    except ImportError as e:
        return json_response(
            {"error": f"QR code library chưa được cài đặt: {str(e)}"}, 500
        )
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tạo QR code: {str(e)}"}, 500
        )


def create_stock_document_from_production_order_api(
    order_id: str, request: Request
) -> Response:  # type: ignore[override]
    """
    POST /api/inventory/documents/from-production-order/:order_id
    
    Tạo phiếu nhập kho từ LSX hoàn thành.
    """
    try:
        import uuid
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        return json_response({"error": "ID LSX không hợp lệ"}, 400)
    
    try:
        with get_session() as db:
            doc = create_stock_document_from_production_order(db, order_uuid)
            db.commit()
            
            return json_response({
                "code": doc.code,
                "id": str(doc.id),
                "warehouse_id": str(doc.warehouse_id),
                "posting_date": doc.posting_date.isoformat(),
            }, 201)
    except ValueError as e:
        return json_response({"error": str(e)}, 400)
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tạo phiếu nhập kho: {str(e)}"}, 500
        )


def create_stock_document_from_production_date_api(
    request: Request
) -> Response:  # type: ignore[override]
    """
    POST /api/inventory/documents/from-production-date
    
    Tạo phiếu xuất kho từ ngày sản xuất.
    
    Payload:
    {
      "production_date": "2025-01-15",
      "warehouse_code": "WH-NVL_01"
    }
    """
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return json_response({"error": "Body không phải JSON hợp lệ"}, 400)
    
    required_fields = ["production_date", "warehouse_code"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return json_response(
            {"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}, 400
        )
    
    try:
        production_date = _parse_date(data["production_date"])
        warehouse_code = data["warehouse_code"]
    except ValueError as e:
        return json_response({"error": f"Ngày không hợp lệ: {str(e)}"}, 400)
    
    try:
        with get_session() as db:
            doc = create_stock_document_from_production_date(
                db, production_date, warehouse_code
            )
            db.commit()
            
            return json_response({
                "code": doc.code,
                "id": str(doc.id),
                "warehouse_id": str(doc.warehouse_id),
                "posting_date": doc.posting_date.isoformat(),
                "production_date": production_date.isoformat(),
            }, 201)
    except ValueError as e:
        return json_response({"error": str(e)}, 400)
    except Exception as e:
        return json_response(
            {"error": f"Lỗi khi tạo phiếu xuất kho: {str(e)}"}, 500
        )


