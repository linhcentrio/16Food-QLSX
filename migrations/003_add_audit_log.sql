-- Migration: Thêm bảng audit_log để ghi lại tất cả các thay đổi trong hệ thống

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id UUID REFERENCES "user"(id),
    username VARCHAR(100),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(50),
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    description TEXT
);

-- Tạo indexes để tối ưu query
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity_type ON audit_log(entity_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity_id ON audit_log(entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity_type_id ON audit_log(entity_type, entity_id);

-- Comment
COMMENT ON TABLE audit_log IS 'Bảng audit log - ghi lại tất cả các thay đổi trong hệ thống';
COMMENT ON COLUMN audit_log.action IS 'Hành động: CREATE, UPDATE, DELETE, VIEW';
COMMENT ON COLUMN audit_log.entity_type IS 'Loại entity: Product, Order, Inventory, etc.';
COMMENT ON COLUMN audit_log.entity_id IS 'ID của entity bị thay đổi';

