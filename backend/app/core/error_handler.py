"""
Error handling và logging nâng cao cho backend.
"""

from __future__ import annotations

import json
import logging
import traceback
from functools import wraps
from typing import Callable, Any

from robyn import Request, Response

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base exception cho ứng dụng."""

    def __init__(self, message: str, status_code: int = 500, error_code: str | None = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(AppError):
    """Lỗi validation dữ liệu."""

    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        super().__init__(message, status_code=400, error_code=error_code)


class NotFoundError(AppError):
    """Lỗi không tìm thấy resource."""

    def __init__(self, message: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(message, status_code=404, error_code=error_code)


class UnauthorizedError(AppError):
    """Lỗi không có quyền truy cập."""

    def __init__(self, message: str = "Unauthorized", error_code: str = "UNAUTHORIZED"):
        super().__init__(message, status_code=401, error_code=error_code)


class ForbiddenError(AppError):
    """Lỗi bị cấm truy cập."""

    def __init__(self, message: str = "Forbidden", error_code: str = "FORBIDDEN"):
        super().__init__(message, status_code=403, error_code=error_code)


def error_response(error: AppError | Exception) -> Response:
    """Tạo response từ exception."""
    if isinstance(error, AppError):
        status_code = error.status_code
        error_data = {
            "error": error.message,
            "error_code": error.error_code or "UNKNOWN_ERROR",
        }
    else:
        status_code = 500
        error_data = {
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        }
        logger.exception("Unhandled exception: %s", error)

    return Response(
        status_code=status_code,
        headers={"Content-Type": "application/json"},
        body=json.dumps(error_data, ensure_ascii=False),
    )


def handle_errors(func: Callable) -> Callable:
    """Decorator để handle errors trong API handlers."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Response:
        try:
            result = await func(*args, **kwargs)
            return result
        except AppError as e:
            logger.warning("AppError: %s", e.message, exc_info=True)
            return error_response(e)
        except Exception as e:
            logger.error("Unhandled error in %s: %s", func.__name__, str(e), exc_info=True)
            return error_response(e)

    return wrapper


def json_response(data: object, status_code: int = 200) -> Response:
    """Helper function để tạo JSON response."""
    return Response(
        status_code=status_code,
        headers={"Content-Type": "application/json"},
        body=json.dumps(data, default=str, ensure_ascii=False),
    )


def log_request(request: Request, response: Response | None = None) -> None:
    """Log request và response."""
    logger.info(
        "%s %s - Status: %s",
        request.method,
        request.url.path,
        response.status_code if response else "N/A",
    )

