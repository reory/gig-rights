from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gig_rights.core.calculators.accrual import (
    STATUTORY_ACCRUAL_RATE,
    AccrualCalculator,
)
from gig_rights.core.models import (
    CalculationMethod,
    PayPeriod,
    Worker,
    WorkerType,
)


@pytest.fixture
def sample_worker():
    """Provides a sample worker instance for testing."""

    return Worker(
        id="WORKER-001",
        name="Alex Smith",
        worker_type=WorkerType.IRREGULAR_HOURS,
        leave_year_start=date(2026, 1, 1),
    )


@pytest.fixture
def sample_period():
    """Provides a sample worker instance for testing."""

    return PayPeriod(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 7),
        hours_worked=Decimal("37.50"),
        gross_pay=Decimal("562.50"),
    )


class TestAccrualCalculatorUnit:
    """Unit tests for deterministic edge cases and explicit expectations."""

    def test_accrual_calculation_standard_hours(self, sample_worker, sample_period):
        """Verifies statutory accrual calculation yields expected entitlement hours."""

        calculator = AccrualCalculator()
        result = calculator.calculate(sample_worker, sample_period)

        # 37.50 * 0.1207 = 4.52625 -> rounds up to 4.53
        assert result.entitlement_hours == Decimal("4.53")
        assert result.holiday_pay_due == Decimal("0.00")
        assert result.method_used == CalculationMethod.STATUTORY_ACCRUAL_1207
        assert result.worker_id == "WORKER-001"

    def test_accrual_calculation_zero_hours(self, sample_worker):
        """Verifies zero accrual is returned when zero hours are worked."""

        calculator = AccrualCalculator()
        period = PayPeriod(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 7),
            hours_worked=Decimal("0.00"),
            gross_pay=Decimal("0.00"),
        )
        result = calculator.calculate(sample_worker, period)

        assert result.entitlement_hours == Decimal("0.00")
        assert result.holiday_pay_due == Decimal("0.00")

    def test_accrual_rounding_half_up_boundary(self, sample_worker):
        """Verifies accrual correctly rounds half-up boundary values."""

        calculator = AccrualCalculator()
        # 10.00 * 0.1207 = 1.2070 -> rounds to 1.21
        period = PayPeriod(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 7),
            hours_worked=Decimal("10.00"),
            gross_pay=Decimal("150.00"),
        )
        result = calculator.calculate(sample_worker, period)

        assert result.entitlement_hours == Decimal("1.21")

    def test_audit_metadata_structure(self, sample_worker, sample_period):
        """
        Verifies calculation result includes expected audit
        metadata structure and rules.
        """

        calculator = AccrualCalculator()
        result = calculator.calculate(sample_worker, sample_period)

        metadata = result.audit_metadata
        assert metadata["accrual_rate_used"] == "0.1207"
        assert metadata["hours_worked"] == "37.50"
        assert "formula" in metadata


class TestAccrualCalculatorHypothesis:
    """Property-based tests using Hypothesis to verify invariant rules across all inputs."""
    
    @settings(deadline=None)
    @given(
        hours=st.decimals(
            min_value=Decimal("0.00"),
            max_value=Decimal("10000.00"),
            places=2,
        )
    )
    def test_hypothesis_accrual_invariants(self, hours):
        """Verifies statutory accrual proportionality and non-negative invariants."""

        worker = Worker(
            id="WORKER-001",
            name="Alex Smith",
            worker_type=WorkerType.IRREGULAR_HOURS,
            leave_year_start=date(2026, 1, 1),
        )
        calculator = AccrualCalculator()
        period = PayPeriod(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 7),
            hours_worked=hours,
            gross_pay=hours * Decimal("15.00"),
        )

        result = calculator.calculate(worker, period)

        # Entitlement hours must never be negative
        assert (result.entitlement_hours >= Decimal("0.00")) is True

        # Holiday pay due is strictly 0.00 for accrual method
        assert (result.holiday_pay_due == Decimal("0.00")) is True

        # Precision is strictly two decimal places
        assert result.entitlement_hours.as_tuple().exponent == -2

        # Entitlement matches formula within rounding tolerance
        expected_raw = hours * STATUTORY_ACCRUAL_RATE
        diff = abs(result.entitlement_hours - expected_raw)
        assert (diff <= Decimal("0.01")) is True
