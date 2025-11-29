"""
Script riêng biệt để xử lý:
1. Export Excel (.xlsx) sang CSV
2. Import CSV vào database SQLite

Sử dụng:
    # Export tất cả sheets ra CSV
    python excel_to_csv_import.py export path/to/file.xlsx --output-dir ./csv_output
    
    # Export chỉ một số sheets cụ thể
    python excel_to_csv_import.py export path/to/file.xlsx --sheets san_pham kh_ncc --output-dir ./csv_output
    
    # Import từ CSV vào database
    python excel_to_csv_import.py import path/to/csv_folder --table product
    
    # Import tất cả CSV files trong folder
    python excel_to_csv_import.py import path/to/csv_folder --all
    
    # Pipeline: Export + Import cùng lúc
    python excel_to_csv_import.py pipeline path/to/file.xlsx

Author: AI Assistant
Created: 2024
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from datetime import datetime, date
from typing import Any, Generator
import os

import pandas as pd

# Thêm path để import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def safe_str(value: Any) -> str | None:
    """Chuyển đổi giá trị sang string an toàn."""
    if pd.isna(value) or value is None:
        return None
    result = str(value).strip()
    return result if result else None


def safe_float(value: Any) -> float | None:
    """Chuyển đổi giá trị sang float an toàn."""
    if pd.isna(value) or value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value: Any) -> int | None:
    """Chuyển đổi giá trị sang int an toàn."""
    if pd.isna(value) or value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def safe_date(value: Any) -> date | None:
    """Chuyển đổi giá trị sang date an toàn."""
    if pd.isna(value) or value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        if isinstance(value, str):
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return pd.to_datetime(value).date()
    except (ValueError, TypeError):
        return None


def clean_column_name(name: str) -> str:
    """Chuẩn hóa tên cột: lowercase, thay space bằng underscore."""
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


# =============================================================================
# EXCEL TO CSV EXPORT
# =============================================================================

class ExcelToCsvExporter:
    """Class xử lý export Excel sang CSV."""
    
    def __init__(self, excel_path: str | Path, output_dir: str | Path = None):
        self.excel_path = Path(excel_path)
        self.output_dir = Path(output_dir) if output_dir else self.excel_path.parent / "csv_export"
        
        if not self.excel_path.exists():
            raise FileNotFoundError(f"File Excel không tồn tại: {self.excel_path}")
    
    def get_sheet_names(self) -> list[str]:
        """Lấy danh sách tên các sheets trong file Excel."""
        xl = pd.ExcelFile(self.excel_path, engine='openpyxl')
        return xl.sheet_names
    
    def export_sheet(self, sheet_name: str, clean_columns: bool = True) -> Path:
        """
        Export một sheet cụ thể ra CSV.
        
        Args:
            sheet_name: Tên sheet cần export
            clean_columns: Có chuẩn hóa tên cột không
            
        Returns:
            Path đến file CSV đã tạo
        """
        try:
            df = pd.read_excel(self.excel_path, sheet_name=sheet_name, engine='openpyxl')
        except ValueError as e:
            raise ValueError(f"Sheet '{sheet_name}' không tồn tại trong file Excel") from e
        
        # Chuẩn hóa tên cột nếu cần
        if clean_columns:
            df.columns = [clean_column_name(col) for col in df.columns]
        
        # Tạo thư mục output nếu chưa có
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Tạo file CSV
        csv_filename = f"{sheet_name}.csv"
        csv_path = self.output_dir / csv_filename
        
        # Export với encoding UTF-8 BOM để Excel đọc được tiếng Việt
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"✅ Đã export sheet '{sheet_name}' -> {csv_path} ({len(df)} dòng)")
        return csv_path
    
    def export_all(self, sheets: list[str] = None, clean_columns: bool = True) -> list[Path]:
        """
        Export nhiều sheets hoặc tất cả sheets ra CSV.
        
        Args:
            sheets: Danh sách sheets cần export (None = tất cả)
            clean_columns: Có chuẩn hóa tên cột không
            
        Returns:
            Danh sách paths đến các files CSV đã tạo
        """
        if sheets is None:
            sheets = self.get_sheet_names()
        
        print(f"\n📁 Export Excel sang CSV")
        print(f"   File nguồn: {self.excel_path}")
        print(f"   Thư mục đích: {self.output_dir}")
        print(f"   Số sheets: {len(sheets)}\n")
        
        exported = []
        for sheet_name in sheets:
            try:
                csv_path = self.export_sheet(sheet_name, clean_columns)
                exported.append(csv_path)
            except Exception as e:
                print(f"⚠️  Lỗi export sheet '{sheet_name}': {e}")
        
        print(f"\n✅ Hoàn thành! Đã export {len(exported)}/{len(sheets)} sheets")
        return exported


# =============================================================================
# CSV TO DATABASE IMPORT  
# =============================================================================

class CsvToDbImporter:
    """Class xử lý import CSV vào database."""
    
    # Mapping từ tên sheet/file CSV sang table name và model class
    TABLE_MAPPING = {
        "san_pham": ("product", "Product"),
        "khach_hang": ("customer", "Customer"),
        "kh_ncc": ("customer_supplier", None),  # Cần xử lý riêng
        "nha_cung_cap": ("supplier", "Supplier"),
        "dm_kho": ("warehouse", "Warehouse"),
        "dskho": ("warehouse", "Warehouse"),
        "phong_ban": ("department", "Department"),
        "chuc_danh": ("jobtitle", "JobTitle"),
        "nhan_su": ("employee", "Employee"),
        "nhan_vien": ("employee", "Employee"),
        "don_hang": ("salesorder", "SalesOrder"),
        "lenh_sx": ("productionorder", "ProductionOrder"),
        "phieu_nx": ("stockdocument", "StockDocument"),
        "bom_sp": ("bommaterial", "BomMaterial"),
    }
    
    def __init__(self, csv_dir: str | Path = None):
        self.csv_dir = Path(csv_dir) if csv_dir else None
        self._db_session = None
    
    def _get_db_session(self):
        """Lazy load database session."""
        if self._db_session is None:
            from backend.app.core.db import SessionLocal
            self._db_session = SessionLocal()
        return self._db_session
    
    def _close_db_session(self):
        """Đóng database session."""
        if self._db_session:
            self._db_session.close()
            self._db_session = None
    
    def _new_db_session(self):
        """Tạo session mới (khi session cũ bị lỗi)."""
        self._close_db_session()
        return self._get_db_session()
    
    def load_csv(self, csv_path: Path) -> Generator[dict[str, str], None, None]:
        """Đọc file CSV và yield từng dòng dưới dạng dict."""
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row
    
    def import_products(self, csv_path: Path) -> int:
        """Import sản phẩm từ CSV."""
        from backend.app.models.entities import Product
        from sqlalchemy.exc import IntegrityError
        
        db = self._get_db_session()
        count = 0
        skipped = 0
        duplicates = 0
        seen_codes = set()  # Track codes trong batch hiện tại
        
        for row in self.load_csv(csv_path):
            # Map columns - hỗ trợ nhiều tên cột
            code = safe_str(row.get("id") or row.get("ma_sp") or row.get("code"))
            name = safe_str(row.get("ten_sp") or row.get("name"))
            group = safe_str(row.get("loai") or row.get("nhom_cap_1") or row.get("group"))
            main_uom = safe_str(row.get("dvt") or row.get("dvt_chinh") or row.get("main_uom")) or "kg"
            
            if not code or not name or not group:
                skipped += 1
                continue
            
            # Kiểm tra duplicate trong batch hiện tại
            if code in seen_codes:
                duplicates += 1
                continue
            seen_codes.add(code)
            
            # Kiểm tra duplicate trong database
            existing = db.query(Product).filter_by(code=code).first()
            if existing:
                duplicates += 1
                continue
            
            product = Product(
                code=code,
                name=name,
                group=group,
                main_uom=main_uom,
                specification=safe_str(row.get("quy_cach") or row.get("specification")),
                secondary_uom=safe_str(row.get("dvt_quy_doi") or row.get("secondary_uom")),
                conversion_rate=safe_float(row.get("ty_le_quy_doi") or row.get("conversion_rate")),
                shelf_life_days=safe_int(row.get("hsd_ngay") or row.get("shelf_life_days")),
                cost_price=safe_float(row.get("gia_von") or row.get("cost_price")),
            )
            db.add(product)
            count += 1
            
            # Commit theo batch để tránh lỗi memory
            if count % 100 == 0:
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    print(f"   ⚠️  Lỗi duplicate trong batch, rollback...")
        
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            print(f"   ⚠️  Lỗi duplicate khi commit cuối, rollback...")
        
        print(f"✅ Import products: {count} thêm mới, {skipped} bỏ qua, {duplicates} trùng lặp")
        return count
    
    def import_customers(self, csv_path: Path) -> int:
        """Import khách hàng từ CSV."""
        from backend.app.models.entities import Customer
        from sqlalchemy.exc import IntegrityError
        
        db = self._get_db_session()
        count = 0
        skipped = 0
        duplicates = 0
        seen_codes = set()
        
        for row in self.load_csv(csv_path):
            # Lọc chỉ khách hàng (nếu file kh_ncc)
            loai = safe_str(row.get("loai") or "")
            if loai:
                loai_lower = loai.lower()
                if not any(kw in loai_lower for kw in ["khách", "khach", "customer"]):
                    continue
            
            code = safe_str(row.get("id") or row.get("ma_kh") or row.get("code"))
            name = safe_str(row.get("ten_day_du") or row.get("ten_kh") or row.get("name"))
            level = safe_str(row.get("level") or row.get("cap_khach_hang")) or "Khac"
            channel = safe_str(row.get("kenh_npp") or row.get("kenh_ban") or row.get("channel")) or "Khac"
            
            if not code or not name:
                skipped += 1
                continue
            
            if code in seen_codes:
                duplicates += 1
                continue
            seen_codes.add(code)
            
            existing = db.query(Customer).filter_by(code=code).first()
            if existing:
                duplicates += 1
                continue
            
            customer = Customer(
                code=code,
                name=name,
                level=level,
                channel=channel,
                phone=safe_str(row.get("di_dong") or row.get("sdt") or row.get("phone")),
                email=safe_str(row.get("email")),
                address=safe_str(row.get("dia_chi") or row.get("address")),
                credit_limit=safe_float(row.get("cong_no_toi_da") or row.get("credit_limit")),
            )
            db.add(customer)
            count += 1
        
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        print(f"✅ Import customers: {count} thêm mới, {skipped} bỏ qua, {duplicates} trùng lặp")
        return count
    
    def import_suppliers(self, csv_path: Path) -> int:
        """Import nhà cung cấp từ CSV."""
        from backend.app.models.entities import Supplier
        from sqlalchemy.exc import IntegrityError
        
        db = self._get_db_session()
        count = 0
        skipped = 0
        duplicates = 0
        seen_codes = set()
        
        for row in self.load_csv(csv_path):
            # Lọc chỉ nhà cung cấp (nếu file kh_ncc)
            loai = safe_str(row.get("loai") or "")
            if loai:
                loai_lower = loai.lower()
                if not any(kw in loai_lower for kw in ["nhà cung cấp", "nha cung cap", "ncc", "supplier"]):
                    continue
            
            code = safe_str(row.get("id") or row.get("ma_ncc") or row.get("code"))
            name = safe_str(row.get("ten_day_du") or row.get("ten_ncc") or row.get("name"))
            
            if not code or not name:
                skipped += 1
                continue
            
            if code in seen_codes:
                duplicates += 1
                continue
            seen_codes.add(code)
            
            existing = db.query(Supplier).filter_by(code=code).first()
            if existing:
                duplicates += 1
                continue
            
            supplier = Supplier(
                code=code,
                name=name,
                phone=safe_str(row.get("di_dong") or row.get("sdt") or row.get("phone")),
                email=safe_str(row.get("email")),
                address=safe_str(row.get("dia_chi") or row.get("address")),
                rating=safe_float(row.get("danh_gia") or row.get("rating")),
            )
            db.add(supplier)
            count += 1
        
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        print(f"✅ Import suppliers: {count} thêm mới, {skipped} bỏ qua, {duplicates} trùng lặp")
        return count
    
    def import_warehouses(self, csv_path: Path) -> int:
        """Import kho từ CSV."""
        from backend.app.models.entities import Warehouse
        from sqlalchemy.exc import IntegrityError
        
        db = self._get_db_session()
        count = 0
        skipped = 0
        duplicates = 0
        seen_codes = set()
        
        for row in self.load_csv(csv_path):
            code = safe_str(row.get("id") or row.get("ma_kho") or row.get("code"))
            name = safe_str(row.get("ten_kho") or row.get("name"))
            wh_type = safe_str(row.get("loai_kho") or row.get("type")) or "Khac"
            
            if not code or not name:
                skipped += 1
                continue
            
            if code in seen_codes:
                duplicates += 1
                continue
            seen_codes.add(code)
            
            existing = db.query(Warehouse).filter_by(code=code).first()
            if existing:
                duplicates += 1
                continue
            
            warehouse = Warehouse(
                code=code,
                name=name,
                type=wh_type,
                location=safe_str(row.get("vi_tri") or row.get("location")),
            )
            db.add(warehouse)
            count += 1
        
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        print(f"✅ Import warehouses: {count} thêm mới, {skipped} bỏ qua, {duplicates} trùng lặp")
        return count
    
    def import_departments(self, csv_path: Path) -> int:
        """Import phòng ban từ CSV."""
        from backend.app.models.entities import Department
        from sqlalchemy.exc import IntegrityError
        
        db = self._get_db_session()
        count = 0
        skipped = 0
        duplicates = 0
        seen_codes = set()
        
        for row in self.load_csv(csv_path):
            code = safe_str(row.get("id") or row.get("ma_pb") or row.get("code"))
            name = safe_str(row.get("ten_phong_ban") or row.get("ten_pb") or row.get("name"))
            
            if not code or not name:
                skipped += 1
                continue
            
            if code in seen_codes:
                duplicates += 1
                continue
            seen_codes.add(code)
            
            existing = db.query(Department).filter_by(code=code).first()
            if existing:
                duplicates += 1
                continue
            
            department = Department(
                code=code,
                name=name,
            )
            db.add(department)
            count += 1
        
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        print(f"✅ Import departments: {count} thêm mới, {skipped} bỏ qua, {duplicates} trùng lặp")
        return count
    
    def import_employees(self, csv_path: Path) -> int:
        """Import nhân viên từ CSV."""
        from backend.app.models.entities import Employee
        from sqlalchemy.exc import IntegrityError
        
        db = self._get_db_session()
        count = 0
        skipped = 0
        duplicates = 0
        seen_codes = set()
        
        for row in self.load_csv(csv_path):
            code = safe_str(row.get("id") or row.get("ma_nv") or row.get("code"))
            name = safe_str(row.get("ho_ten") or row.get("ten_nv") or row.get("name"))
            
            if not code or not name:
                skipped += 1
                continue
            
            if code in seen_codes:
                duplicates += 1
                continue
            seen_codes.add(code)
            
            existing = db.query(Employee).filter_by(code=code).first()
            if existing:
                duplicates += 1
                continue
            
            employee = Employee(
                code=code,
                name=name,
                department_code=safe_str(row.get("phong_ban_id") or row.get("ma_pb")),
                jobtitle_code=safe_str(row.get("chuc_danh_id") or row.get("ma_cd")),
                phone=safe_str(row.get("dien_thoai") or row.get("sdt") or row.get("phone")),
                email=safe_str(row.get("email")),
                hire_date=safe_date(row.get("ngay_vao_lam") or row.get("hire_date")),
            )
            db.add(employee)
            count += 1
        
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        print(f"✅ Import employees: {count} thêm mới, {skipped} bỏ qua, {duplicates} trùng lặp")
        return count
    
    def import_from_csv(self, csv_path: Path, table_type: str = None) -> int:
        """
        Import data từ một file CSV.
        
        Args:
            csv_path: Path đến file CSV
            table_type: Loại bảng (product, customer, supplier, warehouse, department, employee)
                       Nếu None, sẽ tự động detect từ tên file
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"File CSV không tồn tại: {csv_path}")
        
        # Auto-detect table type từ tên file
        if table_type is None:
            file_stem = csv_path.stem.lower()
            if file_stem in self.TABLE_MAPPING:
                table_type = self.TABLE_MAPPING[file_stem][0]
            else:
                # Thử match một phần
                for key, (tbl, _) in self.TABLE_MAPPING.items():
                    if key in file_stem or file_stem in key:
                        table_type = tbl
                        break
        
        if table_type is None:
            print(f"⚠️  Không xác định được loại bảng cho file: {csv_path.name}")
            return 0
        
        # Xử lý đặc biệt cho file kh_ncc: import cả customer và supplier
        if table_type == "customer_supplier":
            print(f"\n📄 Import {csv_path.name} -> customer + supplier")
            count_cust = self.import_customers(csv_path)
            self._new_db_session()  # Tạo session mới
            count_supp = self.import_suppliers(csv_path)
            return count_cust + count_supp
        
        print(f"\n📄 Import {csv_path.name} -> {table_type}")
        
        # Map table type to import function
        import_funcs = {
            "product": self.import_products,
            "customer": self.import_customers,
            "supplier": self.import_suppliers,
            "warehouse": self.import_warehouses,
            "department": self.import_departments,
            "employee": self.import_employees,
        }
        
        import_func = import_funcs.get(table_type)
        if import_func is None:
            print(f"⚠️  Chưa hỗ trợ import bảng: {table_type}")
            return 0
        
        return import_func(csv_path)
    
    def import_all(self, csv_dir: Path = None) -> dict[str, int]:
        """
        Import tất cả files CSV trong thư mục.
        
        Returns:
            Dict mapping filename -> số records đã import
        """
        csv_dir = Path(csv_dir) if csv_dir else self.csv_dir
        if csv_dir is None:
            raise ValueError("Chưa chỉ định thư mục CSV")
        
        if not csv_dir.exists():
            raise FileNotFoundError(f"Thư mục không tồn tại: {csv_dir}")
        
        print(f"\n📁 Import tất cả CSV từ: {csv_dir}")
        
        results = {}
        csv_files = list(csv_dir.glob("*.csv"))
        
        if not csv_files:
            print("⚠️  Không tìm thấy file CSV nào!")
            return results
        
        print(f"   Tìm thấy {len(csv_files)} files CSV\n")
        
        # Thứ tự import để đảm bảo foreign key
        priority_order = [
            "department", "jobtitle", "warehouse", 
            "product", "customer", "supplier", "employee"
        ]
        
        # Sắp xếp files theo priority
        def get_priority(path: Path) -> int:
            stem = path.stem.lower()
            for key, (tbl, _) in self.TABLE_MAPPING.items():
                if key in stem or stem in key:
                    try:
                        return priority_order.index(tbl)
                    except ValueError:
                        return 100
            return 100
        
        csv_files.sort(key=get_priority)
        
        for csv_file in csv_files:
            try:
                # Tạo session mới cho mỗi file để tránh lỗi session
                self._new_db_session()
                count = self.import_from_csv(csv_file)
                results[csv_file.name] = count
            except Exception as e:
                print(f"⚠️  Lỗi import {csv_file.name}: {e}")
                results[csv_file.name] = 0
        
        self._close_db_session()
        
        print(f"\n" + "="*50)
        print("📊 Kết quả import:")
        total = 0
        for fname, cnt in results.items():
            print(f"   {fname}: {cnt} records")
            total += cnt
        print(f"   TỔNG: {total} records")
        
        return results


# =============================================================================
# PIPELINE: EXPORT + IMPORT
# =============================================================================

def run_pipeline(excel_path: str, output_dir: str = None, sheets: list[str] = None):
    """
    Chạy pipeline hoàn chỉnh: Export Excel -> CSV -> Import DB.
    
    Args:
        excel_path: Đường dẫn đến file Excel
        output_dir: Thư mục chứa CSV (tạm)
        sheets: Danh sách sheets cần xử lý (None = tất cả)
    """
    excel_path = Path(excel_path)
    if output_dir is None:
        output_dir = excel_path.parent / "csv_temp"
    output_dir = Path(output_dir)
    
    print("="*60)
    print("🚀 PIPELINE: Excel -> CSV -> Database")
    print("="*60)
    
    # Step 1: Export Excel to CSV
    print("\n📌 BƯỚC 1: Export Excel sang CSV")
    exporter = ExcelToCsvExporter(excel_path, output_dir)
    exported_files = exporter.export_all(sheets=sheets)
    
    if not exported_files:
        print("❌ Không có file nào được export, dừng pipeline.")
        return
    
    # Step 2: Import CSV to Database
    print("\n📌 BƯỚC 2: Import CSV vào Database")
    importer = CsvToDbImporter(output_dir)
    results = importer.import_all()
    
    print("\n" + "="*60)
    print("✅ PIPELINE HOÀN THÀNH!")
    print("="*60)
    
    return results


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Export Excel sang CSV và Import vào Database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  # Export tất cả sheets ra CSV
  python excel_to_csv_import.py export data/home.xlsx --output-dir ./csv_output
  
  # Export chỉ một số sheets
  python excel_to_csv_import.py export data/home.xlsx --sheets san_pham kh_ncc
  
  # Import từ thư mục CSV
  python excel_to_csv_import.py import ./csv_output --all
  
  # Import một file CSV cụ thể
  python excel_to_csv_import.py import ./csv_output/san_pham.csv --table product
  
  # Pipeline hoàn chỉnh (export + import)
  python excel_to_csv_import.py pipeline data/home.xlsx
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Lệnh cần thực thi")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export Excel sang CSV")
    export_parser.add_argument("excel_path", help="Đường dẫn file Excel (.xlsx)")
    export_parser.add_argument("--output-dir", "-o", help="Thư mục output cho CSV")
    export_parser.add_argument("--sheets", "-s", nargs="+", help="Danh sách sheets cần export")
    export_parser.add_argument("--list-sheets", "-l", action="store_true", help="Liệt kê tên các sheets")
    
    # Import command  
    import_parser = subparsers.add_parser("import", help="Import CSV vào Database")
    import_parser.add_argument("path", help="Đường dẫn file CSV hoặc thư mục chứa CSV")
    import_parser.add_argument("--table", "-t", help="Loại bảng (product, customer, supplier, etc.)")
    import_parser.add_argument("--all", "-a", action="store_true", help="Import tất cả CSV trong thư mục")
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser("pipeline", help="Export Excel + Import Database")
    pipeline_parser.add_argument("excel_path", help="Đường dẫn file Excel (.xlsx)")
    pipeline_parser.add_argument("--output-dir", "-o", help="Thư mục tạm cho CSV")
    pipeline_parser.add_argument("--sheets", "-s", nargs="+", help="Danh sách sheets cần xử lý")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    if args.command == "export":
        exporter = ExcelToCsvExporter(args.excel_path, args.output_dir)
        
        if args.list_sheets:
            sheets = exporter.get_sheet_names()
            print("📋 Danh sách sheets:")
            for i, name in enumerate(sheets, 1):
                print(f"   {i}. {name}")
            return
        
        exporter.export_all(sheets=args.sheets)
    
    elif args.command == "import":
        path = Path(args.path)
        importer = CsvToDbImporter()
        
        if path.is_dir() or args.all:
            importer.csv_dir = path if path.is_dir() else path.parent
            importer.import_all()
        else:
            importer.import_from_csv(path, args.table)
    
    elif args.command == "pipeline":
        run_pipeline(args.excel_path, args.output_dir, args.sheets)


if __name__ == "__main__":
    main()
