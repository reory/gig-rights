"""Statutory 12.07% holiday accrual calculator for irregular & part-year workers."""

from decimal import ROUND_HALF_UP, Decimal

from gig_rights.core.calculators.base import BaseHolidayCalculator
from gig_rights.core.models import (
    CalculationMethod,
    CalculationResult,
    PayPeriod,
    Worker,
)

# Statutory accrual multiplier (5.6 weeks / 46.4 working weeks)
STATUTORY_ACCRUAL_RATE = Decimal("0.1207")


class AccrualCalculator(BaseHolidayCalculator):
    """Calculates statutory holiday hours accrued in a given pay period."""

    def calculate(
        self, worker: Worker, current_period: PayPeriod, **kwargs
    ) -> CalculationResult:
        entitlement_hours = (
            current_period.hours_worked * STATUTORY_ACCRUAL_RATE
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return CalculationResult(
            worker_id=worker.id,
            method_used=CalculationMethod.STATUTORY_ACCRUAL_1207,
            pay_period_start=current_period.start_date,
            pay_period_end=current_period.end_date,
            entitlement_hours=entitlement_hours,
            # Hours accrued; pay issued when leave taken
            holiday_pay_due=Decimal("0.00"),
            audit_metadata={
                "accrual_rate_used": str(STATUTORY_ACCRUAL_RATE),
                "hours_worked": str(current_period.hours_worked),
                "formula": f"{current_period.hours_worked} * {STATUTORY_ACCRUAL_RATE}",
            },
        )
