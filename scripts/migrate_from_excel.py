"""
Script migrate dữ liệu từ file Excel (home.xlsx) vào PostgreSQL database.

Mapping các sheet trong Excel với các bảng trong database:
- san_pham -> product
- khach_hang -> customer
- nha_cung_cap -> supplier
- dm_kho -> warehouse
- phong_ban -> department
- chuc_danh -> jobtitle
- nhan_su -> employee
- don_hang -> salesorder
- lenh_sx -> productionorder
- phieu_nx -> stockdocument
- bom_sp -> bommaterial
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, date
from typing import Any
import uuid

import pandas as pd
from sqlalchemy.exc import IntegrityError

# Thêm path để import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.core.db import get_session
from backend.app.models.entities import (
    Product,
    Customer,
    Supplier,
    Warehouse,
    Department,
    JobTitle,
    Employee,
    SalesOrder,
    SalesOrderLine,
    ProductionOrder,
    ProductionOrderLine,
    StockDocument,
    StockDocumentLine,
    BomMaterial,
    PricePolicy,
    MaterialPriceHistory,
    ProductionPlanDay,
    BomLabor,
    BomSemiProduct,
)


def safe_str(value: Any) -> str | None:
    """Chuyển đổi giá trị sang string an toàn."""
    if pd.isna(value) or value is None:
        return None
    return str(value).strip() if str(value).strip() else None


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
            # Thử các format phổ biến
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return pd.to_datetime(value).date()
    except (ValueError, TypeError):
        return None


def migrate_products(excel_path: Path, db) -> int:
    """Migrate sản phẩm từ sheet 'san_pham' - chỉ các trường bắt buộc và cần thiết."""
    try:
        df = pd.read_excel(excel_path, sheet_name="san_pham", engine='openpyxl')
        print(f"   Tìm thấy {len(df)} dòng trong sheet 'san_pham'")
    except ValueError:
        print("⚠️  Sheet 'san_pham' không tồn tại, bỏ qua...")
        return 0
    except Exception as e:
        print(f"⚠️  Lỗi khi đọc sheet 'san_pham': {e}")
        return 0

    count = 0
    skipped = 0
    duplicates = 0
    debug_first = True
    seen_codes = set()  # Track codes đã xử lý trong batch này
    
    # Commit theo batch để tránh lỗi memory và dễ debug
    batch_size = 100
    batch_count = 0
    
    for idx, row in df.iterrows():
        # Map theo cấu trúc thực tế: id, ten_sp, loai/nhom_cap_1, cần tìm dvt_chinh
        code = safe_str(row.get("id") or row.get("ma_sp") or row.get("Ma_sp") or row.get("code") or row.get("Code"))
        name = safe_str(row.get("ten_sp") or row.get("Ten_sp") or row.get("Tên SP") or row.get("name") or row.get("Name"))
        # Thử nhiều cột cho group: loai, nhom_cap_1, nhom_cap_2, etc.
        group = safe_str(
            row.get("loai") or row.get("nhom_cap_1") or row.get("nhom_cap_2") or 
            row.get("nhom_sp") or row.get("Nhom_sp") or row.get("group") or row.get("Group")
        )
        # Tìm đơn vị tính - Excel dùng cột 'dvt'
        main_uom = safe_str(
            row.get("dvt") or row.get("DVT") or row.get("dvt_chinh") or row.get("DVT_chinh") or 
            row.get("don_vi_tinh") or row.get("main_uom") or row.get("Main_UOM") or "kg"  # Default to "kg" if not found
        )
        
        # Debug: hiển thị dòng đầu tiên để xem cấu trúc
        if debug_first and len(df) > 0:
            print(f"   Debug - Cột có sẵn: {list(df.columns)[:15]}...")  # Hiển thị 15 cột đầu
            print(f"   Debug - Dòng đầu: code={code}, name={name}, group={group}, uom={main_uom}")
            debug_first = False
        
        # Kiểm tra các trường bắt buộc (uom có default nên không cần check)
        if not code or not name or not group:
            skipped += 1
            continue

        # Kiểm tra duplicate trong batch hiện tại
        if code in seen_codes:
            duplicates += 1
            continue
            
        # Kiểm tra đã tồn tại trong database
        existing = db.query(Product).filter_by(code=code).first()
        if existing:
            duplicates += 1
            continue

        product = Product(
            code=code,
            name=name,
            group=group,
            main_uom=main_uom,
            # Các trường optional - chỉ migrate nếu có
            specification=safe_str(row.get("quy_cach") or row.get("specification")),
            secondary_uom=safe_str(row.get("dvt_quy_doi") or row.get("secondary_uom")),
            conversion_rate=safe_float(row.get("ty_le_quy_doi") or row.get("conversion_rate")),
            batch_spec=safe_str(row.get("quy_cach_me") or row.get("batch_spec")),
            shelf_life_days=safe_int(row.get("hsd_ngay") or row.get("shelf_life_days")),
            cost_price=safe_float(row.get("gia_von") or row.get("cost_price")),
            # status có default trong model
        )
        db.add(product)
        seen_codes.add(code)
        count += 1
        batch_count += 1
        
        # Commit theo batch để tránh lỗi và dễ debug
        if batch_count >= batch_size:
            try:
                db.commit()
                print(f"   ⏳ Đã commit batch: {count} sản phẩm...")
                batch_count = 0
                seen_codes.clear()  # Clear sau mỗi batch
            except IntegrityError as e:
                db.rollback()
                print(f"   ⚠️  Lỗi duplicate trong batch, rollback và tiếp tục...")
                # Xóa các products đã add trong batch này và giảm count
                count -= batch_count
                seen_codes.clear()
                batch_count = 0
                continue

    # Commit phần còn lại
    try:
        if batch_count > 0:
            db.commit()
    except IntegrityError as e:
        db.rollback()
        print(f"   ⚠️  Lỗi duplicate khi commit cuối, rollback...")
        count -= batch_count
    
    if skipped > 0 or duplicates > 0:
        msg = f"✅ Đã migrate {count} sản phẩm"
        if skipped > 0:
            msg += f" (bỏ qua {skipped} dòng thiếu dữ liệu bắt buộc)"
        if duplicates > 0:
            msg += f" (bỏ qua {duplicates} dòng trùng lặp)"
        print(msg)
    else:
        print(f"✅ Đã migrate {count} sản phẩm")
    return count


def migrate_customers(excel_path: Path, db) -> int:
    """Migrate khách hàng từ sheet 'khach_hang' hoặc 'kh_ncc' - chỉ các trường bắt buộc và cần thiết."""
    sheet_names = ["khach_hang", "kh_ncc"]
    df = None
    sheet_name = None
    
    for name in sheet_names:
        try:
            df = pd.read_excel(excel_path, sheet_name=name, engine='openpyxl')
            sheet_name = name
            print(f"📄 Đang đọc sheet '{name}'...")
            print(f"   Tìm thấy {len(df)} dòng trong sheet '{name}'")
            break
        except ValueError:
            continue
        except Exception as e:
            print(f"⚠️  Lỗi khi đọc sheet '{name}': {e}")
            continue
    
    if df is None:
        print("⚠️  Sheet 'khach_hang' hoặc 'kh_ncc' không tồn tại, bỏ qua...")
        return 0

    count = 0
    skipped = 0
    debug_first = True
    
    for _, row in df.iterrows():
        # Map theo cấu trúc thực tế: id, ten_day_du, level, kenh_npp, loai
        # Chỉ migrate nếu loai = "Khách hàng" hoặc tương tự
        loai_raw = safe_str(row.get("loai") or row.get("Loai") or "")
        loai = loai_raw.lower() if loai_raw else ""
        # Match: "khách hàng", "khach hang", "kh", "customer" - dùng cả có dấu và không dấu
        if "khách" not in loai and "khach" not in loai and "customer" not in loai:
            # Bỏ qua nếu không phải khách hàng
            continue
            
        code = safe_str(row.get("id") or row.get("ma_kh") or row.get("Ma_kh") or row.get("code") or row.get("Code"))
        name = safe_str(row.get("ten_day_du") or row.get("ten_kh") or row.get("Ten_kh") or row.get("name") or row.get("Name"))
        level = safe_str(row.get("level") or row.get("Level") or row.get("cap_khach_hang")) or "Khac"
        channel = safe_str(row.get("kenh_npp") or row.get("kenh_ban") or row.get("Kenh_ban") or row.get("channel")) or "Khac"
        
        # Debug: hiển thị dòng đầu tiên
        if debug_first and len(df) > 0:
            print(f"   Debug - Cột có sẵn: {list(df.columns)[:10]}...")
            print(f"   Debug - Dòng đầu: loai={loai}, code={code}, name={name}, level={level}, channel={channel}")
            debug_first = False
        
        # Kiểm tra các trường bắt buộc
        if not code or not name:
            skipped += 1
            continue

        existing = db.query(Customer).filter_by(code=code).first()
        if existing:
            continue

        customer = Customer(
            code=code,
            name=name,
            level=level,
            channel=channel,
            # Các trường optional - dùng di_dong từ Excel
            phone=safe_str(row.get("di_dong") or row.get("so_dien_thoai") or row.get("sdt") or row.get("phone")),
            email=safe_str(row.get("email")),
            address=safe_str(row.get("dia_chi") or row.get("Address") or row.get("address")),
            credit_limit=safe_float(row.get("cong_no_toi_da") or row.get("credit_limit")),
            # status có default trong model
        )
        db.add(customer)
        count += 1

    db.commit()
    if skipped > 0:
        print(f"✅ Đã migrate {count} khách hàng (bỏ qua {skipped} dòng thiếu dữ liệu bắt buộc)")
    else:
        print(f"✅ Đã migrate {count} khách hàng")
    return count


def migrate_suppliers(excel_path: Path, db) -> int:
    """Migrate nhà cung cấp từ sheet 'nha_cung_cap' hoặc 'kh_ncc' - chỉ các trường bắt buộc và cần thiết."""
    sheet_names = ["nha_cung_cap", "kh_ncc"]
    df = None
    sheet_name = None
    
    for name in sheet_names:
        try:
            df = pd.read_excel(excel_path, sheet_name=name, engine='openpyxl')
            sheet_name = name
            print(f"📄 Đang đọc sheet '{name}'...")
            print(f"   Tìm thấy {len(df)} dòng trong sheet '{name}'")
            break
        except ValueError:
            continue
        except Exception as e:
            print(f"⚠️  Lỗi khi đọc sheet '{name}': {e}")
            continue
    
    if df is None:
        print("⚠️  Sheet 'nha_cung_cap' hoặc 'kh_ncc' không tồn tại, bỏ qua...")
        return 0

    count = 0
    skipped = 0
    debug_first = True
    
    for _, row in df.iterrows():
        # Map theo cấu trúc thực tế: id, ten_day_du, loai
        # Chỉ migrate nếu loai = "Nhà cung cấp" hoặc tương tự
        loai_raw = safe_str(row.get("loai") or row.get("Loai") or "")
        loai = loai_raw.lower() if loai_raw else ""
        # Match: "nhà cung cấp", "nha cung cap", "ncc", "supplier" - dùng cả có dấu và không dấu
        if "nhà cung cấp" not in loai and "nha cung cap" not in loai and "ncc" not in loai and "supplier" not in loai:
            # Bỏ qua nếu không phải nhà cung cấp
            continue
            
        code = safe_str(row.get("id") or row.get("ma_ncc") or row.get("Ma_ncc") or row.get("code") or row.get("Code"))
        name = safe_str(row.get("ten_day_du") or row.get("ten_ncc") or row.get("Ten_ncc") or row.get("name") or row.get("Name"))
        
        # Debug: hiển thị dòng đầu tiên
        if debug_first and len(df) > 0:
            print(f"   Debug - Cột có sẵn: {list(df.columns)[:10]}...")
            print(f"   Debug - Dòng đầu: loai={loai}, code={code}, name={name}")
            debug_first = False
        
        # Kiểm tra các trường bắt buộc (chỉ code và name)
        if not code or not name:
            skipped += 1
            continue

        existing = db.query(Supplier).filter_by(code=code).first()
        if existing:
            continue

        supplier = Supplier(
            code=code,
            name=name,
            # Các trường optional - dùng di_dong và dia_chi từ Excel
            phone=safe_str(row.get("di_dong") or row.get("so_dien_thoai") or row.get("sdt") or row.get("phone")),
            email=safe_str(row.get("email")),
            address=safe_str(row.get("dia_chi") or row.get("Address") or row.get("address")),
            rating=safe_float(row.get("danh_gia") or row.get("rating")),
        )
        db.add(supplier)
        count += 1

    db.commit()
    if skipped > 0:
        print(f"✅ Đã migrate {count} nhà cung cấp (bỏ qua {skipped} dòng thiếu dữ liệu bắt buộc)")
    else:
        print(f"✅ Đã migrate {count} nhà cung cấp")
    return count


def migrate_warehouses(excel_path: Path, db) -> int:
    """Migrate kho từ sheet 'dm_kho' hoặc 'DSKho' - chỉ các trường bắt buộc và cần thiết."""
    sheet_names = ["dm_kho", "DSKho"]
    df = None
    sheet_name = None
    
    for name in sheet_names:
        try:
            df = pd.read_excel(excel_path, sheet_name=name, engine='openpyxl')
            sheet_name = name
            print(f"📄 Đang đọc sheet '{name}'...")
            break
        except ValueError:
            continue
        except Exception as e:
            print(f"⚠️  Lỗi khi đọc sheet '{name}': {e}")
            continue
    
    if df is None:
        print("⚠️  Sheet 'dm_kho' hoặc 'DSKho' không tồn tại, bỏ qua...")
        return 0
    
    print(f"   Tìm thấy {len(df)} dòng trong sheet '{sheet_name}'")

    count = 0
    skipped = 0
    debug_first = True
    
    for _, row in df.iterrows():
        # Map theo cấu trúc thực tế từ Excel: id, ten_kho, ten_loai_kho, dia_chi_kho
        code = safe_str(row.get("id") or row.get("ma_kho") or row.get("Ma_kho") or row.get("code") or row.get("Code"))
        name = safe_str(row.get("ten_kho") or row.get("Ten_kho") or row.get("Tên kho") or row.get("name") or row.get("Name"))
        # Type có default là "Kho tổng" nếu không có giá trị
        type_val = safe_str(row.get("ten_loai_kho") or row.get("loai_kho") or row.get("Loai_kho") or row.get("type") or row.get("Type")) or "Kho tổng"
        
        # Debug: hiển thị dòng đầu tiên để xem cấu trúc
        if debug_first and len(df) > 0:
            print(f"   Debug - Cột có sẵn: {list(df.columns)}")
            print(f"   Debug - Dòng đầu: code={code}, name={name}, type={type_val}")
            debug_first = False
        
        # Kiểm tra các trường bắt buộc (chỉ code và name)
        if not code or not name:
            skipped += 1
            if debug_first:
                print(f"   Debug - Dòng bị skip: code={code}, name={name}, type={type_val}")
            continue

        existing = db.query(Warehouse).filter_by(code=code).first()
        if existing:
            if debug_first:
                print(f"   Debug - Kho {code} đã tồn tại, bỏ qua")
            continue

        warehouse = Warehouse(
            code=code,
            name=name,
            type=type_val,
            # Các trường optional - dùng dia_chi_kho từ Excel
            location=safe_str(row.get("dia_chi_kho") or row.get("dia_diem") or row.get("location")),
            note=safe_str(row.get("ghi_chu") or row.get("note")),
        )
        db.add(warehouse)
        count += 1

    db.commit()
    if skipped > 0:
        print(f"✅ Đã migrate {count} kho (bỏ qua {skipped} dòng thiếu dữ liệu bắt buộc)")
    else:
        print(f"✅ Đã migrate {count} kho")
    return count


def migrate_departments(excel_path: Path, db) -> int:
    """Migrate phòng ban từ sheet 'phong_ban' - chỉ các trường bắt buộc."""
    try:
        df = pd.read_excel(excel_path, sheet_name="phong_ban")
    except ValueError:
        print("⚠️  Sheet 'phong_ban' không tồn tại, bỏ qua...")
        return 0

    count = 0
    skipped = 0
    for _, row in df.iterrows():
        code = safe_str(row.get("ma_phong") or row.get("code"))
        name = safe_str(row.get("ten_phong") or row.get("name"))
        
        # Kiểm tra các trường bắt buộc
        if not code or not name:
            skipped += 1
            continue

        existing = db.query(Department).filter_by(code=code).first()
        if existing:
            continue

        department = Department(
            code=code,
            name=name,
        )
        db.add(department)
        count += 1

    db.commit()
    if skipped > 0:
        print(f"✅ Đã migrate {count} phòng ban (bỏ qua {skipped} dòng thiếu dữ liệu bắt buộc)")
    else:
        print(f"✅ Đã migrate {count} phòng ban")
    return count


def migrate_job_titles(excel_path: Path, db) -> int:
    """Migrate chức danh từ sheet 'chuc_danh' - chỉ các trường bắt buộc."""
    try:
        df = pd.read_excel(excel_path, sheet_name="chuc_danh")
    except ValueError:
        print("⚠️  Sheet 'chuc_danh' không tồn tại, bỏ qua...")
        return 0

    count = 0
    skipped = 0
    for _, row in df.iterrows():
        name = safe_str(row.get("ten_chuc_danh") or row.get("name"))
        
        # Kiểm tra trường bắt buộc (chỉ name)
        if not name:
            skipped += 1
            continue

        # Kiểm tra đã tồn tại (không có code, dùng name)
        existing = db.query(JobTitle).filter_by(name=name).first()
        if existing:
            continue

        job_title = JobTitle(
            name=name,
            # Các trường optional
            base_salary=safe_float(row.get("bac_luong_co_ban") or row.get("base_salary")),
        )
        db.add(job_title)
        count += 1

    db.commit()
    if skipped > 0:
        print(f"✅ Đã migrate {count} chức danh (bỏ qua {skipped} dòng thiếu dữ liệu bắt buộc)")
    else:
        print(f"✅ Đã migrate {count} chức danh")
    return count


def migrate_employees(excel_path: Path, db) -> int:
    """Migrate nhân sự từ sheet 'nhan_su' hoặc 'nhan_vien' - chỉ các trường bắt buộc và cần thiết."""
    sheet_names = ["nhan_su", "nhan_vien", "ds_nhan_vien_cty"]
    df = None
    sheet_name = None
    
    for name in sheet_names:
        try:
            df = pd.read_excel(excel_path, sheet_name=name, engine='openpyxl')
            sheet_name = name
            print(f"📄 Đang đọc sheet '{name}'...")
            print(f"   Tìm thấy {len(df)} dòng trong sheet '{name}'")
            break
        except ValueError:
            continue
        except Exception as e:
            print(f"⚠️  Lỗi khi đọc sheet '{name}': {e}")
            continue
    
    if df is None:
        print("⚠️  Sheet 'nhan_su', 'nhan_vien' hoặc 'ds_nhan_vien_cty' không tồn tại, bỏ qua...")
        return 0

    count = 0
    skipped = 0
    debug_first = True
    
    for _, row in df.iterrows():
        # Map theo cấu trúc thực tế: id, ho_va_ten, bo_phan
        code = safe_str(row.get("id") or row.get("ma_nv") or row.get("Ma_nv") or row.get("code") or row.get("Code"))
        full_name = safe_str(row.get("ho_va_ten") or row.get("ho_ten") or row.get("Ho_ten") or row.get("Họ tên") or row.get("name") or row.get("Name") or row.get("full_name"))
        
        # Debug: hiển thị dòng đầu tiên
        if debug_first and len(df) > 0:
            print(f"   Debug - Cột có sẵn: {list(df.columns)[:10]}...")
            print(f"   Debug - Dòng đầu: code={code}, name={full_name}")
            debug_first = False
        
        # Kiểm tra các trường bắt buộc
        if not code or not full_name:
            skipped += 1
            continue

        existing = db.query(Employee).filter_by(code=code).first()
        if existing:
            continue

        # Tìm department từ bo_phan hoặc tạo mới nếu chưa có
        dept_name = safe_str(row.get("bo_phan") or row.get("phong_ban_id") or row.get("ma_phong")) or "Chưa phân loại"
        dept = db.query(Department).filter_by(name=dept_name).first()
        if not dept:
            # Tạo department mới nếu chưa có
            dept_code = dept_name.lower().replace(" ", "_").replace("/", "_")[:50]  # Giới hạn độ dài code
            dept = Department(code=dept_code, name=dept_name)
            db.add(dept)
            db.flush()

        # Tạo job_title mặc định nếu chưa có
        job_title_name = safe_str(row.get("chuc_danh_id") or row.get("ten_chuc_danh") or row.get("phan_quyen")) or "Nhân viên"
        job_title = db.query(JobTitle).filter_by(name=job_title_name).first()
        if not job_title:
            # Tạo job_title mới nếu chưa có
            job_title = JobTitle(name=job_title_name)
            db.add(job_title)
            db.flush()

        join_date = safe_date(row.get("ngay_vao_lam") or row.get("join_date"))
        if not join_date:
            join_date = date.today()

        employee = Employee(
            code=code,
            full_name=full_name,
            department_id=dept.id,
            job_title_id=job_title.id,
            join_date=join_date,
            # Các trường optional
            leave_date=safe_date(row.get("ngay_nghi_viec") or row.get("leave_date")),
            # status có default trong model
        )
        db.add(employee)
        count += 1

    db.commit()
    if skipped > 0:
        print(f"✅ Đã migrate {count} nhân viên (bỏ qua {skipped} dòng thiếu dữ liệu bắt buộc)")
    else:
        print(f"✅ Đã migrate {count} nhân viên")
    return count


def migrate_price_policies(excel_path: Path, db) -> int:
    """Migrate chính sách giá từ sheet 'chinh_sach_gia'."""
    try:
        df = pd.read_excel(excel_path, sheet_name="chinh_sach_gia")
    except ValueError:
        print("⚠️  Sheet 'chinh_sach_gia' không tồn tại, bỏ qua...")
        return 0

    count = 0
    for _, row in df.iterrows():
        product_code = safe_str(row.get("san_pham_id") or row.get("ma_sp") or row.get("product_code"))
        if not product_code:
            continue

        product = db.query(Product).filter_by(code=product_code).first()
        if not product:
            print(f"⚠️  Bỏ qua chính sách giá: sản phẩm {product_code} không tồn tại")
            continue

        # Kiểm tra đã tồn tại (product_id + customer_level + effective_date)
        customer_level = safe_str(row.get("cap_khach_hang") or row.get("customer_level")) or "Khac"
        effective_date = safe_date(row.get("ngay_hieu_luc") or row.get("effective_date")) or date.today()
        
        existing = db.query(PricePolicy).filter_by(
            product_id=product.id,
            customer_level=customer_level,
            effective_date=effective_date
        ).first()
        if existing:
            continue

        price_policy = PricePolicy(
            product_id=product.id,
            customer_level=customer_level,
            price=safe_float(row.get("don_gia") or row.get("price")) or 0,
            effective_date=effective_date,
        )
        db.add(price_policy)
        count += 1

    db.commit()
    print(f"✅ Đã migrate {count} chính sách giá")
    return count


def migrate_material_price_history(excel_path: Path, db) -> int:
    """Migrate lịch sử giá NVL từ sheet 'lich_su_gia_nvl' hoặc 'bang_gia_nvl'."""
    sheet_names = ["lich_su_gia_nvl", "bang_gia_nvl"]
    df = None
    sheet_name = None
    
    for name in sheet_names:
        try:
            df = pd.read_excel(excel_path, sheet_name=name)
            sheet_name = name
            break
        except ValueError:
            continue
    
    if df is None:
        print("⚠️  Sheet 'lich_su_gia_nvl' hoặc 'bang_gia_nvl' không tồn tại, bỏ qua...")
        return 0

    count = 0
    for _, row in df.iterrows():
        material_code = safe_str(row.get("nvl_id") or row.get("ma_nvl") or row.get("material_code"))
        supplier_code = safe_str(row.get("ncc_id") or row.get("ma_ncc") or row.get("supplier_code"))
        
        if not material_code or not supplier_code:
            continue

        material = db.query(Product).filter_by(code=material_code).first()
        supplier = db.query(Supplier).filter_by(code=supplier_code).first()
        
        if not material or not supplier:
            print(f"⚠️  Bỏ qua giá NVL: material {material_code} hoặc supplier {supplier_code} không tồn tại")
            continue

        quoted_date = safe_date(row.get("ngay_bao_gia") or row.get("ngay_ap_dung") or row.get("quoted_date")) or date.today()

        price_history = MaterialPriceHistory(
            material_id=material.id,
            supplier_id=supplier.id,
            price=safe_float(row.get("don_gia") or row.get("don_gia_nhap") or row.get("price")) or 0,
            quoted_date=quoted_date,
            note=safe_str(row.get("ghi_chu") or row.get("note")),
        )
        db.add(price_history)
        count += 1

    db.commit()
    print(f"✅ Đã migrate {count} lịch sử giá NVL")
    return count


def migrate_bom_materials(excel_path: Path, db) -> int:
    """Migrate BOM vật tư từ sheet 'BOM_sx'.
    
    Cấu trúc Excel:
    - id_sp_btp: mã sản phẩm/BTP (product)
    - id_btp_vt: mã BTP/vật tư (material/component)
    - dinh_muc: định mức
    - dvt: đơn vị tính
    - gia_von: giá vốn
    """
    sheet_names = ["BOM_sx", "bom_sp", "BOM"]
    df = None
    sheet_name = None
    
    for name in sheet_names:
        try:
            df = pd.read_excel(excel_path, sheet_name=name, engine='openpyxl')
            sheet_name = name
            print(f"📄 Đang đọc sheet '{name}'...")
            break
        except ValueError:
            continue
        except Exception as e:
            print(f"⚠️  Lỗi khi đọc sheet '{name}': {e}")
            continue
    
    if df is None:
        print("⚠️  Sheet 'BOM_sx' hoặc 'bom_sp' không tồn tại, bỏ qua...")
        return 0
    
    print(f"   Tìm thấy {len(df)} dòng trong sheet '{sheet_name}'")

    count = 0
    skipped = 0
    not_found = 0
    debug_first = True
    
    for _, row in df.iterrows():
        # Map theo cấu trúc Excel: id_sp_btp là sản phẩm, id_btp_vt là thành phần
        product_code = safe_str(row.get("id_sp_btp") or row.get("san_pham_id") or row.get("ma_sp") or row.get("product_code"))
        material_code = safe_str(row.get("id_btp_vt") or row.get("nvl_id") or row.get("ma_nvl") or row.get("material_code"))
        
        # Debug dòng đầu
        if debug_first and len(df) > 0:
            print(f"   Debug - Cột có sẵn: {list(df.columns)}")
            print(f"   Debug - Dòng đầu: product={product_code}, material={material_code}")
            debug_first = False
        
        if not product_code or not material_code:
            skipped += 1
            continue

        product = db.query(Product).filter_by(code=product_code).first()
        material = db.query(Product).filter_by(code=material_code).first()
        
        if not product or not material:
            not_found += 1
            continue

        # Kiểm tra đã tồn tại
        existing = db.query(BomMaterial).filter_by(
            product_id=product.id,
            material_id=material.id
        ).first()
        if existing:
            continue

        bom = BomMaterial(
            product_id=product.id,
            material_id=material.id,
            quantity=safe_float(row.get("dinh_muc") or row.get("so_luong") or row.get("quantity")) or 0,
            uom=safe_str(row.get("dvt") or row.get("don_vi") or row.get("uom")) or "kg",
            cost=safe_float(row.get("gia_von") or row.get("cost")),
            effective_date=safe_date(row.get("ngay_tao") or row.get("ngay_hieu_luc") or row.get("effective_date")),
        )
        db.add(bom)
        count += 1

    db.commit()
    msg = f"✅ Đã migrate {count} BOM vật tư"
    if skipped > 0:
        msg += f" (bỏ qua {skipped} dòng thiếu dữ liệu)"
    if not_found > 0:
        msg += f" (bỏ qua {not_found} dòng không tìm thấy SP/NVL)"
    print(msg)
    return count


def migrate_sales_orders(excel_path: Path, db) -> int:
    """Migrate đơn hàng từ sheet 'don_hang' và 'don_hang_ct'."""
    try:
        df_orders = pd.read_excel(excel_path, sheet_name="don_hang")
    except ValueError:
        print("⚠️  Sheet 'don_hang' không tồn tại, bỏ qua...")
        return 0

    try:
        df_lines = pd.read_excel(excel_path, sheet_name="don_hang_ct")
    except ValueError:
        print("⚠️  Sheet 'don_hang_ct' không tồn tại, chỉ migrate đơn hàng không có chi tiết...")
        df_lines = None

    count = 0
    for _, row in df_orders.iterrows():
        code = safe_str(row.get("ma_dh") or row.get("code"))
        if not code:
            continue

        existing = db.query(SalesOrder).filter_by(code=code).first()
        if existing:
            continue

        customer_code = safe_str(row.get("khach_hang_id") or row.get("ma_kh") or row.get("customer_code"))
        if not customer_code:
            continue

        customer = db.query(Customer).filter_by(code=customer_code).first()
        if not customer:
            print(f"⚠️  Bỏ qua đơn hàng {code}: khách hàng {customer_code} không tồn tại")
            continue

        order = SalesOrder(
            code=code,
            customer_id=customer.id,
            order_date=safe_date(row.get("ngay_dat_hang") or row.get("order_date")) or date.today(),
            delivery_date=safe_date(row.get("han_giao_hang") or row.get("delivery_date")) or date.today(),
            status=safe_str(row.get("trang_thai") or row.get("status")) or "new",
            total_amount=safe_float(row.get("tong_tien") or row.get("total_amount")) or 0,
            payment_status=safe_str(row.get("thanh_toan") or row.get("payment_status")) or "unpaid",
            note=safe_str(row.get("ghi_chu") or row.get("note")),
        )
        db.add(order)
        db.flush()  # Để lấy ID

        # Migrate chi tiết đơn hàng
        if df_lines is not None:
            order_lines = df_lines[df_lines.get("don_hang_id") == code]
            if order_lines.empty:
                order_lines = df_lines[df_lines.get("ma_dh") == code]
            
            for _, line_row in order_lines.iterrows():
                product_code = safe_str(line_row.get("san_pham_id") or line_row.get("ma_sp") or line_row.get("product_code"))
                if not product_code:
                    continue

                product = db.query(Product).filter_by(code=product_code).first()
                if not product:
                    continue

                line = SalesOrderLine(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=safe_str(line_row.get("ten_sp") or line_row.get("product_name")) or product.name,
                    sales_spec=safe_str(line_row.get("quy_cach") or line_row.get("sales_spec")),
                    uom=safe_str(line_row.get("dvt") or line_row.get("uom")) or product.main_uom,
                    quantity=safe_float(line_row.get("so_luong") or line_row.get("quantity")) or 0,
                    unit_price=safe_float(line_row.get("don_gia") or line_row.get("unit_price")) or 0,
                    line_amount=safe_float(line_row.get("thanh_tien") or line_row.get("line_amount")) or 0,
                    batch_spec=safe_str(line_row.get("quy_cach_me") or line_row.get("batch_spec")),
                )
                db.add(line)

        count += 1

    db.commit()
    print(f"✅ Đã migrate {count} đơn hàng")
    return count


def migrate_production_orders(excel_path: Path, db) -> int:
    """Migrate lệnh sản xuất từ sheet 'lenh_sx' và 'lenh_sx_ct'."""
    try:
        df_orders = pd.read_excel(excel_path, sheet_name="lenh_sx")
    except ValueError:
        print("⚠️  Sheet 'lenh_sx' không tồn tại, bỏ qua...")
        return 0

    try:
        df_lines = pd.read_excel(excel_path, sheet_name="lenh_sx_ct")
    except ValueError:
        print("⚠️  Sheet 'lenh_sx_ct' không tồn tại, chỉ migrate lệnh sản xuất không có chi tiết...")
        df_lines = None

    count = 0
    for _, row in df_orders.iterrows():
        business_id = safe_str(row.get("lsx_id") or row.get("business_id") or row.get("code"))
        if not business_id:
            continue

        existing = db.query(ProductionOrder).filter_by(business_id=business_id).first()
        if existing:
            continue

        product_code = safe_str(row.get("san_pham_id") or row.get("ma_sp") or row.get("product_code"))
        if not product_code:
            continue

        product = db.query(Product).filter_by(code=product_code).first()
        if not product:
            print(f"⚠️  Bỏ qua LSX {business_id}: sản phẩm {product_code} không tồn tại")
            continue

        order = ProductionOrder(
            business_id=business_id,
            production_date=safe_date(row.get("ngay_san_xuat") or row.get("production_date")) or date.today(),
            order_type=safe_str(row.get("loai_lenh") or row.get("order_type")) or "SP",
            product_id=product.id,
            product_name=safe_str(row.get("ten_sp") or row.get("product_name")) or product.name,
            planned_qty=safe_float(row.get("sl_len_lsx") or row.get("planned_qty")) or 0,
            completed_qty=safe_float(row.get("sl_hoan_thanh") or row.get("completed_qty")) or 0,
            expected_diff_qty=safe_float(row.get("du_kien_thua_thieu") or row.get("expected_diff_qty")) or 0,
            status=safe_str(row.get("trang_thai") or row.get("status")) or "new",
            note=safe_str(row.get("ghi_chu") or row.get("note")),
        )
        db.add(order)
        db.flush()

        # Migrate chi tiết lệnh sản xuất
        if df_lines is not None:
            order_lines = df_lines[df_lines.get("lenh_sx_id") == business_id]
            if order_lines.empty:
                order_lines = df_lines[df_lines.get("lsx_id") == business_id]
            
            for _, line_row in order_lines.iterrows():
                line_product_code = safe_str(line_row.get("san_pham_id") or line_row.get("ma_sp") or line_row.get("product_code"))
                if not line_product_code:
                    continue

                line_product = db.query(Product).filter_by(code=line_product_code).first()
                if not line_product:
                    continue

                line = ProductionOrderLine(
                    production_order_id=order.id,
                    product_id=line_product.id,
                    product_name=safe_str(line_row.get("ten_sp") or line_row.get("product_name")) or line_product.name,
                    batch_spec=safe_str(line_row.get("quy_cach_me") or line_row.get("batch_spec")),
                    batch_count=safe_float(line_row.get("so_me") or line_row.get("batch_count")),
                    uom=safe_str(line_row.get("dvt") or line_row.get("uom")) or line_product.main_uom,
                    planned_qty=safe_float(line_row.get("so_luong_ke_hoach") or line_row.get("planned_qty")) or 0,
                    actual_qty=safe_float(line_row.get("so_luong_thuc_te") or line_row.get("actual_qty")) or 0,
                    expected_loss=safe_float(line_row.get("hao_hut_du_kien") or line_row.get("expected_loss")),
                    actual_loss=safe_float(line_row.get("hao_hut_thuc_te") or line_row.get("actual_loss")),
                    note=safe_str(line_row.get("ghi_chu") or line_row.get("note")),
                )
                db.add(line)

        count += 1

    db.commit()
    print(f"✅ Đã migrate {count} lệnh sản xuất")
    return count


def migrate_stock_documents(excel_path: Path, db) -> int:
    """Migrate phiếu nhập/xuất kho từ sheet 'phieu_nx' và 'phieu_nx_ct'."""
    try:
        df_docs = pd.read_excel(excel_path, sheet_name="phieu_nx")
    except ValueError:
        print("⚠️  Sheet 'phieu_nx' không tồn tại, bỏ qua...")
        return 0

    try:
        df_lines = pd.read_excel(excel_path, sheet_name="phieu_nx_ct")
    except ValueError:
        print("⚠️  Sheet 'phieu_nx_ct' không tồn tại, chỉ migrate phiếu không có chi tiết...")
        df_lines = None

    count = 0
    for _, row in df_docs.iterrows():
        code = safe_str(row.get("ma_phieu") or row.get("code"))
        if not code:
            continue

        existing = db.query(StockDocument).filter_by(code=code).first()
        if existing:
            continue

        warehouse_code = safe_str(row.get("kho_id") or row.get("ma_kho") or row.get("warehouse_code"))
        if not warehouse_code:
            continue

        warehouse = db.query(Warehouse).filter_by(code=warehouse_code).first()
        if not warehouse:
            print(f"⚠️  Bỏ qua phiếu {code}: kho {warehouse_code} không tồn tại")
            continue

        doc_type = safe_str(row.get("loai_nx") or row.get("doc_type"))
        if doc_type:
            doc_type = "N" if doc_type.upper().startswith("N") else "X"
        else:
            doc_type = "N"

        document = StockDocument(
            code=code,
            posting_date=safe_date(row.get("ngay_phieu") or row.get("posting_date")) or date.today(),
            doc_type=doc_type,
            warehouse_id=warehouse.id,
            storekeeper=safe_str(row.get("thu_kho") or row.get("storekeeper")),
            partner_name=safe_str(row.get("nguoi_giao_nhan") or row.get("partner_name")),
            description=safe_str(row.get("dien_giai") or row.get("description")),
            qr_code_url=safe_str(row.get("qr_code") or row.get("qr_code_url")),
        )
        db.add(document)
        db.flush()

        # Migrate chi tiết phiếu
        if df_lines is not None:
            doc_lines = df_lines[df_lines.get("ma_phieu") == code]
            if doc_lines.empty:
                doc_lines = df_lines[df_lines.get("phieu_nx_id") == code]
            
            for _, line_row in doc_lines.iterrows():
                product_code = safe_str(line_row.get("san_pham_id") or line_row.get("ma_sp") or line_row.get("product_code"))
                if not product_code:
                    continue

                product = db.query(Product).filter_by(code=product_code).first()
                if not product:
                    continue

                quantity = safe_float(line_row.get("so_luong") or line_row.get("quantity")) or 0
                signed_qty = quantity if doc_type == "N" else -quantity

                line = StockDocumentLine(
                    document_id=document.id,
                    product_id=product.id,
                    product_name=safe_str(line_row.get("ten_sp") or line_row.get("product_name")) or product.name,
                    batch_spec=safe_str(line_row.get("quy_cach") or line_row.get("batch_spec")),
                    mfg_date=safe_date(line_row.get("ngay_sx") or line_row.get("mfg_date")),
                    exp_date=safe_date(line_row.get("hsd") or line_row.get("exp_date")),
                    uom=safe_str(line_row.get("dvt") or line_row.get("uom")) or product.main_uom,
                    quantity=quantity,
                    signed_qty=signed_qty,
                )
                db.add(line)

        count += 1

    db.commit()
    print(f"✅ Đã migrate {count} phiếu nhập/xuất kho")
    return count


def migrate_production_plan_days(excel_path: Path, db) -> int:
    """Migrate kế hoạch sản xuất ngày từ sheet 'khsx_ngay'."""
    try:
        df = pd.read_excel(excel_path, sheet_name="khsx_ngay")
    except ValueError:
        print("⚠️  Sheet 'khsx_ngay' không tồn tại, bỏ qua...")
        return 0

    count = 0
    for _, row in df.iterrows():
        product_code = safe_str(row.get("san_pham_id") or row.get("ma_sp") or row.get("product_code"))
        if not product_code:
            continue

        product = db.query(Product).filter_by(code=product_code).first()
        if not product:
            print(f"⚠️  Bỏ qua KHSX: sản phẩm {product_code} không tồn tại")
            continue

        production_date = safe_date(row.get("ngay_san_xuat") or row.get("production_date")) or date.today()

        # Kiểm tra đã tồn tại
        existing = db.query(ProductionPlanDay).filter_by(
            product_id=product.id,
            production_date=production_date
        ).first()
        if existing:
            continue

        plan = ProductionPlanDay(
            production_date=production_date,
            product_id=product.id,
            planned_qty=safe_float(row.get("so_luong_ke_hoach") or row.get("planned_qty")) or 0,
            ordered_qty=safe_float(row.get("so_luong_da_lenh") or row.get("ordered_qty")) or 0,
            remaining_qty=safe_float(row.get("so_luong_con_thieu") or row.get("remaining_qty")) or 0,
            capacity_max=safe_float(row.get("cong_suat_max") or row.get("capacity_max")) or 0,
        )
        db.add(plan)
        count += 1

    db.commit()
    print(f"✅ Đã migrate {count} kế hoạch sản xuất ngày")
    return count


def main():
    """Chạy migration từ Excel file."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate dữ liệu từ Excel file (home.xlsx) vào PostgreSQL database."
    )
    parser.add_argument(
        "--excel-path",
        default="appsheet_docs_old/appsheet_data/home.xlsx",
        help="Đường dẫn tới file Excel",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Bỏ qua các bản ghi đã tồn tại (mặc định: True)",
    )

    # Parse arguments
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        print(f"❌ File không tồn tại: {excel_path}")
        return

    print(f"📂 Đang đọc file Excel: {excel_path}")
    
    # Liệt kê các sheet có sẵn (chỉ đọc metadata, không load toàn bộ data)
    try:
        print("⏳ Đang mở file Excel để liệt kê sheets (có thể mất vài giây)...")
        xls = pd.ExcelFile(excel_path, engine='openpyxl')
        print(f"📋 Tìm thấy {len(xls.sheet_names)} sheets: {', '.join(xls.sheet_names[:10])}{'...' if len(xls.sheet_names) > 10 else ''}")
        xls.close()  # Đóng file ngay sau khi đọc metadata
    except Exception as e:
        print(f"❌ Lỗi đọc file Excel: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n🚀 Bắt đầu migration...\n")

    with get_session() as db:
        total = 0
        
        # Migrate theo thứ tự phụ thuộc
        print("📦 Migrate danh mục cơ bản...")
        total += migrate_warehouses(excel_path, db)
        # Departments và JobTitles sẽ được tạo tự động trong migrate_employees nếu cần
        # Nhưng vẫn thử migrate nếu có sheet riêng
        total += migrate_departments(excel_path, db)
        total += migrate_job_titles(excel_path, db)
        total += migrate_products(excel_path, db)
        total += migrate_customers(excel_path, db)
        total += migrate_suppliers(excel_path, db)
        total += migrate_employees(excel_path, db)
        
        print("\n💰 Migrate giá và BOM...")
        total += migrate_price_policies(excel_path, db)
        total += migrate_material_price_history(excel_path, db)
        total += migrate_bom_materials(excel_path, db)
        
        print("\n📋 Migrate đơn hàng và sản xuất...")
        total += migrate_sales_orders(excel_path, db)
        total += migrate_production_orders(excel_path, db)
        total += migrate_production_plan_days(excel_path, db)
        
        print("\n📦 Migrate kho...")
        total += migrate_stock_documents(excel_path, db)

    print(f"\n✅ Hoàn thành! Đã migrate tổng cộng {total} bản ghi.")


if __name__ == "__main__":
    main()

