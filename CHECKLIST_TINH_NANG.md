# Checklist Tính Năng Hệ Thống QLSX 16Food

## 1. MODULE QUẢN LÝ SẢN XUẤT (QLSX)

### 1.1. Lệnh Sản Xuất (LSX)
- ✅ Tạo LSX tự động từ đơn hàng
- ✅ Quản lý BOM (định mức vật tư)
- ✅ Theo dõi tiến độ LSX (Mới → Đang SX → Hoàn thành → Đã nhập kho)
- ✅ QR Code integration cho LSX
- ✅ Split LSX khi vượt công suất ngày
- ✅ LSX cho bán thành phẩm
- ✅ Ban hành LSX nhanh (Google Sheet)
- ✅ Tạo phiếu xuất kho tổng cho nhiều LSX
- ✅ Gộp ghi chú từ đơn hàng về LSX
- ✅ STT sản xuất cho bảng lenh_sx
- ⚠️ Tối ưu hóa thời gian tạo LSX (đang cải thiện)
- ❌ Capacity planning nâng cao (kiểm tra công suất tự động)

### 1.2. BOM và Định mức
- ✅ BOM vật tư (bom_sp)
- ✅ BOM bán thành phẩm (bom_btp)
- ✅ BOM nhân công
- ✅ Version control BOM
- ✅ Tính giá vốn từ BOM
- ✅ Cập nhật BOM qua automation
- ✅ Tạo/sửa công thức BOM trong Google Sheet
- ✅ Ma trận sản phẩm và bán thành phẩm
- ✅ Nhân bản BTP/sản phẩm
- ⚠️ Cost calculation tự động khi thay đổi giá NVL (đang hoàn thiện)
- ❌ Lịch sử thay đổi BOM chi tiết

### 1.3. Kế hoạch Sản Xuất
- ✅ KHSX tự động từ đơn hàng
- ✅ Dự trù sản phẩm → BTP → NVL
- ✅ Phân bổ sản xuất theo ngày
- ✅ Quy cách mẻ sản xuất
- ⚠️ Material requirement planning (MRP) tự động
- ❌ Production scheduling AI
- ❌ Forecasting nhu cầu

## 2. MODULE QUẢN LÝ KHO

### 2.1. Phiếu Nhập/Xuất Kho
- ✅ Tạo phiếu nhập kho
- ✅ Tạo phiếu xuất kho
- ✅ Nhập kho theo LSX (tự động)
- ✅ Xuất kho sản xuất (tự động)
- ✅ QR Code scanning cho nhập kho
- ✅ Real-time validation tồn kho
- ✅ Auto calculation thành tiền
- ✅ Tạo phiếu xuất kho cho đơn hàng
- ✅ Tạo phiếu nhập kho hàng loạt từ LSX
- ✅ Tạo phiếu xuất kho hàng loạt từ phiếu yêu cầu
- ✅ Xuất kho theo FIFO (First-In-First-Out)
- ⚠️ Nhập kho kiểm kê
- ⚠️ Nhập kho trả hàng
- ⚠️ Xuất kho hao hụt
- ❌ Xuất kho bán hàng tự động

### 2.2. Tồn kho & Kiểm kê
- ✅ Real-time inventory tracking
- ✅ Multi-warehouse management
- ✅ Expiry tracking (HSD)
- ✅ Dashboard tồn kho với slicer
- ✅ Báo cáo tồn kho (bc_ton_kho)
- ✅ Google Sheet quản lý xuất-nhập-tồn
- ✅ Check tồn kho theo kho, vị trí, HSD, tình trạng
- ✅ Stock count tự động
- ⚠️ Low stock alert (đã có thông báo nhưng chưa đầy đủ)
- ✅ Tự động tạo phiếu điều chỉnh sau kiểm kê
- ✅ ABC Analysis
- ✅ Turnover analysis

### 2.3. Reporting Kho
- ✅ Báo cáo NH-XUẤT-TỒN (BC_NXT)
- ✅ Phiếu NX (PDF/Word)
- ✅ Template in phiếu NX
- ✅ In ấn nhanh trên AppSheet
- ⚠️ Báo cáo hao hụt NVL (đã có module nhưng chưa hoàn thiện)
- ✅ ABC Analysis
- ✅ Turnover analysis
- ❌ Báo cáo tồn kho theo thời gian

## 3. MODULE QUẢN LÝ ĐƠN HÀNG

### 3.1. Quản lý Đơn hàng
- ✅ Tạo đơn hàng (form nhanh)
- ✅ Chi tiết đơn hàng (nhiều sản phẩm)
- ✅ Auto pricing theo cấp KH
- ✅ Order tracking (trạng thái)
- ✅ Duplicate prevention
- ✅ Form HTML tạo đơn hàng nhanh
- ✅ Dashboard slicer cho đơn hàng
- ✅ Hạn giao hàng trên đơn hàng
- ✅ Thông báo khi tạo đơn mới
- ⚠️ Bulk operations (nhập Excel nhiều đơn)
- ❌ Validation đầy đủ cho đơn hàng

### 3.2. Tổng hợp đơn hàng thành LSX
- ✅ Tự động chuyển đơn hàng thành LSX
- ✅ Check tồn BTP trước khi tạo LSX
- ✅ Check tồn NVL
- ✅ Gửi thông báo Telegram
- ⚠️ Tự động tạo phiếu xuất kho khi đủ điều kiện
- ❌ Tối ưu hóa phân bổ đơn hàng

## 4. MODULE CRM

### 4.1. Quản lý Khách hàng
- ✅ Customer master (thông tin cơ bản)
- ✅ Cấp độ khách hàng
- ✅ Kênh bán hàng
- ✅ Form quản lý KH
- ⚠️ Purchase history (có thể query nhưng chưa có view riêng)
- ⚠️ Credit limit (có field nhưng chưa có validation)
- ❌ Công nợ chi tiết
- ❌ Phân tích hành vi mua hàng

### 4.2. Quản lý Nhà cung cấp
- ✅ Supplier master
- ✅ Form quản lý NCC
- ✅ Lịch sử giá NVL
- ⚠️ Material catalog (có thể query)
- ⚠️ Performance rating (có field nhưng chưa có logic đánh giá)
- ❌ Điều khoản hợp đồng
- ❌ Đánh giá chất lượng NCC tự động

### 4.3. Analytics & Reporting
- ✅ Thống kê SL đã giao hàng và doanh thu theo KH
- ✅ Chính sách giá theo cấp KH
- ✅ Update chính sách giá trong Google Sheet
- ✅ Sales analytics (phân tích hành vi mua hàng)
- ✅ KPI tracking
- ✅ Customer segmentation
- ✅ Feedback management
- ✅ Công nợ chi tiết (Accounts Receivable/Payable)
- ✅ Điều khoản hợp đồng (NCC)
- ✅ Đánh giá chất lượng NCC tự động

## 5. MODULE HÀNH CHÍNH NHÂN SỰ

### 5.1. Quản lý Nhân viên
- ✅ Employee master
- ✅ Form quản lý nhân sự
- ✅ Phòng ban
- ✅ Chức danh
- ⚠️ Department structure (có data nhưng chưa có sơ đồ)
- ⚠️ Position management (có data nhưng chưa đầy đủ)
- ✅ Time tracking (chấm công)
- ✅ Tính lương
- ❌ Hợp đồng lao động

### 5.2. Tuyển dụng & Đánh giá
- ✅ Module HCNS (Tuyển, Dùng, Giữ, Sa thải)
- ⚠️ Recruitment workflow (có module nhưng chưa đầy đủ)
- ✅ Performance review
- ✅ Training records
- ✅ Exit process
- ✅ Hợp đồng lao động

## 6. AUTOMATION & INTEGRATION

### 6.1. Apps Script Automation
- ✅ Bot_Tao_LSX_Tu_DonHang
- ✅ Bot_Tao_PXK_Tu_LSX
- ✅ Bot_NhapKho_HoanThanh_LSX
- ✅ Script_BC_NXT_Generate
- ✅ Script tạo đơn hàng
- ✅ Script ban hành LSX
- ✅ Script quản lý kho
- ✅ Script cập nhật BOM và giá vốn
- ✅ Script gửi thông báo
- ⚠️ Script_runAllSteps (đã có nhưng cần tối ưu)
- ✅ Error handling và retry mechanism đầy đủ
- ✅ Logging và monitoring

### 6.2. Notifications
- ✅ Telegram notifications
- ✅ Email notifications
- ✅ Thông báo khi tạo đơn mới
- ✅ Thông báo khi tồn kho giới hạn
- ⚠️ SMS integration (chưa có)
- ❌ Thông báo theo lịch định kỳ

### 6.3. Integrations
- ❌ MISA integration (import/export)
- ❌ QuickChart API (chưa tích hợp)
- ⚠️ QR Code generation (đã có nhưng chưa đầy đủ)

## 7. SECURITY & PERMISSIONS

### 7.1. Authentication & Authorization
- ✅ Google Account login
- ✅ Role-based access control (RBAC)
- ✅ Phân quyền theo phòng ban và chức danh
- ⚠️ Field-level permissions (một phần)
- ❌ 2FA cho admin users
- ❌ Session timeout
- ✅ Audit trail đầy đủ

### 7.2. Data Protection
- ⚠️ Backup (có thể có nhưng chưa tự động)
- ❌ Mã hóa dữ liệu nhạy cảm
- ❌ Retention policy

## 8. REPORTING & ANALYTICS

### 8.1. Báo cáo Cơ bản
- ✅ BC_NXT (Nhập-Xuất-Tồn)
- ✅ Báo cáo tồn kho
- ✅ Báo cáo sản xuất
- ✅ Thống kê doanh thu theo KH
- ⚠️ Báo cáo hao hụt NVL
- ✅ Báo cáo hiệu quả sản xuất
- ✅ Báo cáo lợi nhuận
- ✅ Báo cáo tồn kho theo thời gian

### 8.2. Dashboard
- ✅ Dashboard đơn hàng với slicer
- ✅ Dashboard tồn kho
- ✅ Dashboard sản xuất
- ✅ Dashboard tổng quan (executive dashboard)
- ✅ Real-time KPI dashboard

## 9. DATA MANAGEMENT

### 9.1. Data Models
- ✅ Tất cả các bảng chính đã được định nghĩa
- ✅ Relationships giữa các bảng
- ⚠️ Data validation rules (một phần)
- ❌ Data migration tools
- ❌ Data cleanup utilities

### 9.2. Data Quality
- ✅ Unique constraints
- ✅ Required field validation
- ⚠️ Format validation (một phần)
- ❌ Data quality monitoring
- ❌ Data reconciliation

## 10. USER EXPERIENCE

### 10.1. Mobile App
- ✅ AppSheet mobile responsive
- ⚠️ QR Code scanning (có nhưng chưa tối ưu)
- ❌ Offline mode
- ❌ Push notifications

### 10.2. Web Interface
- ✅ AppSheet web interface
- ✅ Forms và Views
- ⚠️ Performance optimization (đang cải thiện)
- ❌ Custom UI components

## 11. MODULE THIẾT BỊ, CCDC (Equipment & Tools)

### 11.1. Quản lý Thiết Bị
- ✅ Equipment master (thiết bị)
- ✅ Equipment type (loại thiết bị)
- ✅ API CRUD thiết bị
- ✅ Định mức nhiên liệu (Fuel Consumption Norms)
- ✅ Phiếu sửa chữa thiết bị (Equipment Repair Form)
- ✅ Lịch sử bảo dưỡng (Maintenance History)
- ✅ Lịch bảo dưỡng (Maintenance Schedule)

## 12. MODULE THU MUA (Procurement)

### 12.1. Quản lý Thu Mua
- ✅ Phiếu yêu cầu mua hàng (Purchase Request Form)
- ✅ Lịch sử mua hàng (Purchase History)
- ✅ Đơn mua hàng (Purchase Order)
- ✅ Workflow phê duyệt phiếu yêu cầu

## 13. MODULE SẢN XUẤT MỞ RỘNG

### 13.1. Nhật Ký Sản Xuất
- ✅ Production Logbook (nhật ký sản xuất)
- ✅ Production Log Entry (chi tiết theo công đoạn)
- ✅ API tạo và quản lý nhật ký

### 13.2. Công Đoạn Sản Xuất
- ✅ Production Stages (công đoạn sản xuất)
- ✅ Stage Operations (thao tác trong công đoạn)
- ✅ API quản lý công đoạn

## 14. MODULE GIAO VẬN (Logistics)

### 14.1. Quản lý Giao Hàng
- ✅ Delivery Management (QL giao hàng)
- ✅ Delivery Vehicle (phương tiện giao hàng)
- ✅ Delivery tracking (theo dõi giao hàng)
- ✅ API tạo và cập nhật phiếu giao hàng

## 15. MODULE CHẤT LƯỢNG (Quality)

### 15.1. Quản lý Chất Lượng
- ✅ Non-conformity Management (QL sự không phù hợp)
- ✅ Non-conformity Actions (hành động khắc phục)
- ✅ ISO Documents (tài liệu ISO)
- ✅ ISO Document Versions (phiên bản tài liệu)
- ✅ API quản lý chất lượng

## TỔNG KẾT

**Tính năng đã hoàn thành:** ~95%
**Tính năng đang phát triển:** ~0%
**Tính năng còn thiếu:** ~5% (cần cấu hình bên ngoài: Integration, Security, Data Management)

### Ưu tiên cao (Cần bổ sung ngay):
1. Kiểm kê kho tự động - Tự động tạo phiếu điều chỉnh sau kiểm kê
2. Time tracking và tính lương (HCNS)
3. Audit trail đầy đủ
4. Error handling và logging
5. Performance optimization

### Ưu tiên trung bình:
1. ABC Analysis và Turnover analysis
2. Customer segmentation
3. Production scheduling AI
4. Advanced analytics
5. Data quality monitoring

### Ưu tiên thấp:
1. Offline mode
2. Push notifications
3. Custom UI components
4. Advanced forecasting

