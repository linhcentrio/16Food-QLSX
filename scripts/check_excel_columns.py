"""Script kiểm tra tên cột trong các sheet Excel."""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

excel_path = Path("appsheet_docs_old/appsheet_data/home.xlsx")

# Kiểm tra các sheet quan trọng
sheets_to_check = {
    "DSKho": ["ma_kho", "ten_kho", "loai_kho"],
    "san_pham": ["ma_sp", "ten_sp", "nhom_sp", "dvt_chinh"],
    "kh_ncc": ["ma_kh", "ten_kh", "cap_khach_hang", "kenh_ban"],
    "nhan_vien": ["ma_nv", "ho_ten", "phong_ban_id", "chuc_danh_id"],
}

print("🔍 Kiểm tra tên cột trong các sheet Excel...\n")

for sheet_name, expected_cols in sheets_to_check.items():
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, engine='openpyxl', nrows=5)
        print(f"📄 Sheet: {sheet_name}")
        print(f"   Số dòng: {len(df)}")
        print(f"   Tên cột thực tế: {list(df.columns)}")
        print(f"   Cột mong đợi: {expected_cols}")
        
        # Kiểm tra xem có cột nào khớp không
        matching = [col for col in expected_cols if col in df.columns]
        if matching:
            print(f"   ✅ Khớp: {matching}")
        else:
            print(f"   ❌ Không có cột nào khớp!")
        
        # Hiển thị vài dòng đầu
        if len(df) > 0:
            print(f"   Dữ liệu mẫu (dòng đầu):")
            for col in df.columns[:5]:  # Chỉ hiển thị 5 cột đầu
                val = df.iloc[0][col] if len(df) > 0 else None
                print(f"      {col}: {val}")
        print()
    except Exception as e:
        print(f"❌ Lỗi khi đọc sheet '{sheet_name}': {e}\n")

