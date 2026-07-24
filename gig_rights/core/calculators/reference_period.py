"""52-week reference period calculator with statutory zero-pay week exclusion."""

from decimal import ROUND_HALF_UP, Decimal
from typing import List

from gig_rights.core.calculators.base import BaseHolidayCalculator
from gig_rights.core.models import (
    CalculationMethod,
    CalculationResult,
    PayPeriod,
    Worker,
)


class ReferencePeriodCalculator(BaseHolidayCalculator):
    """Calculates holiday pay rate based on the 52-week average earnings rule."""

    def calculate(
        self, worker: Worker, current_period: PayPeriod, **kwargs
    ) -> CalculationResult:

        historical_periods: List[PayPeriod] = kwargs.get("historical_periods", [])
        requested_leave_hours: Decimal = kwargs.get(
            "requested_leave_hours", Decimal("0.0")
        )

        # Statutory rule:
        # Exclude weeks with zero remuneration (going back up to 104 weeks max)
        eligible_periods = [p for p in historical_periods if p.gross_pay > 0][:52]

        if not eligible_periods:
            raise ValueError(
                "Insufficient earning history to evaluate 52-week reference period."
            )
        # Sums all gross pay across eligible weeks, starting from a Decimal zero
        total_earnings = sum((p.gross_pay for p in eligible_periods), Decimal("0.0"))
        # Sums all hours worked across eligible weeks, starting from a Decimal zero
        total_hours = sum((p.hours_worked for p in eligible_periods), Decimal("0.0"))
        # Calculates average hourly pay rate with 4-decimal precision,
        # guarded against division-by-zero
        average_hourly_rate = (
            (total_earnings / total_hours).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
            if total_hours > 0
            else Decimal("0.0000")
        )
        # Calculates total holiday cash pay due, rounded to standard
        # 2-decimal currency (£.p)
        holiday_pay_due = (requested_leave_hours * average_hourly_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return CalculationResult(
            worker_id=worker.id,
            method_used=CalculationMethod.REFERENCE_PERIOD_52_WEEKS,
            pay_period_start=current_period.start_date,
            pay_period_end=current_period.end_date,
            entitlement_hours=requested_leave_hours,
            holiday_pay_due=holiday_pay_due,
            audit_metadata={
                "weeks_evaluated_count": len(eligible_periods),
                "total_lookback_earnings": str(total_earnings),
                "total_lookback_hours": str(total_hours),
                "derived_hourly_rate": str(average_hourly_rate),
                "zero_pay_weeks_excluded": len(historical_periods)
                - len(eligible_periods),
            },
        )
