"""Script kiểm tra database và chạy migration từ Excel."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.core.db import get_session
from backend.app.models.entities import Product, Customer, Warehouse, Department, Employee

# Kiểm tra dữ liệu hiện tại
print("🔍 Kiểm tra dữ liệu hiện tại trong database...")
with get_session() as db:
    products = db.query(Product).count()
    customers = db.query(Customer).count()
    warehouses = db.query(Warehouse).count()
    departments = db.query(Department).count()
    employees = db.query(Employee).count()
    
    print(f"   Products: {products}")
    print(f"   Customers: {customers}")
    print(f"   Warehouses: {warehouses}")
    print(f"   Departments: {departments}")
    print(f"   Employees: {employees}")

if products == 0 and customers == 0:
    print("\n📥 Database trống, bắt đầu migration từ Excel...")
    print("=" * 60)
    import subprocess
    import os
    excel_path = Path(__file__).parent.parent / "appsheet_docs_old" / "appsheet_data" / "home.xlsx"
    result = subprocess.run([
        sys.executable,
        str(Path(__file__).parent / "migrate_from_excel.py"),
        "--excel-path", str(excel_path)
    ], cwd=Path(__file__).parent.parent)
    sys.exit(result.returncode)
else:
    print("\n✅ Database đã có dữ liệu.")
    print("   Nếu muốn migrate lại, hãy xóa database trước hoặc chạy:")
    print("   python scripts/migrate_from_excel.py --excel-path appsheet_docs_old/appsheet_data/home.xlsx")

