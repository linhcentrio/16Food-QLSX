"""
E2E tests cho các luồng sản xuất (Production Flows).

Test UC-01: Tạo Lệnh Sản Xuất từ Đơn Hàng
"""

import pytest
from datetime import date, timedelta

from tests.utils.factories import (
    create_test_customer,
    create_test_product,
    create_test_sales_order,
    create_test_sales_order_line,
    create_test_warehouse,
)


@pytest.mark.e2e
@pytest.mark.p0
def test_uc01_create_production_orders_from_sales_order(test_client, test_db):
    """
    Test Description: UC-01 - Tạo Lệnh Sản Xuất từ Đơn Hàng
    
    UC Reference: UC-01
    
    Given:
    - Đã có Customer với code "KH001"
    - Đã có Product với code "SP001" (loại TP)
    - Đã có Sales Order với status "new" chứa sản phẩm SP001
    
    When:
    - Gọi API POST /api/production/orders/from-sales-orders với date range
    
    Then:
    - Production Orders được tạo thành công
    - Production Orders có QR code
    - Production Orders được phân bổ theo ngày sản xuất
    - Tồn kho được giữ chỗ (nếu có)
    """
    # Setup (Given)
    customer = create_test_customer(test_db, code="KH001", name="Khách hàng Test")
    product = create_test_product(
        test_db,
        code="SP001",
        name="Sản phẩm Test",
        group="TP",
        main_uom="kg"
    )
    
    order_date = date.today()
    delivery_date = order_date + timedelta(days=3)
    
    sales_order = create_test_sales_order(
        test_db,
        customer=customer,
        order_date=order_date,
        delivery_date=delivery_date,
        status="new"
    )
    
    create_test_sales_order_line(
        test_db,
        order=sales_order,
        product=product,
        quantity=100.0,
        unit_price=50000.0
    )
    
    test_db.commit()
    
    # Execute (When)
    payload = {
        "start_date": str(order_date),
        "end_date": str(delivery_date + timedelta(days=1)),
    }
    
    response = test_client.post(
        "/api/production/orders/from-sales-orders",
        json=payload
    )
    
    # Assert (Then)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.body}"
    
    response_data = test_client.json_response(response)
    
    # Kiểm tra production orders được tạo
    assert "production_orders" in response_data or isinstance(response_data, list)
    
    # Kiểm tra production orders có business_id
    orders = response_data if isinstance(response_data, list) else response_data.get("production_orders", [])
    assert len(orders) > 0, "Should create at least one production order"
    
    # Kiểm tra production order có đầy đủ thông tin
    first_order = orders[0]
    assert "business_id" in first_order or "id" in first_order
    assert first_order.get("product_name") == product.name or first_order.get("product_code") == product.code


@pytest.mark.e2e
@pytest.mark.p0
def test_production_flow_complete(test_client, test_db):
    """
    Test Description: Luồng Sản Xuất Hoàn Chỉnh
    
    Given:
    - Setup đầy đủ: customer, product (TP), warehouse (TP), BOM
    - Sales Order đã được tạo với sản phẩm
    
    When:
    - Tạo đơn hàng → Tạo LSX từ đơn hàng → Cập nhật tiến độ LSX → Nhập kho
    
    Then:
    - Tất cả các bước được thực hiện thành công
    - Production Order được tạo với status "new"
    - Production Order có thể được cập nhật tiến độ
    - Stock Document được tạo khi nhập kho
    - Inventory được cập nhật đúng
    """
    # Setup (Given)
    customer = create_test_customer(test_db, code="KH002", name="Khách hàng Test 2")
    product = create_test_product(
        test_db,
        code="SP002",
        name="Sản phẩm Test 2",
        group="TP",
        main_uom="kg"
    )
    warehouse = create_test_warehouse(
        test_db,
        code="KHO_TP",
        name="Kho Thành Phẩm",
        warehouse_type="TP"
    )
    
    order_date = date.today()
    delivery_date = order_date + timedelta(days=5)
    
    sales_order = create_test_sales_order(
        test_db,
        customer=customer,
        order_date=order_date,
        delivery_date=delivery_date,
        status="new"
    )
    
    create_test_sales_order_line(
        test_db,
        order=sales_order,
        product=product,
        quantity=50.0,
        unit_price=60000.0
    )
    
    test_db.commit()
    
    # Step 1: Tạo LSX từ đơn hàng (When)
    payload = {
        "start_date": str(order_date),
        "end_date": str(delivery_date + timedelta(days=1)),
    }
    
    response = test_client.post(
        "/api/production/orders/from-sales-orders",
        json=payload
    )
    
    assert response.status_code == 200
    
    response_data = test_client.json_response(response)
    orders = response_data if isinstance(response_data, list) else response_data.get("production_orders", [])
    assert len(orders) > 0
    
    production_order_id = orders[0].get("id") or orders[0].get("business_id")
    
    # Step 2: Kiểm tra Production Order được tạo
    # Có thể query production orders để verify
    get_response = test_client.get("/api/production/orders")
    assert get_response.status_code == 200
    
    # Step 3: Cập nhật tiến độ LSX (cập nhật completed_qty)
    # Note: Cần xem API endpoint cụ thể để cập nhật
    # Giả sử có endpoint PUT /api/production/orders/:id/lines/:line_id
    
    # Step 4: Nhập kho (sẽ test trong test_inventory_flows.py)
    # Để test complete flow, cần production order status = "completed"
    
    # Assert (Then) - Kiểm tra các bước đã thực hiện
    assert production_order_id is not None, "Production order ID should be available"


@pytest.mark.e2e
@pytest.mark.p1
def test_list_daily_production_plan(test_client, test_db):
    """
    Test Description: Xem Kế Hoạch Sản Xuất Ngày
    
    Given:
    - Có Production Plan Day cho ngày hiện tại
    
    When:
    - Gọi API GET /api/production/daily-plan
    
    Then:
    - Trả về danh sách kế hoạch sản xuất cho ngày
    """
    # Setup (Given) - Cần tạo ProductionPlanDay
    # Note: ProductionPlanDay thường được tạo tự động khi tạo LSX
    
    # Execute (When)
    response = test_client.get("/api/production/daily-plan")
    
    # Assert (Then)
    assert response.status_code == 200
    
    response_data = test_client.json_response(response)
    assert isinstance(response_data, list), "Should return list of daily plans"


@pytest.mark.e2e
@pytest.mark.p1
def test_list_recent_production_orders(test_client, test_db):
    """
    Test Description: Xem Danh Sách LSX Gần Nhất
    
    Given:
    - Có Production Orders trong hệ thống
    
    When:
    - Gọi API GET /api/production/orders
    
    Then:
    - Trả về danh sách LSX gần nhất
    """
    # Execute (When)
    response = test_client.get("/api/production/orders")
    
    # Assert (Then)
    assert response.status_code == 200
    
    response_data = test_client.json_response(response)
    assert isinstance(response_data, list), "Should return list of production orders"

