"""
Service để ghi audit log.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..models.audit import AuditLog
from ..models.entities import User

logger = logging.getLogger(__name__)


def create_audit_log(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    user_id: str | None = None,
    username: str | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    description: str | None = None,
) -> AuditLog | None:
    """Tạo audit log entry."""
    try:
        audit_log = AuditLog(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
        )
        db.add(audit_log)
        db.flush()
        return audit_log
    except Exception as e:
        logger.error("Failed to create audit log: %s", str(e), exc_info=True)
        # Không throw exception để không làm gián đoạn business logic
        return None


def get_audit_logs(
    db: Session,
    entity_type: str | None = None,
    entity_id: str | None = None,
    user_id: str | None = None,
    action: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    """Lấy danh sách audit logs với filters."""
    query = db.query(AuditLog)

    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)

    return query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset).all()

