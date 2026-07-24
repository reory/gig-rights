from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gig_rights.core.calculators.rolled_up import RolledUpPayCalculator
from gig_rights.core.classification import WorkerType
from gig_rights.core.models import (
    CalculationMethod,
    PayPeriod,
    Worker,
)


@pytest.fixture
def irregular_worker():
    """
    Provides a sample worker instance with irregular hours
    configuration for testing.
    """

    return Worker(
        id="WORKER-IRR-001",
        name="Alex Morgan",
        worker_type=WorkerType.IRREGULAR_HOURS,
        leave_year_start=date(2026, 1, 1),
    )


@pytest.fixture
def fixed_worker():
    """Provides a sample worker instance with regular hours configuration for testing."""

    return Worker(
        id="WORKER-FIX-002",
        name="Jordan Lee",
        worker_type=WorkerType.REGULAR_FIXED,
        leave_year_start=date(2026, 1, 1),
    )


@pytest.fixture
def sample_period():
    """Provides a standard sample pay period instance for testing."""

    return PayPeriod(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 7),
        hours_worked=Decimal("37.50"),
        gross_pay=Decimal("750.00"),
    )


class TestRolledUpPayCalculatorUnit:
    """Unit tests for the 12.07% rolled-up holiday pay uplift calculator."""

    def test_standard_rolled_up_calculation(self, irregular_worker, sample_period):
        """
        Verifies standard rolled-up holiday pay
        calculation for irregular hours workers.
        """

        calculator = RolledUpPayCalculator()
        result = calculator.calculate(irregular_worker, sample_period)

        # 37.50 hrs * 0.1207 = 4.52625 -> rounds to 4.53 hrs
        # £750.00 * 0.1207 = £90.525 -> rounds to £90.53
        assert result.worker_id == "WORKER-IRR-001"
        assert result.method_used == CalculationMethod.ROLLED_UP_PAY
        assert result.entitlement_hours == Decimal("4.53")
        assert result.holiday_pay_due == Decimal("90.53")
        assert result.audit_metadata["accrual_rate_used"] == "0.1207"
        assert result.audit_metadata["gross_pay"] == "750.00"
        assert result.audit_metadata["itemised_uplift_amount"] == "90.53"

    def test_raises_value_error_for_regular_fixed_worker(
        self, fixed_worker, sample_period
    ):
        """
        Verifies a ValueError is raised when attempting
        rolled-up calculations for a regular fixed hours worker.
        """

        calculator = RolledUpPayCalculator()
        with pytest.raises(
            ValueError,
            match="Rolled-up holiday pay is unlawful for fixed-hours workers.",
        ):
            calculator.calculate(fixed_worker, sample_period)

    def test_zero_pay_and_hours_returns_zero(self, irregular_worker):
        """
        Verifies statutory accrual returns zero entitlement
        when pay and hours are zero.
        """

        calculator = RolledUpPayCalculator()
        zero_period = PayPeriod(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 7),
            hours_worked=Decimal("0.00"),
            gross_pay=Decimal("0.00"),
        )
        result = calculator.calculate(irregular_worker, zero_period)

        assert result.entitlement_hours == Decimal("0.00")
        assert result.holiday_pay_due == Decimal("0.00")

    def test_rounding_half_up_precision(self, irregular_worker):
        """
        Verifies monetary and hour values correctly
        apply half-up rounding precision.
        """

        calculator = RolledUpPayCalculator()
        # 10.00 gross * 0.1207 = 1.207 -> rounds up to 1.21
        period = PayPeriod(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 7),
            hours_worked=Decimal("10.00"),
            gross_pay=Decimal("10.00"),
        )
        result = calculator.calculate(irregular_worker, period)

        assert result.holiday_pay_due == Decimal("1.21")
        assert result.entitlement_hours == Decimal("1.21")


class TestRolledUpPayCalculatorHypothesis:
    """Property-based tests for rolled-up pay invariants."""

    @given(
        hours=st.decimals(
            min_value=Decimal("0.00"), max_value=Decimal("200.00"), places=2
        ),
        gross=st.decimals(
            min_value=Decimal("0.00"), max_value=Decimal("10000.00"), places=2
        ),
    )
    def test_hypothesis_rolled_up_invariants(self, hours, gross):
        """
        Verifies rolled-up holiday pay
        calculation invariants and bounds under property-based testing.
        """

        worker = Worker(
            id="WORKER-HYP",
            name="Hypothesis Worker",
            worker_type=WorkerType.IRREGULAR_HOURS,
            leave_year_start=date(2026, 1, 1),
        )
        period = PayPeriod(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 7),
            hours_worked=hours,
            gross_pay=gross,
        )
        calculator = RolledUpPayCalculator()
        result = calculator.calculate(worker, period)

        # Pay due and entitlement hours must be non-negative
        assert result.holiday_pay_due >= Decimal("0.00")
        assert result.entitlement_hours >= Decimal("0.00")

        # Precision is strictly 2 decimal places
        assert result.holiday_pay_due.as_tuple().exponent == -2
        assert result.entitlement_hours.as_tuple().exponent == -2

        # Pay due stays within 1 penny of raw calculated value
        expected_raw = gross * Decimal("0.1207")
        assert abs(result.holiday_pay_due - expected_raw) <= Decimal("0.01")
