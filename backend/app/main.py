"""
Điểm vào chính của backend Robyn.

- Khởi tạo Robyn app
- Cấu hình DB, routes cơ bản
- Render layout chính cho frontend (htmx sẽ dùng các endpoint khác nhau).
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from robyn import Robyn, Response, Request

from .core.config import settings
from .core.db import init_db, get_session
from .core.logging_config import setup_logging
from .core.auth import require_roles
from .api import catalog as catalog_api
from .api import orders as orders_api
from .api import production as production_api
from .api import inventory as inventory_api
from .api import bom as bom_api
from .api import inventory_analysis as inventory_analysis_api
from .api import hr as hr_api
from .api import equipment as equipment_api
from .api import procurement as procurement_api
from .api import production_extended as production_extended_api
from .api import logistics as logistics_api
from .api import quality as quality_api
from .api import crm_extended as crm_extended_api
from .api import hr_extended as hr_extended_api
from .api import reporting as reporting_api
from .core.error_handler import handle_errors
from .models.entities import (
    SalesOrder,
    Customer,
    ProductionPlanDay,
    ProductionOrder,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"
STATIC_DIR = BASE_DIR / "frontend" / "static"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

app = Robyn(__file__)


def render_template(template_name: str, **context: object) -> Response:
    """Helper render template Jinja2."""

    template = env.get_template(template_name)
    html = template.render(**context)
    return Response(status_code=200, headers={"Content-Type": "text/html"}, body=html)


@app.get("/")
async def index(request: Request) -> Response:  # type: ignore[override]
    """Trang dashboard chính (placeholder)."""

    return render_template(
        "index.html",
        app_name=settings.app_name,
    )


@app.get("/ui/orders")
async def ui_orders(request: Request) -> Response:  # type: ignore[override]
    """Trang danh sách đơn hàng (htmx target)."""

    return render_template("orders/list.html")


@app.get("/ui/orders/table")
async def ui_orders_table(request: Request) -> Response:  # type: ignore[override]
    """Fragment bảng đơn hàng, dùng cho htmx."""

    with get_session() as db:
        rows = (
            db.query(SalesOrder, Customer)
            .join(Customer, SalesOrder.customer_id == Customer.id)
            .order_by(SalesOrder.order_date.desc())
            .limit(100)
            .all()
        )

        orders = [
            {
                "code": so.code,
                "customer_name": cust.name,
                "order_date": so.order_date,
                "delivery_date": so.delivery_date,
                "status": {
                    "new": "Mới",
                    "in_production": "Đang SX",
                    "completed": "Hoàn thành",
                    "delivered": "Đã giao",
                }.get(so.status, so.status),
                "total_amount": float(so.total_amount or 0),
            }
            for so, cust in rows
        ]

    return render_template("orders/table.html", orders=orders)


@app.get("/ui/production")
async def ui_production(request: Request) -> Response:  # type: ignore[override]
    """Trang tổng quan QLSX (htmx target)."""

    return render_template("production/index.html")


@app.get("/api/production/daily-plan")
async def api_daily_plan(request: Request) -> Response:  # type: ignore[override]
    """API JSON: KHSX ngày (placeholder, hiện lấy theo hôm nay)."""

    return production_api.list_daily_plan()


@app.get("/api/production/orders")
async def api_recent_production_orders(request: Request) -> Response:  # type: ignore[override]
    """API JSON: LSX gần nhất."""

    return production_api.list_recent_production_orders()


@app.post("/api/production/orders/from-sales-orders")
async def api_create_production_orders_from_orders(request: Request) -> Response:  # type: ignore[override]
    """API: Tự động tạo LSX từ đơn hàng (UC-01)."""

    return production_api.create_production_orders_from_orders(request)


@app.get("/api/production/planning/material-requirement")
async def api_get_material_requirement_plan(request: Request) -> Response:  # type: ignore[override]
    """API: Lấy dự trù NVL từ tất cả LSX trong khoảng thời gian."""

    return production_api.get_material_requirement_plan(request)


@app.post("/api/production/planning/calculate-btp-demand")
async def api_calculate_btp_demand(request: Request) -> Response:  # type: ignore[override]
    """API: Tính nhu cầu BTP từ LSX sản phẩm."""

    return production_api.calculate_btp_demand(request)


@app.get("/api/production/planning/summary")
async def api_get_production_planning_summary(request: Request) -> Response:  # type: ignore[override]
    """API: Tổng hợp kế hoạch sản xuất."""

    return production_api.get_production_planning_summary_api(request)


@app.get("/api/production/pivot/bom-lsx")
async def api_get_pivot_bom_lsx(request: Request) -> Response:  # type: ignore[override]
    """API: Pivot BOM LSX theo ngày sản xuất."""

    return production_api.get_pivot_bom_lsx(request)


@app.get("/api/production/pivot/material-plan")
async def api_get_pivot_material_plan(request: Request) -> Response:  # type: ignore[override]
    """API: Pivot kế hoạch vật tư theo ngày sản xuất."""

    return production_api.get_pivot_material_plan(request)


@app.put("/api/production/orders/:order_id/lines/:line_id")
async def api_update_production_order_line(request: Request) -> Response:  # type: ignore[override]
    """API: Cập nhật ProductionOrderLine."""

    order_id = request.path_params.get("order_id", "")
    line_id = request.path_params.get("line_id", "")
    return production_api.update_production_order_line_api(order_id, line_id, request)


@app.put("/api/production/orders/:order_id/lines/bulk")
async def api_bulk_update_production_order_lines(request: Request) -> Response:  # type: ignore[override]
    """API: Cập nhật nhiều ProductionOrderLine cùng lúc."""

    order_id = request.path_params.get("order_id", "")
    return production_api.bulk_update_production_order_lines_api(order_id, request)


@app.post("/api/production/orders/manual")
async def api_create_manual_production_order(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo lệnh sản xuất thủ công."""

    return production_api.create_manual_production_order_api(request)


# BOM API routes
@app.get("/api/bom/products/:product_id")
async def api_get_product_bom(request: Request) -> Response:  # type: ignore[override]
    """API: Xem BOM của sản phẩm."""

    product_id = request.path_params.get("product_id", "")
    return bom_api.get_product_bom(product_id, request)


@app.post("/api/bom/products/:product_id/materials")
async def api_add_material_to_bom(request: Request) -> Response:  # type: ignore[override]
    """API: Thêm NVL vào BOM của sản phẩm."""

    product_id = request.path_params.get("product_id", "")
    return bom_api.add_material_to_bom(product_id, request)


@app.get("/api/bom/production-orders/:order_id/material-requirements")
async def api_get_material_requirements(request: Request) -> Response:  # type: ignore[override]
    """API: Tính toán nhu cầu NVL từ LSX."""

    order_id = request.path_params.get("order_id", "")
    return bom_api.get_material_requirements_for_production_order(order_id, request)


@app.get("/api/bom/products/:product_id/cost-calculation")
async def api_get_product_cost_calculation(request: Request) -> Response:  # type: ignore[override]
    """API: Tính giá vốn sản phẩm từ BOM."""

    product_id = request.path_params.get("product_id", "")
    return bom_api.get_product_cost_calculation(product_id, request)


@app.post("/api/bom/recalculate-costs/:material_id")
async def api_recalculate_costs(request: Request) -> Response:  # type: ignore[override]
    """API: Tự động tính lại giá vốn khi thay đổi giá vật tư."""

    material_id = request.path_params.get("material_id", "")
    return bom_api.recalculate_costs(material_id, request)


@app.get("/ui/inventory")
async def ui_inventory(request: Request) -> Response:  # type: ignore[override]
    """Trang tổng quan kho (htmx target)."""

    # Ví dụ RBAC: chỉ cho phép role warehouse, admin truy cập
    user = require_roles(request, ["warehouse", "admin"])
    if not user:
        return Response(status_code=403, body="Forbidden")

    return render_template("inventory/index.html")


@app.get("/api/inventory")
async def api_inventory(request: Request) -> Response:  # type: ignore[override]
    """API JSON: tồn kho realtime."""

    return inventory_api.get_inventory()


@app.get("/api/inventory/query")
async def api_query_inventory(request: Request) -> Response:  # type: ignore[override]
    """API: Query inventory với nhiều filters."""

    return inventory_api.query_inventory(request)


@app.post("/api/inventory/documents")
async def api_create_stock_document(request: Request) -> Response:  # type: ignore[override]
    """API JSON: tạo phiếu nhập/xuất kho."""

    return inventory_api.create_stock_document(request)


# Stock Taking API routes
@app.get("/api/inventory/stock-taking")
async def api_list_stock_taking(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách phiếu kiểm kê."""

    return inventory_api.list_stock_taking(request)


@app.post("/api/inventory/stock-taking")
async def api_create_stock_taking(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo phiếu kiểm kê mới."""

    return inventory_api.create_stock_taking(request)


@app.get("/api/inventory/stock-taking/:id")
async def api_get_stock_taking_detail(request: Request) -> Response:  # type: ignore[override]
    """API: Chi tiết phiếu kiểm kê."""

    stocktaking_id = request.path_params.get("id", "")
    return inventory_api.get_stock_taking_detail(stocktaking_id, request)


@app.put("/api/inventory/stock-taking/:id")
async def api_update_stock_taking(request: Request) -> Response:  # type: ignore[override]
    """API: Cập nhật phiếu kiểm kê."""

    stocktaking_id = request.path_params.get("id", "")
    return inventory_api.update_stock_taking(stocktaking_id, request)


@app.post("/api/inventory/stock-taking/:id/lock")
async def api_lock_stock_taking(request: Request) -> Response:  # type: ignore[override]
    """API: Khóa phiếu kiểm kê và tạo phiếu điều chỉnh."""

    stocktaking_id = request.path_params.get("id", "")
    return inventory_api.lock_stock_taking(stocktaking_id, request)


@app.get("/api/inventory/stock-taking/:id/adjustments")
async def api_get_stock_taking_adjustments(request: Request) -> Response:  # type: ignore[override]
    """API: Xem phiếu điều chỉnh đã tạo từ kiểm kê."""

    stocktaking_id = request.path_params.get("id", "")
    return inventory_api.get_stock_taking_adjustments(stocktaking_id, request)


@app.get("/api/production/orders/:id/qr-code")
async def api_get_production_order_qr_code(request: Request) -> Response:  # type: ignore[override]
    """API: Lấy QR code của LSX."""

    order_id = request.path_params.get("id", "")
    return production_api.get_production_order_qr_code(order_id, request)


@app.get("/api/inventory/documents/:id/qr-code")
async def api_get_stock_document_qr_code(request: Request) -> Response:  # type: ignore[override]
    """API: Lấy QR code của phiếu kho."""

    document_id = request.path_params.get("id", "")
    return inventory_api.get_stock_document_qr_code(document_id, request)


@app.post("/api/inventory/documents/from-production-order/:order_id")
async def api_create_stock_document_from_production_order(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo phiếu nhập kho từ LSX hoàn thành."""

    order_id = request.path_params.get("order_id", "")
    return inventory_api.create_stock_document_from_production_order_api(order_id, request)


@app.post("/api/inventory/documents/from-production-date")
async def api_create_stock_document_from_production_date(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo phiếu xuất kho từ ngày sản xuất."""

    return inventory_api.create_stock_document_from_production_date_api(request)


@app.get("/ui/crm")
async def ui_crm(request: Request) -> Response:  # type: ignore[override]
    """Trang CRM (htmx target)."""

    return render_template("crm/index.html")


@app.get("/ui/hr")
async def ui_hr(request: Request) -> Response:  # type: ignore[override]
    """Trang nhân sự (htmx target)."""

    return render_template("hr/index.html")


@app.get("/api/catalog/products")
async def api_list_products(request: Request) -> Response:  # type: ignore[override]
    """API: danh sách sản phẩm (sử dụng cho htmx/autocomplete sau này)."""

    return catalog_api.list_products()


@app.post("/api/catalog/products")
async def api_create_product(request: Request) -> Response:  # type: ignore[override]
    """API: tạo sản phẩm mới."""

    return catalog_api.create_product(request)


@app.get("/api/crm/customers")
async def api_list_customers(request: Request) -> Response:  # type: ignore[override]
    """API JSON: danh sách khách hàng."""

    return catalog_api.list_customers()


@app.post("/api/crm/customers")
async def api_create_customer(request: Request) -> Response:  # type: ignore[override]
    """API JSON: tạo khách hàng mới."""

    return catalog_api.create_customer(request)


@app.get("/api/crm/price-policies")
async def api_list_price_policies(request: Request) -> Response:  # type: ignore[override]
    """API JSON: danh sách chính sách giá."""

    return catalog_api.list_price_policies()


@app.post("/api/crm/price-policies")
async def api_create_price_policy(request: Request) -> Response:  # type: ignore[override]
    """API JSON: tạo chính sách giá mới."""

    return catalog_api.create_price_policy(request)


@app.put("/api/catalog/products/:product_id/price-policy")
async def api_update_price_policy(request: Request) -> Response:  # type: ignore[override]
    """API: Cập nhật hoặc tạo mới PricePolicy cho sản phẩm."""

    product_id = request.path_params.get("product_id", "")
    return catalog_api.update_price_policy(product_id, request)


@app.post("/api/catalog/products/price-policy/bulk-update")
async def api_bulk_update_price_policy(request: Request) -> Response:  # type: ignore[override]
    """API: Cập nhật nhiều PricePolicy cùng lúc."""

    return catalog_api.bulk_update_price_policy(request)


@app.get("/api/orders")
async def api_list_orders(request: Request) -> Response:  # type: ignore[override]
    """API JSON: danh sách đơn hàng."""

    return orders_api.list_orders()


@app.post("/api/orders")
async def api_create_order(request: Request) -> Response:  # type: ignore[override]
    """API JSON: tạo đơn hàng mới."""

    return orders_api.create_order(request)


# Inventory Analysis API routes
@app.get("/api/inventory/analysis/abc")
@handle_errors
async def api_get_abc_analysis(request: Request) -> Response:  # type: ignore[override]
    """API: ABC Analysis cho tồn kho."""

    return inventory_analysis_api.get_abc_analysis(request)


@app.get("/api/inventory/analysis/turnover")
@handle_errors
async def api_get_turnover_analysis(request: Request) -> Response:  # type: ignore[override]
    """API: Turnover Analysis cho tồn kho."""

    return inventory_analysis_api.get_turnover_analysis(request)


# HR API routes
@app.post("/api/hr/timesheets")
@handle_errors
async def api_create_timesheet(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo bản ghi chấm công."""

    return hr_api.create_timesheet(request)


@app.get("/api/hr/timesheets")
@handle_errors
async def api_list_timesheets(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách chấm công."""

    return hr_api.list_timesheets(request)


@app.post("/api/hr/salary/calculate")
@handle_errors
async def api_calculate_salary(request: Request) -> Response:  # type: ignore[override]
    """API: Tính lương cho nhân viên."""

    return hr_api.calculate_salary(request)


# Equipment API routes
@app.get("/api/equipment/types")
@handle_errors
async def api_list_equipment_types(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách loại thiết bị."""
    return equipment_api.list_equipment_types()


@app.post("/api/equipment/types")
@handle_errors
async def api_create_equipment_type(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo loại thiết bị mới."""
    return equipment_api.create_equipment_type(request)


@app.get("/api/equipment")
@handle_errors
async def api_list_equipment(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách thiết bị."""
    return equipment_api.list_equipment(request)


@app.post("/api/equipment")
@handle_errors
async def api_create_equipment(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo thiết bị mới."""
    return equipment_api.create_equipment(request)


@app.get("/api/equipment/:id/fuel-norms")
@handle_errors
async def api_list_fuel_norms(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách định mức nhiên liệu của thiết bị."""
    equipment_id = request.path_params.get("id", "")
    return equipment_api.list_fuel_norms(request)


@app.post("/api/equipment/:id/fuel-norms")
@handle_errors
async def api_create_fuel_norm(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo định mức nhiên liệu."""
    equipment_id = request.path_params.get("id", "")
    return equipment_api.create_fuel_norm(equipment_id, request)


@app.get("/api/equipment/repairs")
@handle_errors
async def api_list_equipment_repairs(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách phiếu sửa chữa."""
    return equipment_api.list_equipment_repairs(request)


@app.post("/api/equipment/repairs")
@handle_errors
async def api_create_equipment_repair(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo phiếu sửa chữa."""
    return equipment_api.create_equipment_repair(request)


@app.get("/api/equipment/maintenance")
@handle_errors
async def api_list_maintenance_records(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách lịch sử bảo dưỡng."""
    return equipment_api.list_maintenance_records(request)


@app.post("/api/equipment/maintenance")
@handle_errors
async def api_create_maintenance_record(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo bản ghi bảo dưỡng."""
    return equipment_api.create_maintenance_record(request)


@app.post("/api/equipment/maintenance/schedules")
@handle_errors
async def api_create_maintenance_schedule(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo lịch bảo dưỡng."""
    return equipment_api.create_maintenance_schedule(request)


# Procurement API routes
@app.get("/api/procurement/requests")
@handle_errors
async def api_list_purchase_requests(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách phiếu yêu cầu mua hàng."""
    return procurement_api.list_purchase_requests(request)


@app.post("/api/procurement/requests")
@handle_errors
async def api_create_purchase_request(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo phiếu yêu cầu mua hàng."""
    return procurement_api.create_purchase_request(request)


@app.post("/api/procurement/requests/:id/approve")
@handle_errors
async def api_approve_purchase_request(request: Request) -> Response:  # type: ignore[override]
    """API: Phê duyệt phiếu yêu cầu mua hàng."""
    request_id = request.path_params.get("id", "")
    return procurement_api.approve_purchase_request(request_id, request)


@app.get("/api/procurement/orders")
@handle_errors
async def api_list_purchase_orders(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách đơn mua hàng."""
    return procurement_api.list_purchase_orders(request)


@app.post("/api/procurement/orders")
@handle_errors
async def api_create_purchase_order(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo đơn mua hàng."""
    return procurement_api.create_purchase_order(request)


@app.get("/api/procurement/history")
@handle_errors
async def api_get_purchase_history(request: Request) -> Response:  # type: ignore[override]
    """API: Lịch sử mua hàng."""
    return procurement_api.get_purchase_history(request)


# Production Extended API routes
@app.get("/api/production/stages")
@handle_errors
async def api_list_production_stages(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách công đoạn sản xuất."""
    return production_extended_api.list_production_stages()


@app.post("/api/production/stages")
@handle_errors
async def api_create_production_stage(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo công đoạn sản xuất mới."""
    return production_extended_api.create_production_stage(request)


@app.get("/api/production/logs")
@handle_errors
async def api_list_production_logs(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách nhật ký sản xuất."""
    return production_extended_api.list_production_logs(request)


@app.post("/api/production/logs")
@handle_errors
async def api_create_production_log(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo nhật ký sản xuất."""
    return production_extended_api.create_production_log(request)


@app.get("/api/production/logs/:id")
@handle_errors
async def api_get_production_log_detail(request: Request) -> Response:  # type: ignore[override]
    """API: Chi tiết nhật ký sản xuất."""
    log_id = request.path_params.get("id", "")
    return production_extended_api.get_production_log_detail(log_id, request)


# Logistics API routes
@app.get("/api/logistics/vehicles")
@handle_errors
async def api_list_delivery_vehicles(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách phương tiện giao hàng."""
    return logistics_api.list_delivery_vehicles(request)


@app.post("/api/logistics/vehicles")
@handle_errors
async def api_create_delivery_vehicle(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo phương tiện giao hàng mới."""
    return logistics_api.create_delivery_vehicle(request)


@app.get("/api/logistics/deliveries")
@handle_errors
async def api_list_deliveries(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách phiếu giao hàng."""
    return logistics_api.list_deliveries(request)


@app.post("/api/logistics/deliveries")
@handle_errors
async def api_create_delivery(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo phiếu giao hàng."""
    return logistics_api.create_delivery(request)


@app.put("/api/logistics/deliveries/:id/status")
@handle_errors
async def api_update_delivery_status(request: Request) -> Response:  # type: ignore[override]
    """API: Cập nhật trạng thái giao hàng."""
    delivery_id = request.path_params.get("id", "")
    return logistics_api.update_delivery_status(delivery_id, request)


# Quality API routes
@app.get("/api/quality/non-conformities")
@handle_errors
async def api_list_non_conformities(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách sự không phù hợp."""
    return quality_api.list_non_conformities(request)


@app.post("/api/quality/non-conformities")
@handle_errors
async def api_create_non_conformity(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo sự không phù hợp mới."""
    return quality_api.create_non_conformity(request)


@app.post("/api/quality/non-conformities/:id/actions")
@handle_errors
async def api_add_non_conformity_action(request: Request) -> Response:  # type: ignore[override]
    """API: Thêm hành động khắc phục."""
    non_conformity_id = request.path_params.get("id", "")
    return quality_api.add_non_conformity_action(non_conformity_id, request)


@app.get("/api/quality/iso-documents")
@handle_errors
async def api_list_iso_documents(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách tài liệu ISO."""
    return quality_api.list_iso_documents(request)


@app.post("/api/quality/iso-documents")
@handle_errors
async def api_create_iso_document(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo tài liệu ISO mới."""
    return quality_api.create_iso_document(request)


@app.post("/api/quality/iso-documents/:id/versions")
@handle_errors
async def api_create_iso_document_version(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo phiên bản mới của tài liệu ISO."""
    document_id = request.path_params.get("id", "")
    return quality_api.create_iso_document_version(document_id, request)


# CRM Extended API routes
@app.get("/api/crm/accounts-receivable")
@handle_errors
async def api_list_accounts_receivable(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách công nợ phải thu."""
    return crm_extended_api.list_accounts_receivable(request)


@app.post("/api/crm/accounts-receivable")
@handle_errors
async def api_create_accounts_receivable(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo công nợ phải thu."""
    return crm_extended_api.create_accounts_receivable(request)


@app.get("/api/crm/accounts-payable")
@handle_errors
async def api_list_accounts_payable(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách công nợ phải trả."""
    return crm_extended_api.list_accounts_payable(request)


@app.get("/api/crm/supplier-contracts")
@handle_errors
async def api_list_supplier_contracts(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách hợp đồng nhà cung cấp."""
    return crm_extended_api.list_supplier_contracts(request)


@app.post("/api/crm/supplier-contracts")
@handle_errors
async def api_create_supplier_contract(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo hợp đồng nhà cung cấp."""
    return crm_extended_api.create_supplier_contract(request)


@app.get("/api/crm/supplier-evaluations")
@handle_errors
async def api_list_supplier_evaluations(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách đánh giá nhà cung cấp."""
    return crm_extended_api.list_supplier_evaluations(request)


@app.post("/api/crm/supplier-evaluations")
@handle_errors
async def api_create_supplier_evaluation(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo đánh giá nhà cung cấp."""
    return crm_extended_api.create_supplier_evaluation(request)


@app.get("/api/crm/customer-segmentation")
@handle_errors
async def api_get_customer_segmentation(request: Request) -> Response:  # type: ignore[override]
    """API: Phân khúc khách hàng."""
    return crm_extended_api.get_customer_segmentation_analysis(request)


@app.get("/api/crm/customer-behavior")
@handle_errors
async def api_get_customer_purchase_behavior(request: Request) -> Response:  # type: ignore[override]
    """API: Phân tích hành vi mua hàng."""
    return crm_extended_api.get_customer_purchase_behavior(request)


@app.get("/api/crm/customer-product-preferences")
@handle_errors
async def api_get_customer_product_preferences(request: Request) -> Response:  # type: ignore[override]
    """API: Sản phẩm ưa thích của khách hàng."""
    return crm_extended_api.get_customer_product_preferences_api(request)


@app.get("/api/crm/customer-feedback")
@handle_errors
async def api_list_customer_feedback(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách phản hồi khách hàng."""
    return crm_extended_api.list_customer_feedback(request)


@app.post("/api/crm/customer-feedback")
@handle_errors
async def api_create_customer_feedback(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo phản hồi khách hàng."""
    return crm_extended_api.create_customer_feedback(request)


@app.get("/api/crm/kpi-metrics")
@handle_errors
async def api_list_kpi_metrics(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách KPI metrics."""
    return crm_extended_api.list_kpi_metrics()


@app.post("/api/crm/kpi-metrics")
@handle_errors
async def api_create_kpi_metric(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo KPI metric mới."""
    return crm_extended_api.create_kpi_metric(request)


@app.get("/api/crm/kpi-records")
@handle_errors
async def api_list_kpi_records(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách ghi nhận KPI."""
    return crm_extended_api.list_kpi_records(request)


@app.post("/api/crm/kpi-records")
@handle_errors
async def api_create_kpi_record(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo ghi nhận KPI."""
    return crm_extended_api.create_kpi_record(request)


# HR Extended API routes
@app.get("/api/hr/contracts")
@handle_errors
async def api_list_employment_contracts(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách hợp đồng lao động."""
    return hr_extended_api.list_employment_contracts(request)


@app.post("/api/hr/contracts")
@handle_errors
async def api_create_employment_contract(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo hợp đồng lao động."""
    return hr_extended_api.create_employment_contract(request)


@app.get("/api/hr/performance-reviews")
@handle_errors
async def api_list_performance_reviews(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách đánh giá hiệu suất."""
    return hr_extended_api.list_performance_reviews(request)


@app.post("/api/hr/performance-reviews")
@handle_errors
async def api_create_performance_review(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo đánh giá hiệu suất."""
    return hr_extended_api.create_performance_review(request)


@app.get("/api/hr/training-records")
@handle_errors
async def api_list_training_records(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách ghi nhận đào tạo."""
    return hr_extended_api.list_training_records(request)


@app.post("/api/hr/training-records")
@handle_errors
async def api_create_training_record(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo ghi nhận đào tạo."""
    return hr_extended_api.create_training_record(request)


@app.get("/api/hr/exit-processes")
@handle_errors
async def api_list_exit_processes(request: Request) -> Response:  # type: ignore[override]
    """API: Danh sách quy trình nghỉ việc."""
    return hr_extended_api.list_exit_processes(request)


@app.post("/api/hr/exit-processes")
@handle_errors
async def api_create_exit_process(request: Request) -> Response:  # type: ignore[override]
    """API: Tạo quy trình nghỉ việc."""
    return hr_extended_api.create_exit_process(request)


# Reporting API routes
@app.get("/api/reports/production-efficiency")
@handle_errors
async def api_get_production_efficiency(request: Request) -> Response:  # type: ignore[override]
    """API: Báo cáo hiệu quả sản xuất."""
    return reporting_api.get_production_efficiency(request)


@app.get("/api/reports/profit")
@handle_errors
async def api_get_profit_analysis(request: Request) -> Response:  # type: ignore[override]
    """API: Báo cáo lợi nhuận."""
    return reporting_api.get_profit_analysis(request)


@app.get("/api/reports/inventory-time-series")
@handle_errors
async def api_get_inventory_time_series(request: Request) -> Response:  # type: ignore[override]
    """API: Báo cáo tồn kho theo thời gian."""
    return reporting_api.get_inventory_time_series_report(request)


@app.get("/api/reports/executive-dashboard")
@handle_errors
async def api_get_executive_dashboard(request: Request) -> Response:  # type: ignore[override]
    """API: Dashboard tổng quan."""
    return reporting_api.get_executive_dashboard(request)


@app.get("/api/reports/kpi-dashboard")
@handle_errors
async def api_get_kpi_dashboard(request: Request) -> Response:  # type: ignore[override]
    """API: Real-time KPI dashboard."""
    return reporting_api.get_kpi_dashboard(request)


def setup() -> None:
    """Chạy các bước khởi tạo khi start app."""

    setup_logging()
    init_db()


if __name__ == "__main__":
    setup()
    app.start(port=8000, url="0.0.0.0")


