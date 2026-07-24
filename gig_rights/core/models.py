"""Pydantic v2 domain models and schemas for statutory holiday calculations."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from gig_rights.core.classification import WorkerType


class CalculationMethod(str, Enum):
    """
    Inheriting from (str, Enum) enables clean JSON serialization in FastAPI
    and allows storing human-readable values directly in SQLAlchemy audit logs.
    """

    STATUTORY_ACCRUAL_1207 = "12.07_percent_accrual"
    ROLLED_UP_PAY = "rolled_up_pay"
    REFERENCE_PERIOD_52_WEEKS = "52_week_reference_period"


class PayPeriod(BaseModel):
    """Represents a single pay period with hours worked and earnings."""

    start_date: date
    end_date: date
    hours_worked: Decimal = Field(ge=Decimal("0.0"))
    gross_pay: Decimal = Field(ge=Decimal("0.0"))


class Worker(BaseModel):
    """Worker entitiy used for calculation contexts."""

    id: str
    name: str
    worker_type: WorkerType
    leave_year_start: date


class CalculationResult(BaseModel):
    """Output from a calculator strategy containing audit metadata."""

    # Unique identifier for the worker tied to this calculation record
    worker_id: str
    # Statutory strategy applied (e.g. 12.07% accrual, rolled-up, or 52-week average)
    method_used: CalculationMethod
    # Start date of the pay period evaluated
    pay_period_start: date
    # End date of the pay period evaluated
    pay_period_end: date
    # Statutory holiday hours earned or claimed
    # (Decimal prevents float rounding errors)
    entitlement_hours: Decimal
    # Cash amount due in this period (£0.00 if accruing hours for taking leave later)
    holiday_pay_due: Decimal
    # Structured snapshot (formulas, lookback weeks excluded, rates)
    # for 2026 compliance audits
    audit_metadata: dict[str, Any]
