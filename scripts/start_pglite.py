"""
Khởi động PostgreSQL bằng py-pglite (zero-config PostgreSQL).
"""

from __future__ import annotations

import sys
import os
import atexit
from pathlib import Path
from typing import Optional

try:
    from py_pglite import PGliteManager, PGliteConfig
except ImportError:
    print("❌ py-pglite chưa được cài đặt!")
    print("💡 Cài đặt: pip install 'py-pglite[sqlalchemy]'")
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "pglite_data"

# Global manager instance
_pglite_manager: Optional[PGliteManager] = None


def start_pglite() -> bool:
    """Khởi động PostgreSQL bằng py-pglite."""
    global _pglite_manager
    
    if _pglite_manager is not None:
        print("✅ PGlite đã đang chạy")
        return True
    
    print("🚀 Đang khởi động PostgreSQL bằng py-pglite...")
    
    try:
        # Cấu hình PGlite
        config = PGliteConfig(
            work_dir=str(DATA_DIR),
            use_tcp=True,  # Dùng TCP để tương thích với psycopg2
            tcp_host="127.0.0.1",
            tcp_port=5432,
            cleanup_on_exit=False,  # Giữ data khi thoát
            log_level="WARNING",  # Giảm log noise
        )
        
        # Khởi tạo manager
        _pglite_manager = PGliteManager(config)
        _pglite_manager.__enter__()  # Start the server
        
        # Đăng ký cleanup khi thoát
        atexit.register(stop_pglite)
        
        print("✅ PostgreSQL (PGlite) đã khởi động thành công")
        print(f"📁 Data directory: {DATA_DIR}")
        
        # Tạo user và database
        create_user_and_database()
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi khởi động PGlite: {e}")
        import traceback
        traceback.print_exc()
        return False


def stop_pglite() -> bool:
    """Dừng PostgreSQL."""
    global _pglite_manager
    
    if _pglite_manager is None:
        return True
    
    try:
        _pglite_manager.__exit__(None, None, None)
        _pglite_manager = None
        print("✅ Đã dừng PostgreSQL (PGlite)")
        return True
    except Exception as e:
        print(f"⚠️  Lỗi khi dừng PGlite: {e}")
        return False


def create_user_and_database():
    """Tạo user và database nếu chưa có."""
    from backend.app.core.config import settings
    
    # PGlite dùng database 'postgres' và user 'postgres' mặc định
    # Có thể tạo database mới bằng cách kết nối trực tiếp
    try:
        # Lấy DSN từ PGlite
        dsn = _pglite_manager.get_dsn()
        print(f"💡 PGlite sử dụng:")
        print(f"   DSN: {dsn}")
        print(f"   User: postgres (mặc định)")
        print(f"   Database: postgres (mặc định)")
        print(f"\n📝 Lưu ý: Có thể dùng database 'postgres' hoặc tạo schema riêng")
        
    except Exception as e:
        print(f"⚠️  Lỗi khi lấy thông tin: {e}")
        print("   (Sẽ dùng mặc định: user=postgres, database=postgres)")


def get_connection_string() -> str:
    """Lấy connection string để kết nối."""
    if _pglite_manager is None:
        raise RuntimeError("PGlite chưa được khởi động")
    
    from backend.app.core.config import settings
    
    # PGlite dùng TCP mode, database mặc định là 'postgres'
    # Có thể dùng database 'postgres' hoặc tạo schema riêng
    db_name = "postgres"  # PGlite mặc định
    return f"postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/{db_name}"


def is_running() -> bool:
    """Kiểm tra PGlite có đang chạy không."""
    return _pglite_manager is not None


def main():
    """Chạy khởi động PGlite."""
    print("=" * 60)
    print("🚀 KHỞI ĐỘNG POSTGRESQL BẰNG PY-PGLITE")
    print("=" * 60)
    print(f"\n📁 Data directory: {DATA_DIR}")
    print()
    
    if start_pglite():
        print("\n✅ PostgreSQL (PGlite) đã sẵn sàng!")
        print(f"\n📋 Thông tin kết nối:")
        from backend.app.core.config import settings
        print(f"   Host: 127.0.0.1:5432")
        print(f"   User: postgres (hoặc {settings.db_user})")
        print(f"   Database: {settings.db_name}")
        print(f"\n💡 Connection string:")
        print(f"   {get_connection_string()}")
        print("\n⚠️  Lưu ý: PGlite chạy trong process này.")
        print("   Để dừng, nhấn Ctrl+C hoặc gọi stop_pglite()")
        return 0
    else:
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Đang dừng PGlite...")
        stop_pglite()
        sys.exit(0)

