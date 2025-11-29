"""
Models cho Module Chất Lượng (Quality).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, Date, DateTime, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, uuid_pk


class NonConformity(Base):
    """Bảng sự không phù hợp."""

    __tablename__ = "non_conformity"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    detected_date: Mapped[date] = mapped_column(Date)
    detected_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    production_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("productionorder.id"), nullable=True, index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product.id"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(50))  # Sản phẩm, Quy trình, Hệ thống
    severity: Mapped[str] = mapped_column(String(20))  # Critical, Major, Minor
    description: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="detected"
    )  # detected, analyzing, action_planned, action_taken, verified, closed
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    production_order: Mapped["ProductionOrder | None"] = relationship()
    product: Mapped["Product | None"] = relationship()
    actions: Mapped[list["NonConformityAction"]] = relationship(
        back_populates="non_conformity", cascade="all, delete-orphan"
    )


class NonConformityAction(Base):
    """Bảng hành động khắc phục sự không phù hợp."""

    __tablename__ = "non_conformity_action"

    id: Mapped[uuid.UUID] = uuid_pk()
    non_conformity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("non_conformity.id"), index=True
    )
    action_type: Mapped[str] = mapped_column(String(50))  # Corrective, Preventive
    description: Mapped[str] = mapped_column(Text)
    responsible_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="planned"
    )  # planned, in_progress, completed, verified
    effectiveness: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # Effective, Partially Effective, Not Effective
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    non_conformity: Mapped[NonConformity] = relationship(back_populates="actions")


class IsoDocument(Base):
    """Bảng tài liệu ISO."""

    __tablename__ = "iso_document"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[str] = mapped_column(String(50))  # Procedure, Policy, Form, Record
    iso_standard: Mapped[str | None] = mapped_column(String(50), nullable=True)  # ISO 9001, ISO 22000, etc.
    version: Mapped[str] = mapped_column(String(20))
    effective_date: Mapped[date] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="draft"
    )  # draft, review, approved, active, obsolete
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    versions: Mapped[list["IsoDocumentVersion"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class IsoDocumentVersion(Base):
    """Bảng phiên bản tài liệu ISO."""

    __tablename__ = "iso_document_version"

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("iso_document.id"), index=True
    )
    version: Mapped[str] = mapped_column(String(20))
    effective_date: Mapped[date] = mapped_column(Date)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    document: Mapped[IsoDocument] = relationship(back_populates="versions")

