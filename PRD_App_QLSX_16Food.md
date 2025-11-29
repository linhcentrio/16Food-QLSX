# PRODUCT REQUIREMENTS DOCUMENT (PRD)
## HỆ THỐNG QUẢN LÝ SẢN XUẤT VÀ KHO 16FOOD

**Phiên bản:** 1.0  
**Ngày:** 29/11/2025  
**Tác giả:** Product Team  
**Trạng thái:** Đang phát triển  

---

## 1. TỔNG QUAN DỰ ÁN

### 1.1. Bối cảnh kinh doanh

Công ty 16Food là doanh nghiệp sản xuất thực phẩm với quy mô trung bình, đang đối mặt với các thách thức:

- **Quản lý sản xuất phức tạp:** Nhiều công đoạn từ nguyên vật liệu (NVL) → bán thành phẩm (BTP) → sản phẩm cuối cùng
- **Theo dõi tồn kho khó khăn:** Cần quản lý đa loại kho (NVL, BTP, thành phẩm) với định mức và hạn sử dụng khác nhau
- **Tích hợp dữ liệu phân mảnh:** Dữ liệu đang nằm ở nhiều hệ thống (MISA, Excel, các hệ thống khác nhau)
- **Báo cáo thủ công:** Tốn thời gian汇总 báo cáo sản xuất, kho, doanh thu

### 1.2. Mục tiêu dự án

Xây dựng hệ thống quản lý sản xuất và kho toàn diện trên nền tảng web hiện đại (Robyn API + HTMX), giải quyết các vấn đề:

1. **Tích hợp dữ liệu:** Đồng bộ thông tin từ kế hoạch sản xuất đến xuất kho, báo cáo
2. **Tự động hóa:** Giảm 80% công việc thủ công qua automation backend
3. **Real-time tracking:** Theo dõi tồn kho, tiến độ sản xuất theo thời gian thực
4. **Phân quyền chuyên sâu:** Quản lý truy cập theo phòng ban, chức danh
5. **Reporting hiệu quả:** Báo cáo đa chiều, tự động cập nhật

### 1.3. Scope của dự án

**In Scope:**
- Module Quản lý Sản xuất (QLSX)
- Module Quản lý Kho 
- Module Quản lý Đơn hàng
- Module CRM cơ bản
- Module Hành chính Nhân sự
- Dashboard và Báo cáo tự động

**Out of Scope:**
- Quản lý tài chính kế toán
- Hệ thống ERP hoàn chỉnh
- Mobile app native

---

## 2. KIẾN TRÚC HỆ THỐNG

### 2.1. Architecture Overview

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   HTMX         │         │   Robyn API     │         │  PostgreSQL    │
│   (Frontend)   │◄───────►│   (Backend)     │◄───────►│   (Database)   │
│   HTML/CSS/JS  │  HTTP   │   Python        │  SQL    │                │
└─────────────────┘         └──────────────────┘         └─────────────────┘
        │                           │                           │
        │                           │                           │
        ▼                           ▼                           ▼
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Web Browser  │         │   Services &     │         │   Reports &     │
│   (Client)     │         │   Integrations   │         │   Analytics     │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

### 2.2. Technology Stack

**Frontend:** HTMX + HTML/CSS/JavaScript
- Web interface responsive
- HTMX cho dynamic content updates
- Forms & Views với server-side rendering
- Security & Permissions
- Progressive enhancement

**Backend:** Robyn (Python) với SQLAlchemy
- RESTful API endpoints
- Business logic automation
- Data processing
- Integration workflows
- Error handling & logging

**Database:** PostgreSQL
- Master data tables
- Transaction logs
- Reporting views
- Data validation rules
- Relationships & constraints

**Integrations:**
- Email notifications
- Telegram notifications
- QR Code generation
- QuickChart API (cần cấu hình)

---

## 3. CÁC MODULE CHỨC NĂNG

### 3.1. Module Quản lý Sản xuất (QLSX)

**Trạng thái Backend:** ✅ Đã hoàn thành - API endpoints đã implement trong `backend/app/api/production.py` và `backend/app/api/bom.py`

#### 3.1.1. Lệnh Sản Xuất (LSX)
**Mục tiêu:** Quản lý và theo dõi các lệnh sản xuất từ đơn hàng

**Features:**
- **Tạo LSX tự động:** Tổng hợp từ đơn hàng theo ngày sản xuất
- **Quản lý BOM:** Định mức vật tư, nhân công cho mỗi sản phẩm
- **Theo dõi tiến độ:** Trạng thái: Mới → Đang SX → Hoàn thành → Đã nhập kho
- **QR Code integration:** Tạo QR cho mỗi LSX để tracking
- **Split LSX:** Tách LSX khi vượt công suất ngày

**Data Models:**
```sql
lenh_sx {
  id: string (primary key)
  lsx_id: string (business key)
  ngay_san_xuat: date
  loai_lenh: enum [Sản phẩm, Bán thành phẩm]
  san_pham_id: foreign key → san_pham (hoặc btp_id nếu là BTP)
  ten_sp: string
  sl_len_lsx: number
  sl_hoan_thanh: number
  du_kien_thua_thieu: number
  trang_thai: enum [Mới, Đang SX, Hoàn thành, Đã NK]
  ghi_chu: text
  created_at: timestamp
  updated_at: timestamp
}
```

**Data model chi tiết LSX & liên quan:**

```sql
lenh_sx_ct {
  id: string (primary key)
  lenh_sx_id: foreign key → lenh_sx
  san_pham_id: foreign key → san_pham
  ten_sp: string
  quy_cach_me: string         -- quy cách mẻ sản xuất (kg/mẻ, cái/mẻ)
  so_me: number               -- số mẻ cần chạy
  dvt: string
  so_luong_ke_hoach: number   -- SL kế hoạch theo đơn hàng
  so_luong_thuc_te: number    -- SL thực tế hoàn thành
  hao_hut_du_kien: number
  hao_hut_thuc_te: number
  ghi_chu: text
}

san_pham {
  id: string (primary key)
  ma_sp: string (business key, unique)
  ten_sp: string
  nhom_sp: enum [NVL, BTP, Thành phẩm, Phụ liệu]
  quy_cach: string
  dvt_chinh: string
  dvt_quy_doi: string
  ty_le_quy_doi: number
  quy_cach_me: string        -- kg/mẻ, cái/mẻ
  hsd_ngay: number           -- số ngày HSD kể từ ngày SX
  trang_thai: enum [Đang dùng, Ngưng dùng]
}

khsx_ngay {
  id: string (primary key)
  ngay_san_xuat: date
  san_pham_id: foreign key → san_pham
  so_luong_ke_hoach: number
  so_luong_da_lenh: number
  so_luong_con_thieu: number
  cong_suat_max: number      -- công suất tối đa/ngày
}
```

#### 3.1.2. BOM và Định mức
**Mục tiêu:** Quản lý định mức nguyên vật liệu và nhân công

**Features:**
- **BOM vật tư:** Định mức NVL cho sản phẩm/BTP
- **BOM nhân công:** Định mức thời gian, loại nhân công
- **Version control:** Quản lý thay đổi BOM theo thời gian
- **Cost calculation:** Tự động tính giá vốn khi thay đổi giá NVL

**Data Models:**
```sql
bom_sp {
  id: string
  san_pham_id: foreign key
  nvl_id: foreign key → san_pham
  so_luong: number
  don_vi: string             -- kg, g, lít...
  gia_von: number
  ngay_hieu_luc: date
}

bom_nhan_cong {
  id: string
  san_pham_id: foreign key
  thiet_bi: string
  loai_nhan_cong: string
  so_luong: number
  thoi_gian: number (phút)
  don_gia: number
}

bom_btp {
  id: string
  san_pham_btp_id: foreign key → san_pham   -- BTP
  thanh_phan_btp_id: foreign key → san_pham -- BTP/TP khác
  so_luong: number
  don_vi: string
  thu_tu_cong_doan: number
}
```

**Data model chi tiết BOM & giá vốn:**

```sql
bang_gia_nvl {
  id: string
  nvl_id: foreign key → san_pham
  ncc_id: foreign key → nha_cung_cap
  don_gia_nhap: number
  ngay_ap_dung: date
  ghi_chu: text
}

bang_gia_btp_sp {
  id: string
  san_pham_id: foreign key → san_pham
  gia_von_bom: number         -- giá vốn tính từ BOM
  gia_ban_de_xuat: number
  ngay_tinh_gia: date
}
```
```

#### 3.1.3. Kế hoạch Sản Xuất
**Mục tiêu:** Lập kế hoạch sản xuất dựa trên đơn hàng và tồn kho

**Features:**
- **KHSX tự động:** Từ đơn hàng → BTP → NVL
- **Capacity planning:** Kiểm tra công suất nhà máy
- **Material requirement:** Tính toán NVL cần thiết
- **Production scheduling:** Phân bổ sản xuất theo ngày

**Business Logic (tổng quan):**

```text
1. Tổng hợp nhu cầu sản phẩm từ đơn_hang_ct trong khoảng ngày giao hàng
2. Trừ đi tồn kho BTP/thành phẩm hiện có
3. Quy đổi ra số mẻ cần SX dựa trên quy_cach_me của từng sản phẩm
4. Sinh bản ghi khsx_ngay theo từng ngày SX, tôn trọng công_suat_max
5. Từ kế hoạch, sinh lenh_sx + lenh_sx_ct tương ứng
6. Từ lenh_sx, tính nhu cầu NVL/BTP theo BOM_sp, BOM_btp → bảng dự trù NVL
```

### 3.2. Module Quản lý Kho

**Trạng thái Backend:** ✅ Đã hoàn thành - API endpoints đã implement trong `backend/app/api/inventory.py` và `backend/app/api/inventory_analysis.py`

#### 3.2.1. Quản lý Phiếu Nhập/Xuất Kho
**Mục tiêu:** Quản lý các giao dịch kho một cách hệ thống

**Features:**
- **Tạo phiếu nhập:**
  - Nhập kho theo LSX (tự động)
  - Nhập kho kiểm kê
  - Nhập kho trả hàng
- **Tạo phiếu xuất:**
  - Xuất kho sản xuất (tự động)
  - Xuất kho bán hàng
  - Xuất kho hao hụt
- **QR Code scanning:** Quét QR LSX để nhập kho nhanh
- **Real-time validation:** Kiểm tra tồn kho trước khi xuất
- **Auto calculation:** Tự động tính thành tiền

**Data Models:**
```sql
phieu_nx {
  id: string (primary key)
  ma_phieu: string (PNxxxx/PXxxxx)
  ngay_phieu: date
  loai_nx: enum [Nhập, Xuất]
  kho_id: foreign key → DSKho
  thu_kho: string
  nguoi_giao_nhan: string
  dien_giai: text
  qr_code: url
  file_phieu: attachment
  created_at: timestamp
}

phieu_nx_ct {
  id: string
  ma_phieu: foreign key → phieu_nx
  san_pham_id: foreign key → san_pham
  ten_sp: string
  quy_cach: string           -- thông tin quy cách lô/mẻ
  ngay_sx: date
  hsd: date
  dvt: string
  so_luong: number
  sl_nx: number (dương cho nhập, âm cho xuất)
}
```

#### 3.2.2. Tồn kho & Kiểm kê
**Mục tiêu:** Theo dõi tồn kho theo thời gian thực và kiểm kê định kỳ

**Features:**
- **Real-time inventory:** Cập nhật tồn tự động khi có giao dịch
- **Multi-warehouse:** Quản lý tồn theo từng kho
- **Expiry tracking:** Theo dõi hạn sử dụng
- **Stock count:** Tự động tạo phiếu điều chỉnh sau kiểm kê
- **Low stock alert:** Thông báo khi tồn dưới mức tối thiểu
- **Dashboard:** Slicer lọc theo thời gian, kho, sản phẩm

**Business Logic:**
```
Tồn cuối kỳ = Tồn đầu kỳ + Nhập trong kỳ - Xuất trong kỳ
Tồn kho = SUM(sl_nx) WHERE san_pham_id = [id]
```

**Data model chi tiết Kho & tồn kho:**

```sql
dm_kho {
  id: string (primary key)
  ma_kho: string (unique)
  ten_kho: string
  loai_kho: enum [NVL, BTP, TP, Khác]
  dia_diem: string
  ghi_chu: text
}

ton_kho_song {
  san_pham_id: foreign key → san_pham
  kho_id: foreign key → dm_kho
  tong_sl_nhap: number
  tong_sl_xuat: number
  ton_hien_tai: number        -- = tong_sl_nhap - tong_sl_xuat
  gia_tri_ton: number
}

kiem_ke {
  id: string
  ma_kk: string
  kho_id: foreign key → dm_kho
  ngay_kk: date
  trang_thai: enum [Nháp, Đã khóa]
}

kiem_ke_ct {
  id: string
  ma_kk: foreign key → kiem_ke
  san_pham_id: foreign key → san_pham
  ton_so_sach: number
  ton_thuc_te: number
  chenhlech: number
  da_tao_phieu_dc: boolean
}
```

#### 3.2.3. Reporting Kho
**Mục tiêu:** Cung cấp báo cáo quản trị kho đầy đủ

**Features:**
- **Báo cáo NH-XUÂ-TỒN:** Theo khoảng thời gian, kho, sản phẩm
- **Phiếu kiểm kê:** Tự động tạo file Excel từ template
- **Báo cáo hao hụt:** Thống kê hao hụt NVL trong sản xuất
- **ABC Analysis:** Phân loại sản phẩm theo giá trị tồn kho
- **Turnover analysis:** Tính vòng quay hàng tồn kho

**Báo cáo & file template chính:**
- **BC_NXT:** Sinh từ bảng `phieu_nx_ct` + `phieu_nx`, nhóm theo thời gian/kho/sản phẩm.
- **Phiếu NX (PDF):** Sinh từ template Word `Phiếu NX_BodyTemplate` với dữ liệu từ `phieu_nx` và `phieu_nx_ct`.
- **Báo cáo hao hụt NVL:** So sánh định mức BOM với NVL xuất thực tế cho từng LSX.

### 3.3. Module Quản lý Đơn hàng

**Trạng thái Backend:** ✅ Đã hoàn thành - API endpoints đã implement trong `backend/app/api/orders.py`

#### 3.3.1. Quản lý Đơn hàng
**Mục tiêu:** Quản lý toàn bộ lifecycle đơn hàng

**Features:**
- **Tạo đơn hàng:** Form nhanh với validation
- **Chi tiết đơn hàng:** Nhiều sản phẩm mỗi đơn
- **Auto pricing:** Áp dụng chính sách giá theo cấp KH
- **Order tracking:** Trạng thái từ mới → đang SX → đã giao
- **Duplicate prevention:** Cảnh báo trùng lặp
- **Bulk operations:** Nhập Excel nhiều đơn cùng lúc

**Data Models:**
```sql
don_hang {
  id: string
  ma_dh: string (DHxxxx)
  khach_hang_id: foreign key
  ngay_dat_hang: date
  han_giao_hang: date
  trang_thai: enum [Mới, Đang SX, Hoàn thành, Đã giao]
  tong_tien: number
  thanh_toan: enum [Chưa, Đã]
  ghi_chu: text
  created_at: timestamp
}

don_hang_ct {
  id: string
  don_hang_id: foreign key
  san_pham_id: foreign key
  ten_sp: string
  quy_cach: string            -- quy cách đóng gói bán cho KH
  dvt: string
  so_luong: number
  don_gia: number
  thanh_tien: number
  quy_cach_me: string (kg/mẻ, cái/mẻ)
}
```

#### 3.3.2. Tổng hợp đơn hàng thành LSX
**Mục tiêu:** Tự động chuyển đơn hàng thành lệnh sản xuất

**Business Logic:**
```
Đơn hàng → Check tồn BTP → Tạo LSX sản phẩm
         ↓
         Check tồn NVL → Tạo phiếu xuất kho
         ↓
         Gửi thông báo Telegram cho bộ phận SX
```

**Data model & ràng buộc chính Đơn hàng:**

```text
- don_hang.ma_dh unique, mapping sang MISA (nếu có)
- don_hang_ct.don_gia lấy theo chính sách giá theo cấp khách hàng
- Ràng buộc:
  • Không cho xóa/sửa đơn_hang đã sinh LSX hoặc đã giao hàng
  • Không cho tạo đơn trùng (cùng KH, ngày, mã đơn tham chiếu) theo logic trong backend
```
### 3.4. Module CRM

**Trạng thái Backend:** ✅ Đã hoàn thành - API endpoints đã implement trong `backend/app/api/catalog.py` và `backend/app/api/crm_extended.py`

#### 3.4.1. Quản lý Khách hàng
**Features:**
- **Customer master:** Thông tin liên hệ, địa chỉ, cấp độ
- **Purchase history:** Lịch sử mua hàng
- **Credit limit:** Quản lý nợ, công nợ
- **Pricing policy:** Giá theo cấp khách hàng

#### 3.4.2. Quản lý Nhà cung cấp
**Features:**
- **Supplier master:** Thông tin NCC, điều khoản
- **Material catalog:** Danh mục NVL cung cấp
- **Price tracking:** Lịch sử giá NVL
- **Performance rating:** Đánh giá chất lượng NCC

#### 3.4.3. Analytics & Reporting
**Features:**
- **Sales analytics:** Doanh thu theo kênh, tháng, KH
- **KPI tracking:** Đạt chỉ tiêu phát triển KH mới
- **Customer segmentation:** Phân loại KH theo doanh số
- **Feedback management:** Thu thập phản hồi chất lượng

**Data model chính CRM:**

```sql
khach_hang {
  id: string
  ma_kh: string (unique)
  ten_kh: string
  cap_khach_hang: enum [A, B, C, Khác]
  kenh_ban: enum [GT, MT, Online, Khác]
  sdt: string
  email: string
  dia_chi: string
  cong_no_toi_da: number
  trang_thai: enum [Đang giao dịch, Ngưng]
}

nha_cung_cap {
  id: string
  ma_ncc: string (unique)
  ten_ncc: string
  sdt: string
  email: string
  dia_chi: string
  danh_gia: number        -- rating
}

chinh_sach_gia {
  id: string
  san_pham_id: foreign key → san_pham
  cap_khach_hang: enum [A, B, C, Khác]
  don_gia: number
  ngay_hieu_luc: date
}

lich_su_gia_nvl {
  id: string
  nvl_id: foreign key → san_pham
  ncc_id: foreign key → nha_cung_cap
  don_gia: number
  ngay_bao_gia: date
}
```

### 3.5. Module Hành chính Nhân sự

**Trạng thái Backend:** ✅ Đã hoàn thành - API endpoints đã implement trong `backend/app/api/hr.py` và `backend/app/api/hr_extended.py`

#### 3.5.1. Quản lý Nhân viên
**Features:**
- **Employee master:** Thông tin cá nhân, hợp đồng
- **Department structure:** Sơ đồ phòng ban
- **Position management:** Chức danh, mức lương
- **Time tracking:** Chấm công, tính lương

#### 3.5.2. Tuyển dụng & Đánh giá
**Features:**
- **Recruitment workflow:** Tuyển → Phỏi vấn → Tuyển dụng
- **Performance review:** Đánh giá định kỳ
- **Training records:** Quản lý đào tạo
- **Exit process:** Thông báo nghỉ việc

**Data model chính HCNS:**

```sql
nhan_su {
  id: string
  ma_nv: string (unique)
  ho_ten: string
  phong_ban_id: foreign key → phong_ban
  chuc_danh_id: foreign key → chuc_danh
  ngay_vao_lam: date
  ngay_nghi_viec: date
  trang_thai: enum [Đang làm, Tạm nghỉ, Đã nghỉ]
}

phong_ban {
  id: string
  ma_phong: string (unique)
  ten_phong: string
}

chuc_danh {
  id: string
  ten_chuc_danh: string
  bac_luong_co_ban: number
}

cham_cong {
  id: string
  ngay: date
  ma_nv: foreign key → nhan_su
  ca_lam: string
  so_gio_cong: number
  so_gio_tang_ca: number
}
```

### 3.6. Module Thiết Bị, CCDC (Equipment & Tools)

**Trạng thái Backend:** ✅ Đã hoàn thành - API endpoints đã implement trong `backend/app/api/equipment.py`

**Features:**
- **Equipment master:** Quản lý thiết bị và loại thiết bị
- **Fuel consumption norms:** Định mức nhiên liệu theo thiết bị
- **Equipment repair:** Phiếu sửa chữa và theo dõi sửa chữa
- **Maintenance history:** Lịch sử bảo dưỡng và lịch bảo dưỡng định kỳ

### 3.7. Module Thu Mua (Procurement)

**Trạng thái Backend:** ✅ Đã hoàn thành - API endpoints đã implement trong `backend/app/api/procurement.py`

**Features:**
- **Purchase request:** Phiếu yêu cầu mua hàng với workflow phê duyệt
- **Purchase order:** Đơn mua hàng và chi tiết
- **Purchase history:** Lịch sử mua hàng và đánh giá NCC

### 3.8. Module Sản Xuất Mở Rộng (Production Extended)

**Trạng thái Backend:** ✅ Đã hoàn thành - API endpoints đã implement trong `backend/app/api/production_extended.py`

**Features:**
- **Production logbook:** Nhật ký sản xuất chi tiết theo công đoạn
- **Production stages:** Quản lý công đoạn sản xuất và thao tác

### 3.9. Module Giao Vận (Logistics)

**Trạng thái Backend:** ✅ Đã hoàn thành - API endpoints đã implement trong `backend/app/api/logistics.py`

**Features:**
- **Delivery management:** Quản lý phiếu giao hàng
- **Delivery vehicle:** Quản lý phương tiện giao hàng
- **Delivery tracking:** Theo dõi trạng thái giao hàng

### 3.10. Module Chất Lượng (Quality)

**Trạng thái Backend:** ✅ Đã hoàn thành - API endpoints đã implement trong `backend/app/api/quality.py`

**Features:**
- **Non-conformity management:** Quản lý sự không phù hợp và hành động khắc phục
- **ISO documents:** Quản lý tài liệu ISO với version control

---

### 3.11. Data Model tổng quan (tóm tắt)

- **Nhóm QLSX:**
  - `don_hang`, `don_hang_ct`
  - `lenh_sx`, `lenh_sx_ct`, `khsx_ngay`
  - `bom_sp`, `bom_btp`, `bom_nhan_cong`
- **Nhóm Kho:**
  - `phieu_nx`, `phieu_nx_ct`
  - `dm_kho`, `ton_kho_song`, `kiem_ke`, `kiem_ke_ct`
- **Nhóm Danh mục & CRM:**
  - `san_pham`, `khach_hang`, `nha_cung_cap`, `chinh_sach_gia`, `lich_su_gia_nvl`
- **Nhóm HCNS:**
  - `nhan_su`, `phong_ban`, `chuc_danh`, `cham_cong`
  - `employment_contract`, `performance_review`, `training_record`, `exit_process`
- **Nhóm Thiết Bị:**
  - `equipment_type`, `equipment`, `fuel_consumption_norm`
  - `equipment_repair`, `maintenance_schedule`, `maintenance_record`
- **Nhóm Thu Mua:**
  - `purchase_request`, `purchase_request_line`
  - `purchase_order`, `purchase_order_line`
- **Nhóm Sản Xuất Mở Rộng:**
  - `production_stage`, `stage_operation`
  - `production_log`, `production_log_entry`
- **Nhóm Giao Vận:**
  - `delivery_vehicle`, `delivery`, `delivery_line`
- **Nhóm Chất Lượng:**
  - `non_conformity`, `non_conformity_action`
  - `iso_document`, `iso_document_version`
- **Nhóm CRM Mở Rộng:**
  - `accounts_receivable`, `accounts_payable`
  - `supplier_contract`, `supplier_evaluation`
  - `customer_segment`, `customer_feedback`
  - `kpi_metric`, `kpi_record`

Các entity trên được mô tả chi tiết hơn trong phụ lục Data Dictionary và đã được implement đầy đủ trong backend với migrations tương ứng.

---

## 4. USER STORIES & USE CASES

### 4.1. Roles & Permissions

| Role | Module Access | Key Actions |
|-------|---------------|--------------|
| Admin | Full access | Cấu hình hệ thống, phân quyền |
| Kế toán | Đơn hàng, Báo cáo | Tạo đơn, xem báo cáo |
| Kho trưởng | Kho | Nhập/xuất kho, kiểm kê |
| Sản xuất | QLSX | Tạo LSX, cập nhật tiến độ |
| Kinh doanh | CRM, Đơn hàng | Tạo đơn, quản lý KH |

### 4.2. Key Use Cases

#### UC-01: Tạo Lệnh sản xuất từ Đơn hàng
**Actor:** Kế toán sản xuất
**Preconditions:** Đơn hàng đã được xác nhận

**Flow:**
1. Chọn đơn hàng cần chuyển LSX
2. Hệ thống kiểm tra tồn BTP, NVL
3. Tự động phân bổ sản xuất theo ngày
4. Tạo LSX với QR code
5. Gửi thông báo Telegram cho sản xuất

**Postconditions:** LSX được tạo, tồn kho được giữ chỗ

#### UC-02: Nhập kho hoàn thành sản xuất
**Actor:** Thủ kho
**Preconditions:** LSX đã hoàn thành

**Flow:**
1. Quét QR code LSX bằng điện thoại
2. Hiển thị danh sách sản phẩm cần nhập
3. Nhập số lượng thực tế
4. Hệ thống tạo phiếu nhập kho
5. Cập nhật tồn kho tự động
6. In phiếu nhập kho

#### UC-03: Kiểm kê kho định kỳ
**Actor:** Thủ kho
**Preconditions:** Đã có kế hoạch kiểm kê

**Flow:**
1. Tạo file kiểm kê từ template
2. Import số liệu thực tế đếm
3. Hệ thống so sánh với sổ sách
4. Tự động tạo phiếu điều chỉnh
5. Cập nhật tồn kho về đúng thực tế

---

## 5. YÊU CẦU KỸ THUẬT

### 5.1. Security Requirements

**Authentication:**
- Login qua Google Account
- Session timeout sau 30 phút (cần implement middleware)

**Authorization:**
- Role-based access control (RBAC)
- Field-level permissions
- Audit trail cho tất cả actions

**Data Protection:**
- Backup daily và weekly
- Retention policy 7 năm

### 5.2. Performance Requirements

**Response Time:**
- Screen load < 3 giây
- Report generation < 30 giây
- Real-time sync < 5 giây

**Concurrent Users:**
- Hỗ trợ 50 users đồng thời
- 1000 transactions/giờ
- 99.5% uptime

**Scalability:**
- 50,000 master records
- 10,000 transactions/ngày
- 5 years data retention

### 5.3. Integration Requirements

**Email/Notification:**
- Gmail integration
- Telegram bot for alerts

### 5.4. Data Validation Rules

**Business Rules:**
- Không xuất kho âm
- HSD phải > ngày hiện tại
- Giá bán >= giá vốn
- Đơn hàng phải có KH hợp lệ

**Data Quality:**
- Unique constraints cho key fields
- Required field validation
- Format validation (email, phone, etc)

### 5.5. Automation & Backend Services

**Nhóm QLSX & Đơn hàng:**
- **API Endpoint:** `POST /api/production/orders/from-sales-orders`
  - **Trigger:** Khi đơn hàng chuyển trạng thái "Đã xác nhận" (qua frontend hoặc webhook).
  - **Actions chính:** Backend service tự động:
    - Gom nhu cầu theo sản phẩm/ngày SX.
    - Tạo bản ghi `lenh_sx` + `lenh_sx_ct`.
    - Tính toán nhu cầu BTP/NVL từ BOM.
- **Production Planning Service:**
  - **Mục tiêu:** Chạy pipeline: đọc đơn hàng → tính nhu cầu BTP/NVL → tạo LSX → gửi thông báo.
  - **API:** `POST /api/production/planning/calculate-btp-demand`

**Nhóm Kho & Tồn kho:**
- **API Endpoint:** `POST /api/inventory/documents/from-production-date`
  - **Trigger:** Khi LSX chuyển trạng thái "Ban hành".
  - **Actions:** Tạo `phieu_nx` loại Xuất + `phieu_nx_ct` tương ứng định mức NVL theo BOM.
- **API Endpoint:** `POST /api/inventory/documents/from-production-order/:order_id`
  - **Trigger:** Khi cập nhật SL hoàn thành LSX.
  - **Actions:** Tạo `phieu_nx` loại Nhập kho thành phẩm/BTP, cập nhật tồn kho real-time.
- **Reporting Service:**
  - **API:** `GET /api/reports/*` - Sinh báo cáo NXT và các báo cáo khác từ dữ liệu database.

**Nhóm Thông báo & In ấn:**
- **Telegram Bot Service:**
  - Gửi thông báo khi:
    - Có LSX mới được tạo/ban hành.
    - Có phiếu xuất NVL lớn bất thường.
    - Tồn kho dưới mức min.
- **Document Generation:**
  - **Backend service** tạo file Word/PDF từ các template:
    - `LSX_BodyTemplate`
    - `Phiếu NX_BodyTemplate`
    - `BC_NXT_BodyTemplate`
  - Sử dụng thư viện Python (python-docx, reportlab, etc.)

Tất cả automation trên được log execution (backend logs) và có cơ chế retry hoặc cảnh báo khi lỗi.

---

## 6. IMPLEMENTATION ROADMAP

### 6.1. Current Status (Completed ✅)

**Backend Implementation - 100% Hoàn Thành (39/39 tính năng core)**

**Core Modules:**
- ✅ BOM management và cost calculation
- ✅ Lệnh sản xuất workflow
- ✅ Nhập/xuất kho cơ bản
- ✅ Real-time inventory tracking
- ✅ QR code generation
- ✅ Basic reporting
- ✅ Đơn hàng management
- ✅ Inventory analysis (ABC, Turnover)

**Module Mới (11 tính năng):**
- ✅ Module Thiết Bị, CCDC (4 tính năng): Equipment, Fuel Norms, Repair, Maintenance
- ✅ Module Thu Mua (2 tính năng): Purchase Request, Purchase History
- ✅ Module Sản Xuất Mở Rộng (2 tính năng): Production Logbook, Production Stages
- ✅ Module Giao Vận (1 tính năng): Delivery Management
- ✅ Module Chất Lượng (2 tính năng): Non-conformity Management, ISO Documents

**CRM Enhancements (7 tính năng):**
- ✅ Công nợ chi tiết (Accounts Receivable/Payable)
- ✅ Phân tích hành vi mua hàng
- ✅ Điều khoản hợp đồng NCC
- ✅ Đánh giá chất lượng NCC tự động
- ✅ KPI tracking
- ✅ Customer segmentation
- ✅ Feedback management

**HCNS Enhancements (4 tính năng):**
- ✅ Hợp đồng lao động
- ✅ Performance review
- ✅ Training records
- ✅ Exit process

**Reporting Enhancements (5 tính năng):**
- ✅ Báo cáo hiệu quả sản xuất
- ✅ Báo cáo lợi nhuận
- ✅ Dashboard tổng quan (Executive Dashboard)
- ✅ Real-time KPI dashboard
- ✅ Báo cáo tồn kho theo thời gian

**Backend API Endpoints:** 80+ endpoints đã implement
**Database Migrations:** 6 migration files với đầy đủ schema

### 6.2. In Progress 🚧

**Frontend Integration:**
- 🚧 Tích hợp UI cho các module mới
- 🚧 Web interface improvements
- 🚧 Mobile app optimization

**Cần Cấu Hình:**
- ⚠️ QuickChart API integration (cần cấu hình)
- ⚠️ Session timeout middleware (cần implement)
- ⚠️ Data migration/cleanup tools (scripts riêng)

### 6.3. Planned Features 📋

**Frontend Development:**
- 📋 Complete UI cho tất cả modules
- 📋 Advanced dashboard visualizations
- 📋 Mobile app enhancements

**Future Enhancements:**
- 📋 Advanced forecasting
- 📋 Production scheduling AI
- 📋 Supplier portal

### 6.4. Technical Debt

**Priority Items:**
1. Code refactoring cho performance
2. Security audit & hardening
3. Documentation improvements
4. Testing automation setup
5. Error handling enhancement

---

## 7. TESTING & QA

### 7.1. Testing Strategy

**Unit Testing:**
- Backend API endpoints
- Business logic validation
- Data calculation accuracy
- Service layer functions

**Integration Testing:**
- Frontend (HTMX) ↔ Backend (Robyn API)
- Database operations
- External API calls
- Email/Telegram notifications

**UAT Testing:**
- End-to-end workflows
- User acceptance criteria
- Performance under load

### 7.2. Test Cases Sample

| TC | Description | Expected Result |
|----|-------------|-----------------|
| TC-001 | Tạo LSX từ đơn hàng | LSX created with correct BOM |
| TC-002 | Nhập kho bằng QR | Stock updated correctly |
| TC-003 | Xuất kho vượt tồn | Error message shown |
| TC-004 | Báo cáo tồn kho | Accurate inventory data |

### 7.3. Acceptance Criteria

**Functional:**
- All user stories working
- Business rules enforced
- Data integrity maintained

**Non-functional:**
- Performance requirements met
- Security standards complied
- Usability score > 8/10

---

## 8. DEPLOYMENT & MAINTENANCE

### 8.1. Deployment Strategy

**Environment:**
- Development: Test account
- Staging: Pilot with 5 users
- Production: Full rollout

**Rollback Plan:**
- Data backup trước deployment
- Version control với tags
- Emergency rollback procedure

### 8.2. Monitoring & Support

**System Monitoring:**
- Backend API logs (Robyn logging)
- Database query performance
- API response time monitoring
- Error rate monitoring
- System resource usage (CPU, memory, disk)

**User Support:**
- Help documentation
- Training materials
- Support hotline
- Issue tracking system

### 8.3. Backup & Recovery

**Backup Schedule:**
- Daily incremental backup (PostgreSQL)
- Weekly full backup
- Monthly archive to cloud storage
- Cross-region backup storage

**Recovery Procedures:**
- RTO: 4 hours
- RPO: 1 hour
- Disaster recovery plan
- Annual recovery testing

---

## 9. SUCCESS METRICS

### 9.1. Business KPIs

**Efficiency Gains:**
- 80% reduction in manual data entry
- 50% faster order processing
- 90% accuracy in inventory counting
- 60% time savings in reporting

**Cost Benefits:**
- 40% reduction in overtime costs
- 25% improvement in cash flow
- 15% reduction in inventory holding costs
- 35% better on-time delivery

### 9.2. Technical Metrics

**System Performance:**
- < 2 second average response time
- 99.9% system availability
- < 0.1% error rate
- 50+ concurrent users supported

**User Adoption:**
- 90% user satisfaction score
- 80% feature utilization rate
- < 1 day average issue resolution
- 95% successful transaction rate

---

## 10. APPENDICES

### 10.1. Glossary

| Term | Definition |
|-------|------------|
| BOM | Bill of Materials - Định mức nguyên vật liệu |
| LSX | Lệnh Sản Xuất - Production Order |
| BTP | Bán Thành Phẩm - Semi-finished Goods |
| NVL | Nguyên Vật Liệu - Raw Materials |
| KHSX | Kế Hoạch Sản Xuất - Production Planning |

### 10.2. References

**Technical Documentation:**
- Robyn framework documentation
- HTMX documentation
- PostgreSQL documentation
- SQLAlchemy ORM guide
- Python best practices

**Business Process:**
- Manufacturing workflow diagrams
- Inventory management best practices
- Quality control procedures

---

**Document Control:**
- **Owner:** Product Manager
- **Review Cycle:** Quarterly
- **Next Review:** 29/02/2025
- **Distribution:** All stakeholders

---

*This PRD is living document and will be updated as requirements evolve and user feedback is collected.*
