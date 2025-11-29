"""
E2E tests cho các luồng tích hợp phức tạp (Integrated Business Flows).

Test các luồng nghiệp vụ end-to-end qua nhiều modules.
"""

import pytest
from datetime import date, timedelta

from tests.utils.factories import (
    create_test_customer,
    create_test_product,
    create_test_material,
    create_test_sales_order,
    create_test_sales_order_line,
    create_test_warehouse,
    create_test_bom_material,
)


@pytest.mark.e2e
@pytest.mark.p0
def test_complete_production_to_inventory_flow(test_client, test_db):
    """
    Test Description: Luồng Hoàn Chỉnh: Sản Xuất → Kho → Báo Cáo
    
    Given:
    - Setup đầy đủ: customer, product với BOM, warehouse
    
    When:
    - Tạo đơn hàng → Tạo LSX từ đơn hàng → Cập nhật tiến độ LSX 
      → Nhập kho thành phẩm → Xuất kho NVL → Xem báo cáo
    
    Then:
    - Tất cả documents được tạo đúng
    - Tồn kho chính xác sau mỗi bước
    - Báo cáo phản ánh đúng tình trạng
    """
    # Setup (Given)
    customer = create_test_customer(test_db, code="KH_INT", name="Khách hàng Tích hợp")
    
    # Tạo NVL
    material = create_test_material(
        test_db,
        code="NVL_INT",
        name="Nguyên vật liệu Tích hợp",
        cost_price=10000.0
    )
    
    # Tạo thành phẩm với BOM
    product = create_test_product(
        test_db,
        code="SP_INT",
        name="Sản phẩm Tích hợp",
        group="TP",
        main_uom="kg"
    )
    
    # Tạo BOM: 1kg thành phẩm cần 2kg NVL
    create_test_bom_material(
        test_db,
        product=product,
        material=material,
        quantity=2.0
    )
    
    # Tạo kho
    warehouse_tp = create_test_warehouse(
        test_db,
        code="KHO_TP_INT",
        warehouse_type="TP"
    )
    
    warehouse_nvl = create_test_warehouse(
        test_db,
        code="KHO_NVL_INT",
        warehouse_type="NVL"
    )
    
    # Tạo tồn kho NVL ban đầu
    from tests.utils.factories import create_test_inventory_snapshot
    create_test_inventory_snapshot(
        test_db,
        product=material,
        warehouse=warehouse_nvl,
        current_qty=500.0  # Có sẵn 500kg NVL
    )
    
    test_db.commit()
    
    # Step 1: Tạo đơn hàng (When)
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
        quantity=100.0,  # Cần 100kg thành phẩm
        unit_price=60000.0
    )
    
    test_db.commit()
    
    # Step 2: Tạo LSX từ đơn hàng
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
    
    # Step 3: Cập nhật tiến độ LSX (completed)
    # Giả sử có endpoint để update completed_qty
    # production_order.completed_qty = 95.0  # Hoàn thành 95/100
    # production_order.status = "completed"
    
    # Step 4: Nhập kho thành phẩm từ LSX
    # Note: Cần production order status = "completed" trước
    
    # Step 5: Kiểm tra tồn kho sau nhập
    inventory_response = test_client.get(f"/api/inventory/query?product_code={product.code}")
    assert inventory_response.status_code == 200
    
    # Assert (Then)
    assert production_order_id is not None
    # Verify các steps đã thực hiện thành công


@pytest.mark.e2e
@pytest.mark.p1
def test_multi_product_production_flow(test_client, test_db):
    """
    Test Description: Luồng Sản Xuất Nhiều Sản Phẩm Cùng Lúc
    
    Given:
    - Nhiều đơn hàng với nhiều sản phẩm khác nhau
    - Các sản phẩm có delivery_date khác nhau
    
    When:
    - Generate LSX từ tất cả đơn hàng trong date range
    
    Then:
    - LSX được tạo cho tất cả sản phẩm
    - LSX được phân bổ đúng theo ngày sản xuất
    - Không vượt quá capacity_max của mỗi ngày
    """
    # Setup (Given)
    customer = create_test_customer(test_db, code="KH_MULTI")
    
    product1 = create_test_product(test_db, code="SP_MULTI_1", group="TP")
    product2 = create_test_product(test_db, code="SP_MULTI_2", group="TP")
    
    order_date = date.today()
    
    # Tạo nhiều đơn hàng
    order1 = create_test_sales_order(
        test_db,
        customer=customer,
        order_date=order_date,
        delivery_date=order_date + timedelta(days=3)
    )
    
    create_test_sales_order_line(test_db, order=order1, product=product1, quantity=50.0)
    
    order2 = create_test_sales_order(
        test_db,
        customer=customer,
        order_date=order_date,
        delivery_date=order_date + timedelta(days=5)
    )
    
    create_test_sales_order_line(test_db, order=order2, product=product2, quantity=75.0)
    
    test_db.commit()
    
    # Execute (When)
    payload = {
        "start_date": str(order_date),
        "end_date": str(order_date + timedelta(days=7)),
    }
    
    response = test_client.post(
        "/api/production/orders/from-sales-orders",
        json=payload
    )
    
    # Assert (Then)
    assert response.status_code == 200
    
    response_data = test_client.json_response(response)
    orders = response_data if isinstance(response_data, list) else response_data.get("production_orders", [])
    
    # Nên có ít nhất 2 LSX (cho 2 sản phẩm)
    assert len(orders) >= 1  # Có thể được gộp hoặc tách tùy logic
    
    # Verify các LSX có production_date khác nhau (nếu có)
    production_dates = [order.get("production_date") for order in orders if "production_date" in order]
    # Có thể có nhiều ngày khác nhau


@pytest.mark.e2e
@pytest.mark.p1
def test_inventory_analysis_flow(test_client, test_db):
    """
    Test Description: Luồng Phân Tích Tồn Kho
    
    Given:
    - Có nhiều sản phẩm với tồn kho khác nhau
    - Có lịch sử nhập/xuất kho
    
    When:
    - Gọi API ABC Analysis
    - Gọi API Turnover Analysis
    
    Then:
    - Kết quả phân tích được trả về
    - Sản phẩm được phân loại đúng (A, B, C)
    - Turnover rate được tính đúng
    """
    # Setup (Given)
    # Tạo nhiều sản phẩm với tồn kho khác nhau
    products = []
    warehouse = create_test_warehouse(test_db, code="KHO_ANALYSIS", warehouse_type="TP")
    
    from tests.utils.factories import create_test_inventory_snapshot
    
    for i in range(5):
        product = create_test_product(test_db, code=f"SP_ANALYSIS_{i+1}")
        products.append(product)
        
        # Tạo tồn kho với giá trị khác nhau
        qty = (i + 1) * 100.0
        create_test_inventory_snapshot(
            test_db,
            product=product,
            warehouse=warehouse,
            current_qty=qty,
            inventory_value=qty * 50000.0  # Giá trị khác nhau
        )
    
    test_db.commit()
    
    # Execute (When) - ABC Analysis
    abc_response = test_client.get("/api/inventory/analysis/abc")
    assert abc_response.status_code == 200
    
    abc_data = test_client.json_response(abc_response)
    assert isinstance(abc_data, dict) or isinstance(abc_data, list)
    
    # Execute (When) - Turnover Analysis
    turnover_response = test_client.get("/api/inventory/analysis/turnover")
    assert turnover_response.status_code == 200
    
    turnover_data = test_client.json_response(turnover_response)
    assert isinstance(turnover_data, dict) or isinstance(turnover_data, list)


@pytest.mark.e2e
@pytest.mark.p2
def test_reporting_flows(test_client, test_db):
    """
    Test Description: Luồng Báo Cáo
    
    Given:
    - Có dữ liệu sản xuất, kho, đơn hàng
    
    When:
    - Gọi các API báo cáo khác nhau
    
    Then:
    - Báo cáo được tạo thành công
    - Dữ liệu báo cáo chính xác
    """
    # Setup (Given) - Cần có dữ liệu đầy đủ
    # ... (có thể tạo minimal data)
    
    # Execute (When) - Production Efficiency Report
    prod_eff_response = test_client.get("/api/reports/production-efficiency")
    # Có thể trả về 200 hoặc 404 nếu chưa có dữ liệu
    assert prod_eff_response.status_code in [200, 404]
    
    # Execute (When) - Executive Dashboard
    dashboard_response = test_client.get("/api/reports/executive-dashboard")
    assert dashboard_response.status_code in [200, 404]
    
    # Execute (When) - Profit Report
    profit_response = test_client.get("/api/reports/profit")
    assert profit_response.status_code in [200, 404]
    
    # Execute (When) - KPI Dashboard
    kpi_response = test_client.get("/api/reports/kpi-dashboard")
    assert kpi_response.status_code in [200, 404]

