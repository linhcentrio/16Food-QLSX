"""
Models mở rộng cho Module HCNS.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, Date, DateTime, Boolean, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, uuid_pk


class EmploymentContract(Base):
    """Bảng hợp đồng lao động."""

    __tablename__ = "employment_contract"

    id: Mapped[uuid.UUID] = uuid_pk()
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employee.id"), index=True
    )
    contract_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    contract_type: Mapped[str] = mapped_column(String(50))  # Full-time, Part-time, Contract, Intern
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    salary: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, expired, terminated
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    employee: Mapped["Employee"] = relationship()


class PerformanceReview(Base):
    """Bảng đánh giá hiệu suất làm việc."""

    __tablename__ = "performance_review"

    id: Mapped[uuid.UUID] = uuid_pk()
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employee.id"), index=True
    )
    review_period_start: Mapped[date] = mapped_column(Date)
    review_period_end: Mapped[date] = mapped_column(Date)
    review_date: Mapped[date] = mapped_column(Date)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Điểm đánh giá
    work_quality_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100
    productivity_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    teamwork_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    communication_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    overall_score: Mapped[float] = mapped_column(Numeric(5, 2))
    
    rating: Mapped[str] = mapped_column(String(20))  # Excellent, Good, Satisfactory, Needs Improvement
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    areas_for_improvement: Mapped[str | None] = mapped_column(Text, nullable=True)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    employee: Mapped["Employee"] = relationship()


class TrainingRecord(Base):
    """Bảng ghi nhận đào tạo."""

    __tablename__ = "training_record"

    id: Mapped[uuid.UUID] = uuid_pk()
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employee.id"), index=True
    )
    training_name: Mapped[str] = mapped_column(String(255))
    training_type: Mapped[str] = mapped_column(String(50))  # Internal, External, Online, On-the-job
    training_date: Mapped[date] = mapped_column(Date)
    duration_hours: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    trainer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    certificate_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")  # planned, in_progress, completed, cancelled
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    employee: Mapped["Employee"] = relationship()


class ExitProcess(Base):
    """Bảng quy trình nghỉ việc."""

    __tablename__ = "exit_process"

    id: Mapped[uuid.UUID] = uuid_pk()
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employee.id"), index=True
    )
    resignation_date: Mapped[date] = mapped_column(Date)
    last_working_date: Mapped[date] = mapped_column(Date)
    exit_type: Mapped[str] = mapped_column(String(50))  # Resignation, Termination, Retirement, End of Contract
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    exit_interview_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exit_interview_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    handover_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    handover_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assets_returned: Mapped[bool] = mapped_column(Boolean, default=False)
    final_settlement: Mapped[bool] = mapped_column(Boolean, default=False)
    final_settlement_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="initiated")  # initiated, in_progress, completed
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    employee: Mapped["Employee"] = relationship()

