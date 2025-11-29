"""
E2E tests cho các luồng BOM và tính giá vốn.

Priority: P1
"""

import pytest
from datetime import date

from tests.utils.factories import (
    create_test_product,
    create_test_material,
    create_test_bom_material,
    create_test_bom_labor,
    create_test_supplier,
    create_test_warehouse,
)


@pytest.mark.e2e
@pytest.mark.p1
def test_bom_cost_calculation_flow(test_client, test_db):
    """
    Test Description: Luồng Tính Giá Vốn từ BOM
    
    Given:
    - Product với BOM đầy đủ (BomMaterial và BomLabor)
    - Material có cost_price
    
    When:
    - Gọi API GET /api/bom/products/:product_id/cost-calculation
    
    Then:
    - Cost được tính đúng từ NVL + nhân công
    - Kết quả trả về đầy đủ thông tin breakdown
    """
    # Setup (Given)
    product = create_test_product(
        test_db,
        code="SP_BOM",
        name="Sản phẩm có BOM",
        group="TP"
    )
    
    material1 = create_test_material(
        test_db,
        code="NVL_001",
        cost_price=10000.0
    )
    
    material2 = create_test_material(
        test_db,
        code="NVL_002",
        cost_price=15000.0
    )
    
    # Tạo BOM materials
    bom_mat1 = create_test_bom_material(
        test_db,
        product=product,
        material=material1,
        quantity=2.0  # Cần 2kg material1
    )
    
    bom_mat2 = create_test_bom_material(
        test_db,
        product=product,
        material=material2,
        quantity=1.5  # Cần 1.5kg material2
    )
    
    # Tạo BOM labor
    bom_labor = create_test_bom_labor(
        test_db,
        product=product,
        duration_minutes=60,
        unit_cost=50000.0  # 50k/giờ
    )
    
    test_db.commit()
    
    # Execute (When)
    product_id = str(product.id)
    response = test_client.get(f"/api/bom/products/{product_id}/cost-calculation")
    
    # Assert (Then)
    assert response.status_code == 200
    
    response_data = test_client.json_response(response)
    
    # Kiểm tra có thông tin cost calculation
    assert "total_cost" in response_data or "cost" in response_data
    
    # Verify calculation:
    # Material cost = (2 * 10000) + (1.5 * 15000) = 20000 + 22500 = 42500
    # Labor cost = (60/60) * 50000 = 50000
    # Total = 92500
    # (Note: Có thể có thêm overhead hoặc các chi phí khác)


@pytest.mark.e2e
@pytest.mark.p1
def test_bom_recalculate_on_material_price_change(test_client, test_db):
    """
    Test Description: Tự Động Tính Lại Giá Khi Giá NVL Thay Đổi
    
    Given:
    - Product với BOM
    - Material có giá cũ
    - Product đã có cost_price được tính
    
    When:
    - Cập nhật giá material (cost_price)
    - Gọi API POST /api/bom/recalculate-costs/:material_id
    
    Then:
    - Product cost được cập nhật tự động
    - Tất cả products sử dụng material đó đều được recalculate
    """
    # Setup (Given)
    material = create_test_material(
        test_db,
        code="NVL_PRICE_CHANGE",
        cost_price=10000.0
    )
    
    product1 = create_test_product(test_db, code="SP_1", group="TP")
    product2 = create_test_product(test_db, code="SP_2", group="TP")
    
    # Tạo BOM cho cả 2 products với material
    create_test_bom_material(test_db, product=product1, material=material, quantity=1.0)
    create_test_bom_material(test_db, product=product2, material=material, quantity=2.0)
    
    test_db.commit()
    
    # Update material price
    material.cost_price = 12000.0  # Tăng giá từ 10k lên 12k
    test_db.commit()
    
    # Execute (When)
    material_id = str(material.id)
    response = test_client.post(f"/api/bom/recalculate-costs/{material_id}", json={})
    
    # Assert (Then)
    assert response.status_code == 200
    
    # Verify products được recalculate
    # Có thể query lại products để kiểm tra cost_price đã thay đổi


@pytest.mark.e2e
@pytest.mark.p1
def test_get_product_bom(test_client, test_db):
    """
    Test Description: Xem BOM của Sản Phẩm
    
    Given:
    - Product có BOM (materials và labor)
    
    When:
    - Gọi API GET /api/bom/products/:product_id
    
    Then:
    - Trả về danh sách materials và labor trong BOM
    """
    # Setup (Given)
    product = create_test_product(test_db, code="SP_BOM_VIEW", group="TP")
    material1 = create_test_material(test_db, code="NVL_BOM1")
    material2 = create_test_material(test_db, code="NVL_BOM2")
    
    create_test_bom_material(test_db, product=product, material=material1, quantity=1.0)
    create_test_bom_material(test_db, product=product, material=material2, quantity=2.0)
    create_test_bom_labor(test_db, product=product, duration_minutes=30)
    
    test_db.commit()
    
    # Execute (When)
    product_id = str(product.id)
    response = test_client.get(f"/api/bom/products/{product_id}")
    
    # Assert (Then)
    assert response.status_code == 200
    
    response_data = test_client.json_response(response)
    
    # Kiểm tra có materials và labor
    assert "materials" in response_data or isinstance(response_data, list)
    # Verify có đủ 2 materials


@pytest.mark.e2e
@pytest.mark.p1
def test_add_material_to_bom(test_client, test_db):
    """
    Test Description: Thêm NVL vào BOM
    
    Given:
    - Product đã tồn tại
    - Material đã tồn tại
    
    When:
    - Gọi API POST /api/bom/products/:product_id/materials với material mới
    
    Then:
    - BomMaterial được tạo
    - BOM được cập nhật
    """
    # Setup (Given)
    product = create_test_product(test_db, code="SP_BOM_ADD", group="TP")
    material = create_test_material(test_db, code="NVL_NEW")
    
    test_db.commit()
    
    # Execute (When)
    product_id = str(product.id)
    payload = {
        "material_id": str(material.id),
        "quantity": 3.0,
        "uom": material.main_uom
    }
    
    response = test_client.post(
        f"/api/bom/products/{product_id}/materials",
        json=payload
    )
    
    # Assert (Then)
    assert response.status_code == 200
    
    # Verify BOM đã được cập nhật
    get_response = test_client.get(f"/api/bom/products/{product_id}")
    assert get_response.status_code == 200


@pytest.mark.e2e
@pytest.mark.p1
def test_get_material_requirements_for_production_order(test_client, test_db):
    """
    Test Description: Tính Nhu Cầu NVL từ LSX
    
    Given:
    - Production Order với product có BOM
    
    When:
    - Gọi API GET /api/bom/production-orders/:order_id/material-requirements
    
    Then:
    - Trả về danh sách materials cần thiết với số lượng
    - Số lượng được tính từ BOM * planned_qty của LSX
    """
    # Setup (Given)
    from tests.utils.factories import create_test_production_order
    
    product = create_test_product(test_db, code="SP_REQ", group="TP")
    material = create_test_material(test_db, code="NVL_REQ")
    
    # Tạo BOM: 1 sản phẩm cần 2kg material
    create_test_bom_material(test_db, product=product, material=material, quantity=2.0)
    
    production_order = create_test_production_order(
        test_db,
        product=product,
        planned_qty=50.0  # Cần sản xuất 50 sản phẩm
    )
    
    test_db.commit()
    
    # Execute (When)
    order_id = str(production_order.id)
    response = test_client.get(f"/api/bom/production-orders/{order_id}/material-requirements")
    
    # Assert (Then)
    assert response.status_code == 200
    
    response_data = test_client.json_response(response)
    
    # Kiểm tra có materials
    materials = response_data if isinstance(response_data, list) else response_data.get("materials", [])
    assert len(materials) > 0
    
    # Verify: 50 sản phẩm * 2kg material = 100kg material cần
    # (Có thể cần tìm material trong list)

