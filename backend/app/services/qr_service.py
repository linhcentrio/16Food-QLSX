"""
Service tạo QR code cho LSX và phiếu kho.
"""

from __future__ import annotations

import io
import json
import base64

try:
    import qrcode
    from qrcode.image.pil import PilImage
except ImportError:
    qrcode = None
    PilImage = None


def generate_qr_code_image(data: str, size: int = 10, border: int = 4) -> bytes:
    """
    Tạo QR code image từ dữ liệu text.
    
    Args:
        data: Nội dung QR code (text hoặc JSON string)
        size: Kích thước QR code (1-40, default: 10)
        border: Border size (default: 4)
    
    Returns:
        Bytes của image PNG
    """
    if qrcode is None:
        raise ImportError(
            "qrcode library chưa được cài đặt. Chạy: pip install qrcode[pil]"
        )
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    
    return img_bytes.read()


def generate_qr_code_base64(data: str, size: int = 10, border: int = 4) -> str:
    """
    Tạo QR code và trả về dưới dạng base64 string.
    
    Args:
        data: Nội dung QR code
        size: Kích thước QR code
        border: Border size
    
    Returns:
        Base64 string của image PNG
    """
    img_bytes = generate_qr_code_image(data, size, border)
    return base64.b64encode(img_bytes).decode("utf-8")


def generate_qr_code_data_url(data: str, size: int = 10, border: int = 4) -> str:
    """
    Tạo QR code và trả về dưới dạng data URL (có thể dùng trực tiếp trong HTML).
    
    Args:
        data: Nội dung QR code
        size: Kích thước QR code
        border: Border size
    
    Returns:
        Data URL string (data:image/png;base64,...)
    """
    base64_str = generate_qr_code_base64(data, size, border)
    return f"data:image/png;base64,{base64_str}"


def create_production_order_qr_data(
    production_order_id: str,
    business_id: str,
    production_date: str,
    product_name: str,
) -> str:
    """
    Tạo dữ liệu JSON cho QR code của LSX.
    
    Args:
        production_order_id: UUID của LSX
        business_id: Mã LSX (LSX-yyyyMMdd-xxx)
        production_date: Ngày sản xuất (YYYY-MM-DD)
        product_name: Tên sản phẩm
    
    Returns:
        JSON string
    """
    data = {
        "type": "production_order",
        "id": production_order_id,
        "business_id": business_id,
        "production_date": production_date,
        "product_name": product_name,
    }
    return json.dumps(data, ensure_ascii=False)


def create_stock_document_qr_data(
    document_code: str,
    doc_type: str,
    posting_date: str,
    warehouse_code: str,
) -> str:
    """
    Tạo dữ liệu JSON cho QR code của phiếu kho.
    
    Args:
        document_code: Mã phiếu (PNxxxx/PXxxxx)
        doc_type: Loại phiếu (N/X)
        posting_date: Ngày phiếu (YYYY-MM-DD)
        warehouse_code: Mã kho
    
    Returns:
        JSON string
    """
    data = {
        "type": "stock_document",
        "code": document_code,
        "doc_type": doc_type,
        "posting_date": posting_date,
        "warehouse_code": warehouse_code,
    }
    return json.dumps(data, ensure_ascii=False)

