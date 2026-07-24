"""SQLAlchemy ORM models for workers and immutable append-only audit logs."""

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gig_rights.db.session import Base


class WorkerModel(Base):
    """Worker profile record."""

    __tablename__ = "workers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    worker_type: Mapped[str] = mapped_column(String(50), nullable=False)
    leave_year_start: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationship to append-only audit entries
    audit_logs: Mapped[list["AuditLogModel"]] = relationship(
        "AuditLogModel", back_populates="worker", cascade="all"
    )


class AuditLogModel(Base):
    """
    Append-only statutory audit record for holiday calculations.
    Immutability Constraint: This table is strictly append-only.
    Entries are written when a calculation executes and are never updated or deleted.
    """

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    worker_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workers.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    method_used: Mapped[str] = mapped_column(String(50), nullable=False)
    pay_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    pay_period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Change Numeric(...) to Float for clean SQLite storage
    hours_worked: Mapped[float] = mapped_column(Float, nullable=False)
    gross_pay: Mapped[float] = mapped_column(Float, nullable=False)
    entitlement_hours: Mapped[float] = mapped_column(Float, nullable=False)
    holiday_pay_due: Mapped[float] = mapped_column(Float, nullable=False)

    # Full audit snapshot (formulas, lookback weeks, zero-pay weeks count, rates)
    audit_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    worker: Mapped["WorkerModel"] = relationship(
        "WorkerModel", back_populates="audit_logs"
    )
