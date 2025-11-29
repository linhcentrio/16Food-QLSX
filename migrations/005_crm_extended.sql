-- Migration 005: Thêm các bảng cho CRM mở rộng

-- ============================================
-- 1. CÔNG NỢ
-- ============================================

CREATE TABLE IF NOT EXISTS accounts_receivable (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id uuid NOT NULL REFERENCES customer(id),
    sales_order_id uuid REFERENCES salesorder(id),
    transaction_date date NOT NULL,
    due_date date NOT NULL,
    invoice_number varchar(50),
    amount numeric(18,2) NOT NULL,
    paid_amount numeric(18,2) NOT NULL DEFAULT 0,
    remaining_amount numeric(18,2) NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'unpaid',
    payment_terms varchar(50),
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS accounts_payable (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id uuid NOT NULL REFERENCES supplier(id),
    purchase_order_id uuid REFERENCES purchase_order(id),
    transaction_date date NOT NULL,
    due_date date NOT NULL,
    invoice_number varchar(50),
    amount numeric(18,2) NOT NULL,
    paid_amount numeric(18,2) NOT NULL DEFAULT 0,
    remaining_amount numeric(18,2) NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'unpaid',
    payment_terms varchar(50),
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================
-- 2. HỢP ĐỒNG VÀ ĐÁNH GIÁ NHÀ CUNG CẤP
-- ============================================

CREATE TABLE IF NOT EXISTS supplier_contract (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id uuid NOT NULL REFERENCES supplier(id),
    contract_number varchar(50) NOT NULL UNIQUE,
    contract_type varchar(50) NOT NULL,
    start_date date NOT NULL,
    end_date date,
    payment_terms varchar(100),
    delivery_terms varchar(100),
    quality_requirements text,
    penalty_clause text,
    contract_terms text,
    status varchar(20) NOT NULL DEFAULT 'active',
    file_url text,
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS supplier_evaluation (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id uuid NOT NULL REFERENCES supplier(id),
    contract_id uuid REFERENCES supplier_contract(id),
    evaluation_date date NOT NULL,
    evaluation_period_start date NOT NULL,
    evaluation_period_end date NOT NULL,
    evaluated_by varchar(255),
    quality_score numeric(5,2),
    delivery_score numeric(5,2),
    price_score numeric(5,2),
    service_score numeric(5,2),
    overall_score numeric(5,2) NOT NULL,
    on_time_delivery_rate numeric(5,2),
    defect_rate numeric(5,2),
    total_orders integer,
    total_value numeric(18,2),
    rating varchar(20) NOT NULL,
    comments text,
    recommendations text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================
-- 3. PHÂN KHÚC VÀ PHẢN HỒI KHÁCH HÀNG
-- ============================================

CREATE TABLE IF NOT EXISTS customer_segment (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(50) NOT NULL UNIQUE,
    name varchar(255) NOT NULL,
    description text,
    criteria text,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customer_feedback (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id uuid NOT NULL REFERENCES customer(id),
    sales_order_id uuid REFERENCES salesorder(id),
    feedback_date date NOT NULL,
    feedback_type varchar(50) NOT NULL,
    category varchar(50),
    rating integer,
    subject varchar(255),
    content text NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'new',
    assigned_to varchar(255),
    resolution text,
    resolved_date date,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================
-- 4. KPI TRACKING
-- ============================================

CREATE TABLE IF NOT EXISTS kpi_metric (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(50) NOT NULL UNIQUE,
    name varchar(255) NOT NULL,
    category varchar(50) NOT NULL,
    unit varchar(20),
    target_value numeric(18,2),
    current_value numeric(18,2),
    calculation_formula text,
    is_active boolean NOT NULL DEFAULT true,
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS kpi_record (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kpi_metric_id uuid NOT NULL REFERENCES kpi_metric(id),
    record_date date NOT NULL,
    period_type varchar(20) NOT NULL,
    value numeric(18,2) NOT NULL,
    target_value numeric(18,2),
    variance numeric(18,2),
    variance_percentage numeric(5,2),
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================
-- 5. INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_accounts_receivable_customer_id ON accounts_receivable(customer_id);
CREATE INDEX IF NOT EXISTS idx_accounts_receivable_sales_order_id ON accounts_receivable(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_accounts_receivable_status ON accounts_receivable(status);
CREATE INDEX IF NOT EXISTS idx_accounts_receivable_due_date ON accounts_receivable(due_date);

CREATE INDEX IF NOT EXISTS idx_accounts_payable_supplier_id ON accounts_payable(supplier_id);
CREATE INDEX IF NOT EXISTS idx_accounts_payable_status ON accounts_payable(status);
CREATE INDEX IF NOT EXISTS idx_accounts_payable_due_date ON accounts_payable(due_date);

CREATE INDEX IF NOT EXISTS idx_supplier_contract_supplier_id ON supplier_contract(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_contract_status ON supplier_contract(status);
CREATE INDEX IF NOT EXISTS idx_supplier_evaluation_supplier_id ON supplier_evaluation(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_evaluation_contract_id ON supplier_evaluation(contract_id);

CREATE INDEX IF NOT EXISTS idx_customer_feedback_customer_id ON customer_feedback(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_feedback_status ON customer_feedback(status);
CREATE INDEX IF NOT EXISTS idx_customer_feedback_type ON customer_feedback(feedback_type);

CREATE INDEX IF NOT EXISTS idx_kpi_metric_category ON kpi_metric(category);
CREATE INDEX IF NOT EXISTS idx_kpi_record_kpi_metric_id ON kpi_record(kpi_metric_id);
CREATE INDEX IF NOT EXISTS idx_kpi_record_record_date ON kpi_record(record_date);
CREATE INDEX IF NOT EXISTS idx_kpi_record_period_type ON kpi_record(period_type);

-- Comments
COMMENT ON TABLE accounts_receivable IS 'Bảng công nợ phải thu';
COMMENT ON TABLE accounts_payable IS 'Bảng công nợ phải trả';
COMMENT ON TABLE supplier_contract IS 'Bảng hợp đồng nhà cung cấp';
COMMENT ON TABLE supplier_evaluation IS 'Bảng đánh giá nhà cung cấp';
COMMENT ON TABLE customer_feedback IS 'Bảng phản hồi khách hàng';
COMMENT ON TABLE kpi_metric IS 'Bảng KPI metrics';
COMMENT ON TABLE kpi_record IS 'Bảng ghi nhận KPI';

