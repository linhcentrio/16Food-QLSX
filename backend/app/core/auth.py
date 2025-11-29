"""
Auth & RBAC cơ bản cho webapp.

- Dùng cookie session đơn giản (chưa phải JWT/OAuth2).
- Mỗi request có thể đọc user từ cookie và kiểm tra role.
"""

from __future__ import annotations

import hashlib
import hmac

from robyn import Request

from .config import settings
from .db import get_session
from ..models.entities import User


def hash_password(plain: str) -> str:
    """Hash mật khẩu (demo, khuyến nghị dùng bcrypt/argon2 cho production)."""

    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_password(plain), hashed)


def get_current_user(request: Request) -> User | None:
    """Đọc user hiện tại từ cookie `x-user` (demo, chưa mã hóa)."""

    username = request.cookies.get("x-user")  # type: ignore[assignment]
    if not username:
        return None
    with get_session() as db:
        return db.query(User).filter(User.username == username).first()


def require_roles(request: Request, roles: list[str]) -> User | None:
    """Helper kiểm tra quyền; trả về user nếu hợp lệ, None nếu không."""

    user = get_current_user(request)
    if not user or user.role not in roles:
        return None
    return user


