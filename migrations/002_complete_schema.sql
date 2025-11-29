-- Migration 002: Complete schema với indexes, constraints, triggers và bảng User
-- Chạy sau migration 001_initial_schema.sql

-- ============================================
-- 1. Thêm bảng User
-- ============================================

CREATE TABLE IF NOT EXISTS "user" (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    username varchar(50) NOT NULL UNIQUE,
    password_hash varchar(255) NOT NULL,
    role varchar(30) NOT NULL,
    employee_id uuid REFERENCES employee(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================
-- 2. Thêm Indexes cho performance
-- ============================================

-- Indexes cho foreign keys
CREATE INDEX IF NOT EXISTS idx_pricepolicy_product_id ON pricepolicy(product_id);
CREATE INDEX IF NOT EXISTS idx_materialpricehistory_material_id ON materialpricehistory(material_id);
CREATE INDEX IF NOT EXISTS idx_materialpricehistory_supplier_id ON materialpricehistory(supplier_id);
CREATE INDEX IF NOT EXISTS idx_inventorysnapshot_product_id ON inventorysnapshot(product_id);
CREATE INDEX IF NOT EXISTS idx_inventorysnapshot_warehouse_id ON inventorysnapshot(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_stockdocument_warehouse_id ON stockdocument(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_stockdocumentline_document_id ON stockdocumentline(document_id);
CREATE INDEX IF NOT EXISTS idx_stockdocumentline_product_id ON stockdocumentline(product_id);
CREATE INDEX IF NOT EXISTS idx_stocktaking_warehouse_id ON stocktaking(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_stocktakingline_stocktaking_id ON stocktakingline(stocktaking_id);
CREATE INDEX IF NOT EXISTS idx_stocktakingline_product_id ON stocktakingline(product_id);
CREATE INDEX IF NOT EXISTS idx_salesorder_customer_id ON salesorder(customer_id);
CREATE INDEX IF NOT EXISTS idx_salesorderline_order_id ON salesorderline(order_id);
CREATE INDEX IF NOT EXISTS idx_salesorderline_product_id ON salesorderline(product_id);
CREATE INDEX IF NOT EXISTS idx_productionplanday_product_id ON productionplanday(product_id);
CREATE INDEX IF NOT EXISTS idx_productionorder_product_id ON productionorder(product_id);
CREATE INDEX IF NOT EXISTS idx_productionorderline_production_order_id ON productionorderline(production_order_id);
CREATE INDEX IF NOT EXISTS idx_productionorderline_product_id ON productionorderline(product_id);
CREATE INDEX IF NOT EXISTS idx_bommaterial_product_id ON bommaterial(product_id);
CREATE INDEX IF NOT EXISTS idx_bommaterial_material_id ON bommaterial(material_id);
CREATE INDEX IF NOT EXISTS idx_bomlabor_product_id ON bomlabor(product_id);
CREATE INDEX IF NOT EXISTS idx_bomsemiproduct_semi_product_id ON bomsemiproduct(semi_product_id);
CREATE INDEX IF NOT EXISTS idx_bomsemiproduct_component_id ON bomsemiproduct(component_id);
CREATE INDEX IF NOT EXISTS idx_employee_department_id ON employee(department_id);
CREATE INDEX IF NOT EXISTS idx_employee_job_title_id ON employee(job_title_id);
CREATE INDEX IF NOT EXISTS idx_timesheet_employee_id ON timesheet(employee_id);
CREATE INDEX IF NOT EXISTS idx_user_employee_id ON "user"(employee_id);

-- Indexes cho các trường thường query
CREATE INDEX IF NOT EXISTS idx_product_code ON product(code);
CREATE INDEX IF NOT EXISTS idx_product_group ON product("group");
CREATE INDEX IF NOT EXISTS idx_product_status ON product(status);
CREATE INDEX IF NOT EXISTS idx_customer_code ON customer(code);
CREATE INDEX IF NOT EXISTS idx_customer_status ON customer(status);
CREATE INDEX IF NOT EXISTS idx_warehouse_code ON warehouse(code);
CREATE INDEX IF NOT EXISTS idx_warehouse_type ON warehouse(type);
CREATE INDEX IF NOT EXISTS idx_stockdocument_code ON stockdocument(code);
CREATE INDEX IF NOT EXISTS idx_stockdocument_doc_type ON stockdocument(doc_type);
CREATE INDEX IF NOT EXISTS idx_stockdocument_posting_date ON stockdocument(posting_date);
CREATE INDEX IF NOT EXISTS idx_stocktaking_code ON stocktaking(code);
CREATE INDEX IF NOT EXISTS idx_stocktaking_status ON stocktaking(status);
CREATE INDEX IF NOT EXISTS idx_stocktaking_stocktaking_date ON stocktaking(stocktaking_date);
CREATE INDEX IF NOT EXISTS idx_salesorder_code ON salesorder(code);
CREATE INDEX IF NOT EXISTS idx_salesorder_status ON salesorder(status);
CREATE INDEX IF NOT EXISTS idx_salesorder_order_date ON salesorder(order_date);
CREATE INDEX IF NOT EXISTS idx_salesorder_delivery_date ON salesorder(delivery_date);
CREATE INDEX IF NOT EXISTS idx_productionorder_business_id ON productionorder(business_id);
CREATE INDEX IF NOT EXISTS idx_productionorder_status ON productionorder(status);
CREATE INDEX IF NOT EXISTS idx_productionorder_production_date ON productionorder(production_date);
CREATE INDEX IF NOT EXISTS idx_productionplanday_production_date ON productionplanday(production_date);
CREATE INDEX IF NOT EXISTS idx_user_username ON "user"(username);
CREATE INDEX IF NOT EXISTS idx_user_role ON "user"(role);

-- Composite indexes cho queries phức tạp
CREATE INDEX IF NOT EXISTS idx_inventorysnapshot_product_warehouse ON inventorysnapshot(product_id, warehouse_id);
CREATE INDEX IF NOT EXISTS idx_stockdocument_warehouse_date ON stockdocument(warehouse_id, posting_date);
CREATE INDEX IF NOT EXISTS idx_salesorder_customer_date ON salesorder(customer_id, order_date);
CREATE INDEX IF NOT EXISTS idx_productionorder_product_date ON productionorder(product_id, production_date);
CREATE INDEX IF NOT EXISTS idx_productionplanday_date_product ON productionplanday(production_date, product_id);

-- ============================================
-- 3. Thêm Constraints
-- ============================================

-- CHECK constraints cho enum values
ALTER TABLE product
    ADD CONSTRAINT chk_product_group CHECK ("group" IN ('NVL', 'BTP', 'TP', 'Phu_lieu'));

ALTER TABLE product
    ADD CONSTRAINT chk_product_status CHECK (status IN ('active', 'inactive'));

ALTER TABLE customer
    ADD CONSTRAINT chk_customer_level CHECK (level IN ('A', 'B', 'C', 'Khac'));

ALTER TABLE customer
    ADD CONSTRAINT chk_customer_channel CHECK (channel IN ('GT', 'MT', 'Online', 'Khac'));

ALTER TABLE customer
    ADD CONSTRAINT chk_customer_status CHECK (status IN ('active', 'inactive'));

ALTER TABLE warehouse
    ADD CONSTRAINT chk_warehouse_type CHECK (type IN ('NVL', 'BTP', 'TP', 'Khac'));

ALTER TABLE stockdocument
    ADD CONSTRAINT chk_stockdocument_doc_type CHECK (doc_type IN ('N', 'X'));

ALTER TABLE stocktaking
    ADD CONSTRAINT chk_stocktaking_status CHECK (status IN ('draft', 'locked'));

ALTER TABLE salesorder
    ADD CONSTRAINT chk_salesorder_status CHECK (status IN ('new', 'in_production', 'completed', 'delivered'));

ALTER TABLE salesorder
    ADD CONSTRAINT chk_salesorder_payment_status CHECK (payment_status IN ('unpaid', 'paid', 'partial'));

ALTER TABLE productionorder
    ADD CONSTRAINT chk_productionorder_order_type CHECK (order_type IN ('SP', 'BTP'));

ALTER TABLE productionorder
    ADD CONSTRAINT chk_productionorder_status CHECK (status IN ('new', 'in_production', 'completed', 'stocked'));

ALTER TABLE employee
    ADD CONSTRAINT chk_employee_status CHECK (status IN ('active', 'suspended', 'inactive'));

ALTER TABLE "user"
    ADD CONSTRAINT chk_user_role CHECK (role IN ('admin', 'accountant', 'warehouse', 'production', 'sales'));

-- UNIQUE constraints (một số đã có trong CREATE TABLE, nhưng thêm để chắc chắn)
-- Đã có: product.code, customer.code, warehouse.code, stockdocument.code, etc.

-- NOT NULL constraints cho các trường bắt buộc
ALTER TABLE materialpricehistory
    ALTER COLUMN price SET NOT NULL;

ALTER TABLE materialpricehistory
    ALTER COLUMN quoted_date SET NOT NULL;

ALTER TABLE productionorder
    ALTER COLUMN business_id SET NOT NULL;

-- ============================================
-- 4. Thêm Triggers
-- ============================================

-- Function để cập nhật updated_at tự động
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger cho productionorder.updated_at
CREATE TRIGGER update_productionorder_updated_at
    BEFORE UPDATE ON productionorder
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger cho user.updated_at
CREATE TRIGGER update_user_updated_at
    BEFORE UPDATE ON "user"
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 5. Hoàn thiện schema hiện có
-- ============================================

-- Thêm cột nếu chưa có (safe migration)
DO $$
BEGIN
    -- Thêm qr_code_url vào productionorder nếu chưa có
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'productionorder' AND column_name = 'qr_code_url'
    ) THEN
        ALTER TABLE productionorder ADD COLUMN qr_code_url text;
    END IF;
END $$;

-- Thêm constraint cho inventorysnapshot để đảm bảo unique (product_id, warehouse_id)
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventorysnapshot_unique_product_warehouse
    ON inventorysnapshot(product_id, warehouse_id);

-- Thêm constraint cho productionplanday để đảm bảo unique (production_date, product_id)
CREATE UNIQUE INDEX IF NOT EXISTS idx_productionplanday_unique_date_product
    ON productionplanday(production_date, product_id);

-- ============================================
-- 6. Comments cho documentation
-- ============================================

COMMENT ON TABLE "user" IS 'Bảng user đăng nhập hệ thống, gắn với nhân sự và role';
COMMENT ON COLUMN "user".role IS 'admin, accountant, warehouse, production, sales';
COMMENT ON COLUMN product."group" IS 'NVL: Nguyên vật liệu, BTP: Bán thành phẩm, TP: Thành phẩm, Phu_lieu: Phụ liệu';
COMMENT ON COLUMN stockdocument.doc_type IS 'N: Nhập, X: Xuất';
COMMENT ON COLUMN productionorder.order_type IS 'SP: Sản phẩm, BTP: Bán thành phẩm';
COMMENT ON COLUMN productionorder.status IS 'new: Mới, in_production: Đang SX, completed: Hoàn thành, stocked: Đã NK';

