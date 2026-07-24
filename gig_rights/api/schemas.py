"""Pydantic request and response schemas for the REST API."""

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from gig_rights.core.classification import WorkerType
from gig_rights.core.models import CalculationMethod, PayPeriod


class CalculationRequest(BaseModel):
    """Payload to trigger a statutory calculation and append to audit log."""

    worker_id: str = Field(..., description="Unique UUID or reference for the worker")
    worker_name: str = Field(..., description="Worker display name")
    worker_type: WorkerType
    leave_year_start: date

    method: CalculationMethod
    current_period: PayPeriod

    # Required only if method == CalculationMethod.REFERENCE_PERIOD_52_WEEK
    requested_leave_hours: Decimal | None = Field(
        default=Decimal("0.0"),
        description="Hours of leave requested for 52-week lookback calculation",
    )
    historical_periods: list[PayPeriod] | None = Field(
        default_factory=list,
        description="Historical pay periods (up to 104 weeks) for 52-week average calculation",
    )


class AuditLogResponse(BaseModel):
    """Immutable audit record representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    worker_id: str
    created_at: str
    method_used: str
    pay_period_start: date
    pay_period_end: date
    hours_worked: Decimal
    gross_pay: Decimal
    entitlement_hours: Decimal
    holiday_pay_due: Decimal
    audit_metadata: dict[str, Any]
