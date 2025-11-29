"""
Service xử lý thông báo (Telegram, Email, etc.).

Bao gồm:
- Telegram notification
- Email notification (có thể mở rộng sau)
"""

from __future__ import annotations

import logging
from datetime import datetime

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from ..core.config import settings

logger = logging.getLogger(__name__)


def send_telegram_notification(message: str) -> bool:
    """
    Gửi thông báo qua Telegram.
    
    Args:
        message: Nội dung tin nhắn
    
    Returns:
        True nếu gửi thành công, False nếu có lỗi
    """
    if not HTTPX_AVAILABLE:
        logger.warning("httpx chưa được cài đặt, không thể gửi Telegram notification")
        return False
    
    # Lấy config từ settings
    bot_token = getattr(settings, "telegram_bot_token", None)
    chat_id = getattr(settings, "telegram_chat_id", None)
    
    if not bot_token or not chat_id:
        logger.warning("Telegram bot token hoặc chat ID chưa được cấu hình")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            
            logger.info("Đã gửi thông báo Telegram thành công")
            return True
    except Exception as e:
        logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
        return False


def format_order_notification(
    order_code: str,
    customer_name: str,
    product_names: str,
    total_qty: float,
    delivery_date: str,
    total_amount: float,
    creator: str | None = None,
) -> str:
    """
    Định dạng thông báo đơn hàng mới cho Telegram.
    
    Args:
        order_code: Mã đơn hàng
        customer_name: Tên khách hàng
        product_names: Tên các sản phẩm (có thể là danh sách)
        total_qty: Tổng số lượng
        delivery_date: Hạn giao hàng
        total_amount: Thành tiền
        creator: Người tạo đơn hàng
    
    Returns:
        Chuỗi thông báo đã định dạng
    """
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    creator_text = creator or "Hệ thống"
    
    message = (
        f"Vào lúc {now}, {creator_text} đã tạo thành công đơn hàng \"{order_code}\" "
        f"của khách hàng \"{customer_name}\" có các sản phẩm {product_names}; "
        f"số lượng đặt hàng {total_qty}; hạn giao hàng {delivery_date}; "
        f"Thành tiền {total_amount:,.0f} vnd. "
        f"Hãy vào AppSheet mục đơn hàng để biết thêm chi tiết."
    )
    
    return message

