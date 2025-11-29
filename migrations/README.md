# Database Migrations

Hướng dẫn chạy migrations cho hệ thống QLSX 16Food.

## Thứ tự chạy migrations

1. **001_initial_schema.sql**: Tạo các bảng cơ bản
2. **002_complete_schema.sql**: Hoàn thiện schema với indexes, constraints, triggers và bảng User

## Cách chạy migrations

### Sử dụng psql

```bash
# Kết nối đến database
psql -U qlsx -d qlsx_16food -h localhost

# Chạy migration 001
\i migrations/001_initial_schema.sql

# Chạy migration 002
\i migrations/002_complete_schema.sql
```

### Sử dụng Python script

```bash
python scripts/run_migrations.py
```

### Sử dụng SQLAlchemy Alembic (tương lai)

```bash
alembic upgrade head
```

## Lưu ý

- Backup database trước khi chạy migrations
- Kiểm tra version PostgreSQL (yêu cầu >= 12)
- Đảm bảo extension `uuid-ossp` đã được enable
- Kiểm tra permissions của user database

## Rollback

Để rollback migration 002:

```sql
-- Xóa triggers
DROP TRIGGER IF EXISTS update_productionorder_updated_at ON productionorder;
DROP TRIGGER IF EXISTS update_user_updated_at ON "user";
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Xóa bảng user (nếu cần)
DROP TABLE IF EXISTS "user";

-- Xóa indexes (optional, giữ lại để không ảnh hưởng performance)
-- Các indexes không cần rollback vì không ảnh hưởng data
```

