"""Rolled-up holiday pay uplift calculator with legal compliance guards."""

from decimal import ROUND_HALF_UP, Decimal

from loguru import logger

from gig_rights.core.calculators.base import BaseHolidayCalculator
from gig_rights.core.classification import WorkerType
from gig_rights.core.models import (
    CalculationMethod,
    CalculationResult,
    PayPeriod,
    Worker,
)

STATUTORY_ACCRUAL_RATE = Decimal("0.1207")


class RolledUpPayCalculator(BaseHolidayCalculator):
    """Calculates rolled-up holiday pay uplift (12.07% on gross pay).

    Statutory Guard: Unlawful for regular fixed-hours workers.
    """

    def calculate(
        self, worker: Worker, current_period: PayPeriod, **kwargs
    ) -> CalculationResult:
        if worker.worker_type == WorkerType.REGULAR_FIXED:
            logger.warning(
                f"COMPLIANCE GUARD TRIGGERED | Worker: {worker.id} | "
                "Attempted rolled-up pay calculation for REGULAR_FIXED worker."
            )
            raise ValueError(
                "Rolled-up holiday pay is unlawful for fixed-hours workers."
            )

        # Calculates statutory holiday hours earned in the pay period,
        # rounded to 2 decimal places
        entitlement_hours = (
            current_period.hours_worked * STATUTORY_ACCRUAL_RATE
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Calculates rolled-up holiday pay cash uplift (12.07% on gross pay)
        # for the pay period
        rolled_up_pay = (current_period.gross_pay * STATUTORY_ACCRUAL_RATE).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        logger.info(
            f"Calculated rolled-up pay | Worker: {worker.id} | "
            f"Gross Pay: £{current_period.gross_pay:.2f} -> Uplift: £{rolled_up_pay} | "
            f"Entitlement: {entitlement_hours} hrs"
        )

        return CalculationResult(
            worker_id=worker.id,
            method_used=CalculationMethod.ROLLED_UP_PAY,
            pay_period_start=current_period.start_date,
            pay_period_end=current_period.end_date,
            entitlement_hours=entitlement_hours,
            holiday_pay_due=rolled_up_pay,
            audit_metadata={
                "accrual_rate_used": str(STATUTORY_ACCRUAL_RATE),
                "gross_pay": str(current_period.gross_pay),
                "itemised_uplift_amount": str(rolled_up_pay),
                "compliance_note": "Must be separately itemised on the worker's payslip.",
            },
        )
