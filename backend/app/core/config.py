"""
Config chung cho backend Robyn.

- Đọc cấu hình từ biến môi trường (.env) cho DB, secret key...
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Cấu hình ứng dụng backend.

    Sử dụng biến môi trường để dễ triển khai nhiều môi trường.
    """

    app_name: str = "QLSX 16Food"
    debug: bool = os.getenv("APP_DEBUG", "false").lower() == "true"
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production")

    db_path: str = os.getenv("DB_PATH", "data/qlsx_16food.db")

    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN", None)
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID", None)

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Trả về connection string cho SQLite.
        
        SQLite URI format: sqlite:///path/to/database.db
        Hoặc sqlite:///:memory: cho in-memory database
        """
        return f"sqlite:///{self.db_path}"


settings = Settings()


