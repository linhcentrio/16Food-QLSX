-- Initial schema for QLSX 16Food webapp (PostgreSQL)
-- Sinh từ PRD_App_QLSX_16Food, rút gọn cho phase đầu.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Danh mục & CRM

CREATE TABLE product (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    code varchar(50) NOT NULL UNIQUE,
    name varchar(255) NOT NULL,
    "group" varchar(30) NOT NULL,
    specification varchar(255),
    main_uom varchar(20) NOT NULL,
    secondary_uom varchar(20),
    conversion_rate numeric(18,6),
    batch_spec varchar(100),
    shelf_life_days integer,
    status varchar(20) NOT NULL DEFAULT 'active'
);

CREATE TABLE customer (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    code varchar(50) NOT NULL UNIQUE,
    name varchar(255) NOT NULL,
    level varchar(10) NOT NULL,
    channel varchar(20) NOT NULL,
    phone varchar(30),
    email varchar(255),
    address text,
    credit_limit numeric(18,2),
    status varchar(30) NOT NULL DEFAULT 'active'
);

CREATE TABLE supplier (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    code varchar(50) NOT NULL UNIQUE,
    name varchar(255) NOT NULL,
    phone varchar(30),
    email varchar(255),
    address text,
    rating numeric(3,2)
);

CREATE TABLE pricepolicy (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id uuid NOT NULL REFERENCES product(id),
    customer_level varchar(10) NOT NULL,
    price numeric(18,2) NOT NULL,
    effective_date date NOT NULL
);

CREATE TABLE materialpricehistory (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    material_id uuid NOT NULL REFERENCES product(id),
    supplier_id uuid NOT NULL REFERENCES supplier(id),
    price numeric(18,4) NOT NULL,
    quoted_date date NOT NULL,
    note text
);

-- Kho

CREATE TABLE warehouse (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    code varchar(50) NOT NULL UNIQUE,
    name varchar(255) NOT NULL,
    type varchar(20) NOT NULL,
    location varchar(255),
    note text
);

CREATE TABLE inventorysnapshot (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id uuid NOT NULL REFERENCES product(id),
    warehouse_id uuid NOT NULL REFERENCES warehouse(id),
    total_in numeric(18,3) NOT NULL DEFAULT 0,
    total_out numeric(18,3) NOT NULL DEFAULT 0,
    current_qty numeric(18,3) NOT NULL DEFAULT 0,
    inventory_value numeric(18,2) NOT NULL DEFAULT 0
);

CREATE TABLE stockdocument (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    code varchar(50) NOT NULL UNIQUE,
    posting_date date NOT NULL,
    doc_type varchar(10) NOT NULL,
    warehouse_id uuid NOT NULL REFERENCES warehouse(id),
    storekeeper varchar(255),
    partner_name varchar(255),
    description text,
    qr_code_url text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE stockdocumentline (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id uuid NOT NULL REFERENCES stockdocument(id) ON DELETE CASCADE,
    product_id uuid NOT NULL REFERENCES product(id),
    product_name varchar(255) NOT NULL,
    batch_spec varchar(255),
    mfg_date date,
    exp_date date,
    uom varchar(20) NOT NULL,
    quantity numeric(18,3) NOT NULL,
    signed_qty numeric(18,3) NOT NULL
);

CREATE TABLE stocktaking (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    code varchar(50) NOT NULL UNIQUE,
    warehouse_id uuid NOT NULL REFERENCES warehouse(id),
    stocktaking_date date NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'draft'
);

CREATE TABLE stocktakingline (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    stocktaking_id uuid NOT NULL REFERENCES stocktaking(id) ON DELETE CASCADE,
    product_id uuid NOT NULL REFERENCES product(id),
    book_qty numeric(18,3) NOT NULL,
    counted_qty numeric(18,3) NOT NULL,
    difference_qty numeric(18,3) NOT NULL,
    adjustment_created boolean NOT NULL DEFAULT false
);

-- Đơn hàng

CREATE TABLE salesorder (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    code varchar(50) NOT NULL UNIQUE,
    customer_id uuid NOT NULL REFERENCES customer(id),
    order_date date NOT NULL,
    delivery_date date NOT NULL,
    status varchar(30) NOT NULL DEFAULT 'new',
    total_amount numeric(18,2) NOT NULL DEFAULT 0,
    payment_status varchar(20) NOT NULL DEFAULT 'unpaid',
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE salesorderline (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id uuid NOT NULL REFERENCES salesorder(id) ON DELETE CASCADE,
    product_id uuid NOT NULL REFERENCES product(id),
    product_name varchar(255) NOT NULL,
    sales_spec varchar(255),
    uom varchar(20) NOT NULL,
    quantity numeric(18,3) NOT NULL,
    unit_price numeric(18,2) NOT NULL,
    line_amount numeric(18,2) NOT NULL,
    batch_spec varchar(100)
);

-- Kế hoạch sản xuất & Lệnh sản xuất

CREATE TABLE productionplanday (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    production_date date NOT NULL,
    product_id uuid NOT NULL REFERENCES product(id),
    planned_qty numeric(18,3) NOT NULL,
    ordered_qty numeric(18,3) NOT NULL DEFAULT 0,
    remaining_qty numeric(18,3) NOT NULL DEFAULT 0,
    capacity_max numeric(18,3) NOT NULL
);

CREATE TABLE productionorder (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id varchar(50) NOT NULL UNIQUE,
    production_date date NOT NULL,
    order_type varchar(20) NOT NULL,
    product_id uuid NOT NULL REFERENCES product(id),
    product_name varchar(255) NOT NULL,
    planned_qty numeric(18,3) NOT NULL,
    completed_qty numeric(18,3) NOT NULL DEFAULT 0,
    expected_diff_qty numeric(18,3) NOT NULL DEFAULT 0,
    status varchar(20) NOT NULL DEFAULT 'new',
    note text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE productionorderline (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    production_order_id uuid NOT NULL REFERENCES productionorder(id) ON DELETE CASCADE,
    product_id uuid NOT NULL REFERENCES product(id),
    product_name varchar(255) NOT NULL,
    batch_spec varchar(100),
    batch_count numeric(18,3),
    uom varchar(20) NOT NULL,
    planned_qty numeric(18,3) NOT NULL,
    actual_qty numeric(18,3) NOT NULL DEFAULT 0,
    expected_loss numeric(18,3),
    actual_loss numeric(18,3),
    note text
);

-- BOM

CREATE TABLE bommaterial (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id uuid NOT NULL REFERENCES product(id),
    material_id uuid NOT NULL REFERENCES product(id),
    quantity numeric(18,6) NOT NULL,
    uom varchar(20) NOT NULL,
    cost numeric(18,4),
    effective_date date
);

CREATE TABLE bomlabor (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id uuid NOT NULL REFERENCES product(id),
    equipment varchar(100),
    labor_type varchar(100),
    quantity numeric(18,3),
    duration_minutes integer,
    unit_cost numeric(18,4)
);

CREATE TABLE bomsemiproduct (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    semi_product_id uuid NOT NULL REFERENCES product(id),
    component_id uuid NOT NULL REFERENCES product(id),
    quantity numeric(18,6) NOT NULL,
    uom varchar(20) NOT NULL,
    operation_sequence integer
);

-- HCNS

CREATE TABLE department (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    code varchar(50) NOT NULL UNIQUE,
    name varchar(255) NOT NULL
);

CREATE TABLE jobtitle (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name varchar(255) NOT NULL,
    base_salary numeric(18,2)
);

CREATE TABLE employee (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    code varchar(50) NOT NULL UNIQUE,
    full_name varchar(255) NOT NULL,
    department_id uuid NOT NULL REFERENCES department(id),
    job_title_id uuid NOT NULL REFERENCES jobtitle(id),
    join_date date NOT NULL,
    leave_date date,
    status varchar(20) NOT NULL DEFAULT 'active'
);

CREATE TABLE timesheet (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_date date NOT NULL,
    employee_id uuid NOT NULL REFERENCES employee(id),
    shift varchar(50),
    working_hours numeric(5,2) NOT NULL DEFAULT 0,
    overtime_hours numeric(5,2) NOT NULL DEFAULT 0
);


