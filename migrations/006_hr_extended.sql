-- Migration 006: Thêm các bảng cho HCNS mở rộng

CREATE TABLE IF NOT EXISTS employment_contract (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id uuid NOT NULL REFERENCES employee(id),
    contract_number varchar(50) NOT NULL UNIQUE,
    contract_type varchar(50) NOT NULL,
    start_date date NOT NULL,
    end_date date,
    salary numeric(18,2),
    position varchar(255),
    department varchar(255),
    status varchar(20) NOT NULL DEFAULT 'active',
    file_url text,
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS performance_review (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id uuid NOT NULL REFERENCES employee(id),
    review_period_start date NOT NULL,
    review_period_end date NOT NULL,
    review_date date NOT NULL,
    reviewed_by varchar(255),
    work_quality_score numeric(5,2),
    productivity_score numeric(5,2),
    teamwork_score numeric(5,2),
    communication_score numeric(5,2),
    overall_score numeric(5,2) NOT NULL,
    rating varchar(20) NOT NULL,
    strengths text,
    areas_for_improvement text,
    goals text,
    comments text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS training_record (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id uuid NOT NULL REFERENCES employee(id),
    training_name varchar(255) NOT NULL,
    training_type varchar(50) NOT NULL,
    training_date date NOT NULL,
    duration_hours numeric(5,2),
    trainer varchar(255),
    location varchar(255),
    certificate_number varchar(100),
    score numeric(5,2),
    status varchar(20) NOT NULL DEFAULT 'completed',
    description text,
    file_url text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS exit_process (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id uuid NOT NULL REFERENCES employee(id),
    resignation_date date NOT NULL,
    last_working_date date NOT NULL,
    exit_type varchar(50) NOT NULL,
    reason text,
    exit_interview_date date,
    exit_interview_notes text,
    handover_completed boolean NOT NULL DEFAULT false,
    handover_notes text,
    assets_returned boolean NOT NULL DEFAULT false,
    final_settlement boolean NOT NULL DEFAULT false,
    final_settlement_amount numeric(18,2),
    status varchar(20) NOT NULL DEFAULT 'initiated',
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_employment_contract_employee_id ON employment_contract(employee_id);
CREATE INDEX IF NOT EXISTS idx_employment_contract_status ON employment_contract(status);
CREATE INDEX IF NOT EXISTS idx_performance_review_employee_id ON performance_review(employee_id);
CREATE INDEX IF NOT EXISTS idx_training_record_employee_id ON training_record(employee_id);
CREATE INDEX IF NOT EXISTS idx_exit_process_employee_id ON exit_process(employee_id);
CREATE INDEX IF NOT EXISTS idx_exit_process_status ON exit_process(status);

COMMENT ON TABLE employment_contract IS 'Bảng hợp đồng lao động';
COMMENT ON TABLE performance_review IS 'Bảng đánh giá hiệu suất';
COMMENT ON TABLE training_record IS 'Bảng ghi nhận đào tạo';
COMMENT ON TABLE exit_process IS 'Bảng quy trình nghỉ việc';

