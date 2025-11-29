"""
Script chạy migrations để khởi tạo database.

- Với SQLite: Sử dụng SQLAlchemy models để tạo schema tự động
- Với PostgreSQL: Chạy các file SQL migration
"""

from __future__ import annotations

import sys
from pathlib import Path
import subprocess
import os

# Thêm path để import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.core.config import settings
from backend.app.core.db import engine, init_db


def is_sqlite(db_uri: str) -> bool:
    """Kiểm tra xem database có phải SQLite không."""
    return db_uri.startswith("sqlite:///")


def run_sql_file_postgresql(file_path: Path, db_uri: str) -> bool:
    """Chạy file SQL bằng psql cho PostgreSQL."""
    # Parse connection string
    # postgresql+psycopg2://user:password@host:port/dbname
    uri = db_uri.replace("postgresql+psycopg2://", "")
    parts = uri.split("@")
    if len(parts) != 2:
        print(f"❌ Invalid database URI format")
        return False
    
    user_pass = parts[0].split(":")
    if len(user_pass) != 2:
        print(f"❌ Invalid database URI format")
        return False
    
    user = user_pass[0]
    password = user_pass[1]
    
    host_db = parts[1].split("/")
    if len(host_db) != 2:
        print(f"❌ Invalid database URI format")
        return False
    
    host_port = host_db[0].split(":")
    host = host_port[0]
    port = host_port[1] if len(host_port) > 1 else "5432"
    dbname = host_db[1]
    
    # Set PGPASSWORD environment variable
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    
    # Chạy psql
    cmd = [
        "psql",
        "-h", host,
        "-p", port,
        "-U", user,
        "-d", dbname,
        "-f", str(file_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ Đã chạy: {file_path.name}")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Lỗi khi chạy {file_path.name}:")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("❌ Không tìm thấy psql. Vui lòng cài đặt PostgreSQL client.")
        return False


def run_migrations_using_sqlalchemy(migration_files: list[Path]) -> bool:
    """Chạy migrations bằng SQLAlchemy (fallback nếu không có psql)."""
    print("⚠️  Sử dụng SQLAlchemy để chạy migrations...")
    
    from sqlalchemy import text
    
    try:
        with engine.begin() as conn:  # begin() tự động commit/rollback
            for file_path in migration_files:
                print(f"📄 Đang chạy: {file_path.name}")
                sql_content = file_path.read_text(encoding="utf-8")
                
                # Loại bỏ các câu lệnh không tương thích với SQLite
                if is_sqlite(settings.sqlalchemy_database_uri):
                    # Loại bỏ CREATE EXTENSION và các câu lệnh PostgreSQL-specific
                    lines = sql_content.split("\n")
                    filtered_lines = []
                    for line in lines:
                        if line.strip().startswith("CREATE EXTENSION"):
                            continue
                        if "uuid_generate_v4()" in line:
                            # SQLite không có uuid_generate_v4(), SQLAlchemy sẽ tự xử lý
                            line = line.replace("uuid_generate_v4()", "NULL")
                        filtered_lines.append(line)
                    sql_content = "\n".join(filtered_lines)
                
                # Chạy toàn bộ file SQL (SQLAlchemy có thể xử lý multiple statements)
                try:
                    conn.execute(text(sql_content))
                    print(f"✅ Đã chạy: {file_path.name}")
                except Exception as e:
                    print(f"❌ Lỗi khi chạy {file_path.name}: {e}")
                    # Rollback và dừng
                    raise
        
        return True
    except Exception as e:
        print(f"❌ Lỗi khi chạy migrations: {e}")
        return False


def init_sqlite_database() -> bool:
    """Khởi tạo SQLite database từ SQLAlchemy models."""
    print("📦 Đang tạo schema từ SQLAlchemy models...")
    
    try:
        # Import tất cả models để đảm bảo chúng được đăng ký
        # Import từ __init__.py để đảm bảo tất cả models được load
        from backend.app.models import (  # noqa: F401
            Base, Product, Customer, Supplier, Warehouse, Department, JobTitle,
            Employee, SalesOrder, ProductionOrder, StockDocument, BomMaterial,
            PricePolicy, MaterialPriceHistory, ProductionPlanDay, User,
            EquipmentType, Equipment, PurchaseRequest, PurchaseOrder,
            ProductionStage, DeliveryVehicle, Delivery, NonConformity,
            AccountsReceivable, EmploymentContract, AuditLog, InventorySnapshot,
            StockDocumentLine, StockTaking, StockTakingLine, SalesOrderLine,
            ProductionOrderLine, BomLabor, BomSemiProduct, TimeSheet,
            FuelConsumptionNorm, EquipmentRepair, EquipmentRepairLine,
            MaintenanceSchedule, MaintenanceRecord, PurchaseRequestLine,
            PurchaseOrderLine, StageOperation, ProductionLog, ProductionLogEntry,
            DeliveryLine, NonConformityAction, IsoDocument, IsoDocumentVersion,
            AccountsPayable, SupplierContract, SupplierEvaluation,
            CustomerSegment, CustomerFeedback, KpiMetric, KpiRecord,
            PerformanceReview, TrainingRecord, ExitProcess
        )
        
        # Tạo tất cả bảng
        init_db()
        print("✅ Đã tạo schema thành công!")
        return True
    except Exception as e:
        print(f"❌ Lỗi khi tạo schema: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Chạy migrations để khởi tạo database."""
    db_uri = settings.sqlalchemy_database_uri
    
    print(f"🔗 Database URI: {db_uri}")
    print(f"📂 Database path: {settings.db_path}")
    
    # Với SQLite: dùng SQLAlchemy models
    if is_sqlite(db_uri):
        print("\n🗄️  Phát hiện SQLite database")
        print("🚀 Khởi tạo database từ SQLAlchemy models...\n")
        
        if init_sqlite_database():
            print("\n✅ Hoàn thành! Database đã được khởi tạo.")
        else:
            print("\n❌ Khởi tạo database thất bại.")
        return
    
    # Với PostgreSQL: chạy SQL files
    print("\n🗄️  Phát hiện PostgreSQL database")
    
    migrations_dir = Path(__file__).parent.parent / "migrations"
    
    if not migrations_dir.exists():
        print(f"❌ Thư mục migrations không tồn tại: {migrations_dir}")
        return
    
    # Lấy tất cả file migration và sắp xếp theo tên (theo số thứ tự)
    migration_files = sorted(
        migrations_dir.glob("*.sql"),
        key=lambda x: int(x.stem.split("_")[0]) if x.stem.split("_")[0].isdigit() else 999
    )
    
    # Loại bỏ README.md nếu có
    migration_files = [f for f in migration_files if f.name != "README.md"]
    
    if not migration_files:
        print("⚠️  Không tìm thấy file migration nào")
        return
    
    print(f"📂 Tìm thấy {len(migration_files)} file migration:")
    for f in migration_files:
        print(f"   - {f.name}")
    
    print("\n🚀 Bắt đầu chạy migrations...\n")
    
    success = True
    for file_path in migration_files:
        print(f"📄 Đang chạy: {file_path.name}")
        
        # Thử dùng psql trước (nếu có)
        try:
            if run_sql_file_postgresql(file_path, db_uri):
                continue
        except Exception:
            pass
        
        # Fallback: dùng SQLAlchemy
        if not run_migrations_using_sqlalchemy([file_path]):
            success = False
            print(f"❌ Dừng migration do lỗi ở {file_path.name}")
            break
    
    if success:
        print(f"\n✅ Hoàn thành! Đã chạy {len(migration_files)} migrations.")
    else:
        print(f"\n❌ Migration thất bại. Vui lòng kiểm tra lỗi ở trên.")


if __name__ == "__main__":
    main()

