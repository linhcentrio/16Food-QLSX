# Tests cho Hệ Thống QLSX 16Food

## Cấu Trúc Tests

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures và configuration
├── utils/
│   ├── __init__.py
│   ├── test_db.py          # Database utilities
│   ├── test_client.py      # Test client wrapper
│   └── factories.py        # Factory functions tạo test data
└── e2e/
    ├── __init__.py
    ├── test_production_flows.py      # UC-01, Production flows (P0)
    ├── test_inventory_flows.py       # UC-02, UC-03, Inventory flows (P0/P1)
    ├── test_bom_flows.py             # BOM và cost calculation (P1)
    └── test_integrated_business_flows.py  # Complex integrated flows
```

## Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

Dependencies cho tests:
- pytest>=7.4.0
- pytest-asyncio>=0.21.0
- pytest-cov>=4.1.0
- httpx>=0.24.0

## Chạy Tests

### Chạy tất cả tests

```bash
pytest
```

### Chạy tests theo marker

```bash
# Chỉ chạy E2E tests
pytest -m e2e

# Chạy tests P0 (critical)
pytest -m p0

# Chạy tests P1 (important)
pytest -m p1

# Chạy tests theo module
pytest tests/e2e/test_production_flows.py
```

### Chạy với coverage

```bash
pytest --cov=backend --cov-report=html
```

Coverage report sẽ được tạo trong `htmlcov/index.html`

### Chạy với verbose output

```bash
pytest -v
```

### Chạy một test cụ thể

```bash
pytest tests/e2e/test_production_flows.py::test_uc01_create_production_orders_from_sales_order -v
```

## Test Format

Tất cả tests theo format **Given-When-Then**:

```python
def test_example(test_client, test_db):
    """
    Test Description: [Mô tả ngắn gọn]
    
    UC Reference: UC-XX (nếu có)
    
    Given:
    - [Điều kiện 1]
    - [Điều kiện 2]
    
    When:
    - [Hành động 1]
    - [Hành động 2]
    
    Then:
    - [Kết quả mong đợi 1]
    - [Kết quả mong đợi 2]
    """
    # Setup (Given)
    # ...
    
    # Execute (When)
    # ...
    
    # Assert (Then)
    # ...
```

## Test Data Strategy

- Mỗi test sử dụng SQLite in-memory database riêng
- Mỗi test tạo dữ liệu riêng (isolation)
- Sử dụng factories để tạo test data nhanh chóng
- Cleanup tự động sau mỗi test (rollback transaction)

## Test Priorities

- **P0 (Critical)**: UC-01, UC-02, luồng sản xuất hoàn chỉnh
- **P1 (Important)**: UC-03, BOM flows, inventory analysis
- **P2 (Secondary)**: Reporting, CRM flows

## Notes

- Tests sẽ tự động rollback sau mỗi test để đảm bảo isolation
- Database được tạo trong memory, không cần cleanup thủ công
- Test client sử dụng httpx để test async endpoints

## Troubleshooting

### Lỗi import

Nếu gặp lỗi import, đảm bảo PYTHONPATH đúng:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Lỗi database

Database được tạo tự động trong memory. Nếu có lỗi, kiểm tra:
- SQLAlchemy models đã được import đầy đủ
- Base.metadata.create_all() đã được gọi

### Lỗi test client

Nếu test client không hoạt động, kiểm tra:
- httpx đã được cài đặt
- Robyn app được import đúng

