-- Migration 004: Thêm các bảng cho Module Thiết Bị, Thu Mua, Sản Xuất mở rộng, Giao Vận, và Chất Lượng

-- ============================================
-- 1. MODULE THIẾT BỊ, CCDC
-- ============================================

CREATE TABLE IF NOT EXISTS equipment_type (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(50) NOT NULL UNIQUE,
    name varchar(255) NOT NULL,
    description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS equipment (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(50) NOT NULL UNIQUE,
    name varchar(255) NOT NULL,
    equipment_type_id uuid REFERENCES equipment_type(id),
    manufacturer varchar(255),
    model varchar(255),
    serial_number varchar(100),
    purchase_date date,
    warranty_expiry date,
    location varchar(255),
    status varchar(20) NOT NULL DEFAULT 'active',
    note text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fuel_consumption_norm (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id uuid NOT NULL REFERENCES equipment(id),
    fuel_type varchar(50) NOT NULL,
    consumption_rate numeric(18,4) NOT NULL,
    unit varchar(20) NOT NULL,
    effective_date date NOT NULL,
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS equipment_repair (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(50) NOT NULL UNIQUE,
    equipment_id uuid NOT NULL REFERENCES equipment(id),
    request_date date NOT NULL,
    repair_date date,
    description text,
    issue_description text,
    repair_description text,
    cost numeric(18,2),
    status varchar(20) NOT NULL DEFAULT 'requested',
    repaired_by varchar(255),
    note text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS equipment_repair_line (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    repair_id uuid NOT NULL REFERENCES equipment_repair(id),
    item_description varchar(255) NOT NULL,
    quantity numeric(18,3) NOT NULL,
    unit_price numeric(18,2) NOT NULL,
    line_amount numeric(18,2) NOT NULL,
    note text
);

CREATE TABLE IF NOT EXISTS maintenance_schedule (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id uuid NOT NULL REFERENCES equipment(id),
    maintenance_type varchar(50) NOT NULL,
    interval_days integer,
    interval_hours numeric(18,2),
    next_maintenance_date date,
    next_maintenance_hours numeric(18,2),
    is_active boolean NOT NULL DEFAULT true,
    note text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS maintenance_record (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id uuid NOT NULL REFERENCES equipment(id),
    schedule_id uuid REFERENCES maintenance_schedule(id),
    maintenance_date date NOT NULL,
    maintenance_hours numeric(18,2),
    maintenance_type varchar(50) NOT NULL,
    description text,
    performed_by varchar(255),
    cost numeric(18,2),
    next_maintenance_date date,
    next_maintenance_hours numeric(18,2),
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================
-- 2. MODULE THU MUA
-- ============================================

CREATE TABLE IF NOT EXISTS purchase_request (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(50) NOT NULL UNIQUE,
    request_date date NOT NULL,
    requested_by varchar(255),
    department varchar(255),
    purpose text,
    status varchar(20) NOT NULL DEFAULT 'draft',
    approved_by varchar(255),
    approved_date date,
    total_amount numeric(18,2) NOT NULL DEFAULT 0,
    note text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS purchase_request_line (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id uuid NOT NULL REFERENCES purchase_request(id),
    product_id uuid NOT NULL REFERENCES product(id),
    product_name varchar(255) NOT NULL,
    specification varchar(255),
    quantity numeric(18,3) NOT NULL,
    uom varchar(20) NOT NULL,
    estimated_unit_price numeric(18,2),
    estimated_amount numeric(18,2) NOT NULL DEFAULT 0,
    required_date date,
    note text
);

CREATE TABLE IF NOT EXISTS purchase_order (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(50) NOT NULL UNIQUE,
    purchase_request_id uuid REFERENCES purchase_request(id),
    supplier_id uuid NOT NULL REFERENCES supplier(id),
    order_date date NOT NULL,
    expected_delivery_date date,
    actual_delivery_date date,
    status varchar(20) NOT NULL DEFAULT 'draft',
    total_amount numeric(18,2) NOT NULL DEFAULT 0,
    payment_status varchar(20) NOT NULL DEFAULT 'unpaid',
    note text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS purchase_order_line (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES purchase_order(id),
    product_id uuid NOT NULL REFERENCES product(id),
    product_name varchar(255) NOT NULL,
    specification varchar(255),
    quantity numeric(18,3) NOT NULL,
    received_quantity numeric(18,3) NOT NULL DEFAULT 0,
    uom varchar(20) NOT NULL,
    unit_price numeric(18,2) NOT NULL,
    line_amount numeric(18,2) NOT NULL,
    note text
);

-- ============================================
-- 3. MODULE SẢN XUẤT MỞ RỘNG
-- ============================================

CREATE TABLE IF NOT EXISTS production_stage (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(50) NOT NULL UNIQUE,
    name varchar(255) NOT NULL,
    sequence integer NOT NULL,
    description text,
    standard_duration_minutes integer,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stage_operation (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    stage_id uuid NOT NULL REFERENCES production_stage(id),
    name varchar(255) NOT NULL,
    sequence integer NOT NULL,
    description text,
    standard_duration_minutes integer
);

CREATE TABLE IF NOT EXISTS production_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(50) NOT NULL UNIQUE,
    production_order_id uuid NOT NULL REFERENCES productionorder(id),
    log_date date NOT NULL,
    shift varchar(50),
    operator varchar(255),
    start_time timestamptz,
    end_time timestamptz,
    actual_quantity numeric(18,3),
    quality_notes text,
    issues text,
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS production_log_entry (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    log_id uuid NOT NULL REFERENCES production_log(id),
    stage_id uuid NOT NULL REFERENCES production_stage(id),
    start_time timestamptz,
    end_time timestamptz,
    duration_minutes integer,
    operator varchar(255),
    quantity_processed numeric(18,3),
    quality_status varchar(20),
    issues text,
    note text
);

-- ============================================
-- 4. MODULE GIAO VẬN
-- ============================================

CREATE TABLE IF NOT EXISTS delivery_vehicle (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(50) NOT NULL UNIQUE,
    license_plate varchar(20) NOT NULL UNIQUE,
    vehicle_type varchar(50) NOT NULL,
    driver_name varchar(255),
    driver_phone varchar(30),
    capacity_kg numeric(18,2),
    status varchar(20) NOT NULL DEFAULT 'available',
    note text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS delivery (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(50) NOT NULL UNIQUE,
    sales_order_id uuid NOT NULL REFERENCES salesorder(id),
    vehicle_id uuid REFERENCES delivery_vehicle(id),
    planned_delivery_date date NOT NULL,
    actual_delivery_date date,
    delivery_address text,
    contact_person varchar(255),
    contact_phone varchar(30),
    driver_name varchar(255),
    status varchar(20) NOT NULL DEFAULT 'planned',
    delivery_notes text,
    signature_url text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS delivery_line (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_id uuid NOT NULL REFERENCES delivery(id),
    product_id uuid NOT NULL REFERENCES product(id),
    product_name varchar(255) NOT NULL,
    quantity numeric(18,3) NOT NULL,
    delivered_quantity numeric(18,3) NOT NULL DEFAULT 0,
    uom varchar(20) NOT NULL,
    note text
);

-- ============================================
-- 5. MODULE CHẤT LƯỢNG
-- ============================================

CREATE TABLE IF NOT EXISTS non_conformity (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(50) NOT NULL UNIQUE,
    detected_date date NOT NULL,
    detected_by varchar(255),
    production_order_id uuid REFERENCES productionorder(id),
    product_id uuid REFERENCES product(id),
    category varchar(50) NOT NULL,
    severity varchar(20) NOT NULL,
    description text NOT NULL,
    root_cause text,
    status varchar(20) NOT NULL DEFAULT 'detected',
    note text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS non_conformity_action (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    non_conformity_id uuid NOT NULL REFERENCES non_conformity(id),
    action_type varchar(50) NOT NULL,
    description text NOT NULL,
    responsible_person varchar(255),
    planned_date date,
    completed_date date,
    status varchar(20) NOT NULL DEFAULT 'planned',
    effectiveness varchar(20),
    note text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS iso_document (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(50) NOT NULL UNIQUE,
    title varchar(255) NOT NULL,
    document_type varchar(50) NOT NULL,
    iso_standard varchar(50),
    version varchar(20) NOT NULL,
    effective_date date NOT NULL,
    expiry_date date,
    status varchar(20) NOT NULL DEFAULT 'draft',
    approved_by varchar(255),
    approved_date date,
    file_url text,
    description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS iso_document_version (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES iso_document(id),
    version varchar(20) NOT NULL,
    effective_date date NOT NULL,
    file_url text,
    change_description text,
    created_by varchar(255),
    created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================
-- 6. INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_equipment_type_id ON equipment(equipment_type_id);
CREATE INDEX IF NOT EXISTS idx_equipment_status ON equipment(status);
CREATE INDEX IF NOT EXISTS idx_fuel_norm_equipment_id ON fuel_consumption_norm(equipment_id);
CREATE INDEX IF NOT EXISTS idx_equipment_repair_equipment_id ON equipment_repair(equipment_id);
CREATE INDEX IF NOT EXISTS idx_equipment_repair_status ON equipment_repair(status);
CREATE INDEX IF NOT EXISTS idx_equipment_repair_line_repair_id ON equipment_repair_line(repair_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_schedule_equipment_id ON maintenance_schedule(equipment_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_record_equipment_id ON maintenance_record(equipment_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_record_schedule_id ON maintenance_record(schedule_id);

CREATE INDEX IF NOT EXISTS idx_purchase_request_status ON purchase_request(status);
CREATE INDEX IF NOT EXISTS idx_purchase_request_line_request_id ON purchase_request_line(request_id);
CREATE INDEX IF NOT EXISTS idx_purchase_request_line_product_id ON purchase_request_line(product_id);
CREATE INDEX IF NOT EXISTS idx_purchase_order_supplier_id ON purchase_order(supplier_id);
CREATE INDEX IF NOT EXISTS idx_purchase_order_status ON purchase_order(status);
CREATE INDEX IF NOT EXISTS idx_purchase_order_purchase_request_id ON purchase_order(purchase_request_id);
CREATE INDEX IF NOT EXISTS idx_purchase_order_line_order_id ON purchase_order_line(order_id);
CREATE INDEX IF NOT EXISTS idx_purchase_order_line_product_id ON purchase_order_line(product_id);

CREATE INDEX IF NOT EXISTS idx_production_stage_sequence ON production_stage(sequence);
CREATE INDEX IF NOT EXISTS idx_stage_operation_stage_id ON stage_operation(stage_id);
CREATE INDEX IF NOT EXISTS idx_production_log_production_order_id ON production_log(production_order_id);
CREATE INDEX IF NOT EXISTS idx_production_log_log_date ON production_log(log_date);
CREATE INDEX IF NOT EXISTS idx_production_log_entry_log_id ON production_log_entry(log_id);
CREATE INDEX IF NOT EXISTS idx_production_log_entry_stage_id ON production_log_entry(stage_id);

CREATE INDEX IF NOT EXISTS idx_delivery_vehicle_status ON delivery_vehicle(status);
CREATE INDEX IF NOT EXISTS idx_delivery_sales_order_id ON delivery(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_delivery_vehicle_id ON delivery(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_delivery_status ON delivery(status);
CREATE INDEX IF NOT EXISTS idx_delivery_line_delivery_id ON delivery_line(delivery_id);
CREATE INDEX IF NOT EXISTS idx_delivery_line_product_id ON delivery_line(product_id);

CREATE INDEX IF NOT EXISTS idx_non_conformity_production_order_id ON non_conformity(production_order_id);
CREATE INDEX IF NOT EXISTS idx_non_conformity_product_id ON non_conformity(product_id);
CREATE INDEX IF NOT EXISTS idx_non_conformity_status ON non_conformity(status);
CREATE INDEX IF NOT EXISTS idx_non_conformity_action_non_conformity_id ON non_conformity_action(non_conformity_id);
CREATE INDEX IF NOT EXISTS idx_iso_document_status ON iso_document(status);
CREATE INDEX IF NOT EXISTS idx_iso_document_version_document_id ON iso_document_version(document_id);

-- Comments
COMMENT ON TABLE equipment IS 'Bảng thiết bị';
COMMENT ON TABLE fuel_consumption_norm IS 'Bảng định mức nhiên liệu';
COMMENT ON TABLE equipment_repair IS 'Bảng phiếu sửa chữa thiết bị';
COMMENT ON TABLE maintenance_record IS 'Bảng lịch sử bảo dưỡng';
COMMENT ON TABLE purchase_request IS 'Bảng phiếu yêu cầu mua hàng';
COMMENT ON TABLE purchase_order IS 'Bảng đơn mua hàng';
COMMENT ON TABLE production_log IS 'Bảng nhật ký sản xuất';
COMMENT ON TABLE production_stage IS 'Bảng công đoạn sản xuất';
COMMENT ON TABLE delivery IS 'Bảng phiếu giao hàng';
COMMENT ON TABLE non_conformity IS 'Bảng sự không phù hợp';
COMMENT ON TABLE iso_document IS 'Bảng tài liệu ISO';

