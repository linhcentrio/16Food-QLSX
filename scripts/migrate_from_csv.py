"""
Script hỗ trợ migrate dữ liệu từ file CSV (export từ Google Sheets) vào DB mới.

Ý tưởng:
- Người dùng export các sheet quan trọng (ví dụ danh mục `san_pham`, `khach_hang`)
  thành file CSV.
- Script đọc CSV, map cột sang model SQLAlchemy tương ứng rồi insert.

Hiện tại minh họa migrate bảng `product` (san_pham) cơ bản.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from backend.app.core.db import get_session  # type: ignore[import]
from backend.app.models.entities import Product  # type: ignore[import]


def load_csv_rows(path: Path) -> Iterable[dict[str, str]]:
  """Đọc file CSV và yield từng dòng dưới dạng dict."""

  with path.open("r", encoding="utf-8-sig", newline="") as f:
      reader = csv.DictReader(f)
      for row in reader:
          yield row


def migrate_products(csv_path: str) -> None:
    """
    Migrate danh mục sản phẩm cơ bản từ CSV.

    Yêu cầu file có tối thiểu các cột:
    - code
    - name
    - group
    - main_uom
    """

    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(path)

    with get_session() as db:
        for row in load_csv_rows(path):
            code = (row.get("code") or "").strip()
            name = (row.get("name") or "").strip()
            group = (row.get("group") or "").strip()
            main_uom = (row.get("main_uom") or "").strip()

            if not code or not name or not group or not main_uom:
                # Bỏ qua dòng thiếu dữ liệu bắt buộc
                continue

            # Nếu đã tồn tại mã sản phẩm thì bỏ qua (tránh trùng lặp)
            existing = db.query(Product).filter_by(code=code).first()
            if existing:
                continue

            product = Product(
                code=code,
                name=name,
                group=group,
                main_uom=main_uom,
            )
            db.add(product)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate danh mục sản phẩm từ CSV vào DB PostgreSQL."
    )
    parser.add_argument(
        "csv_path",
        help="Đường dẫn tới file CSV export từ Google Sheets (danh mục sản phẩm).",
    )

    args = parser.parse_args()
    migrate_products(args.csv_path)
    print("Done migrate products.")


