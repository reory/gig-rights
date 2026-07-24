from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gig_rights.core.calculators.reference_period import ReferencePeriodCalculator
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
        id="WORKER-002",
        name="Sam Taylor",
        worker_type=WorkerType.IRREGULAR_HOURS,
        leave_year_start=date(2026, 1, 1),
    )


@pytest.fixture
def sample_period():
    """Provides a sample worker instance for testing."""

    return PayPeriod(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 7),
        hours_worked=Decimal("0.00"),
        gross_pay=Decimal("0.00"),
    )


class TestReferencePeriodCalculatorUnit:
    """Unit tests covering 52-week lookback rules, zero-pay exclusion, and edge cases."""

    def test_standard_52_week_reference_calculation(self, sample_worker, sample_period):
        """
        Verifies reference period calculation
        aggregates over the standard 52-week window.
        """

        calculator = ReferencePeriodCalculator()

        # 2 weeks history: 10 hrs @ £200 = £20/hr average
        historical = [
            PayPeriod(
                start_date=date(2026, 6, 1),
                end_date=date(2026, 6, 7),
                hours_worked=Decimal("10.00"),
                gross_pay=Decimal("200.00"),
            ),
            PayPeriod(
                start_date=date(2026, 6, 8),
                end_date=date(2026, 6, 14),
                hours_worked=Decimal("10.00"),
                gross_pay=Decimal("200.00"),
            ),
        ]

        # Request 8 hours of leave -> 8 * £20.00 = £160.00
        result = calculator.calculate(
            sample_worker,
            sample_period,
            historical_periods=historical,
            requested_leave_hours=Decimal("8.00"),
        )

        assert result.holiday_pay_due == Decimal("160.00")
        assert result.entitlement_hours == Decimal("8.00")
        assert result.method_used == CalculationMethod.REFERENCE_PERIOD_52_WEEKS
        assert result.audit_metadata["derived_hourly_rate"] == "20.0000"
        assert result.audit_metadata["weeks_evaluated_count"] == 2
        assert result.audit_metadata["zero_pay_weeks_excluded"] == 0

    def test_zero_pay_weeks_are_excluded(self, sample_worker, sample_period):
        """
        Verifies weeks with zero earnings are
        correctly excluded from the reference period average.
        """

        calculator = ReferencePeriodCalculator()

        # 3 weeks total: 1 zero-pay week included
        historical = [
            PayPeriod(
                start_date=date(2026, 6, 1),
                end_date=date(2026, 6, 7),
                hours_worked=Decimal("10.00"),
                gross_pay=Decimal("150.00"),
            ),
            PayPeriod(
                start_date=date(2026, 6, 8),
                end_date=date(2026, 6, 14),
                hours_worked=Decimal("0.00"),
                gross_pay=Decimal("0.00"),  # <--- Zero pay week
            ),
            PayPeriod(
                start_date=date(2026, 6, 15),
                end_date=date(2026, 6, 21),
                hours_worked=Decimal("10.00"),
                gross_pay=Decimal("150.00"),
            ),
        ]

        result = calculator.calculate(
            sample_worker,
            sample_period,
            historical_periods=historical,
            requested_leave_hours=Decimal("10.00"),
        )

        # Total earnings = £300 over 20 eligible hours -> £15.00/hr
        # 10 hrs leave * £15.00 = £150.00
        assert result.holiday_pay_due == Decimal("150.00")
        assert result.audit_metadata["weeks_evaluated_count"] == 2
        assert result.audit_metadata["zero_pay_weeks_excluded"] == 1

    def test_lookback_capped_at_52_eligible_weeks(self, sample_worker, sample_period):
        """
        Verifies reference period lookback window is
        strictly capped at 52 eligible weeks.
        """

        calculator = ReferencePeriodCalculator()

        # Create 60 eligible weeks
        historical = [
            PayPeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 7),
                hours_worked=Decimal("10.00"),
                gross_pay=Decimal("100.00"),
            )
            for _ in range(60)
        ]

        result = calculator.calculate(
            sample_worker,
            sample_period,
            historical_periods=historical,
            requested_leave_hours=Decimal("5.00"),
        )

        assert result.audit_metadata["weeks_evaluated_count"] == 52

    def test_raises_value_error_when_no_earning_history(
        self, sample_worker, sample_period
    ):
        """
        Verifies a ValueError is raised when calculating
        a reference period with no earnings history.
        """

        calculator = ReferencePeriodCalculator()

        with pytest.raises(ValueError, match="Insufficient earning history"):
            calculator.calculate(
                sample_worker,
                sample_period,
                historical_periods=[],
                requested_leave_hours=Decimal("10.00"),
            )

    def test_raises_value_error_when_all_weeks_are_zero_pay(
        self, sample_worker, sample_period
    ):
        """
        Verifies a ValueError is raised when all
        weeks in the reference period have zero earnings.
        """

        calculator = ReferencePeriodCalculator()

        historical = [
            PayPeriod(
                start_date=date(2026, 6, 1),
                end_date=date(2026, 6, 7),
                hours_worked=Decimal("0.00"),
                gross_pay=Decimal("0.00"),
            )
        ]

        with pytest.raises(ValueError, match="Insufficient earning history"):
            calculator.calculate(
                sample_worker,
                sample_period,
                historical_periods=historical,
                requested_leave_hours=Decimal("5.00"),
            )

    def test_division_by_zero_safety_zero_total_hours(
        self, sample_worker, sample_period
    ):
        """
        Verifies calculations handle zero total hours
        safely without raising division by zero errors.
        """

        calculator = ReferencePeriodCalculator()

        # Earning without recorded hours (e.g., retrospective bonus adjustment)
        historical = [
            PayPeriod(
                start_date=date(2026, 6, 1),
                end_date=date(2026, 6, 7),
                hours_worked=Decimal("0.00"),
                gross_pay=Decimal("100.00"),
            )
        ]

        result = calculator.calculate(
            sample_worker,
            sample_period,
            historical_periods=historical,
            requested_leave_hours=Decimal("5.00"),
        )

        assert result.holiday_pay_due == Decimal("0.00")
        assert result.audit_metadata["derived_hourly_rate"] == "0.0000"


class TestReferencePeriodCalculatorHypothesis:
    """Property-based tests for reference period invariants."""

    @given(
        leave_hours=st.decimals(
            min_value=Decimal("0.00"), max_value=Decimal("100.00"), places=2
        ),
        pay_per_week=st.decimals(
            min_value=Decimal("0.01"), max_value=Decimal("1000.00"), places=2
        ),
        hours_per_week=st.decimals(
            min_value=Decimal("0.01"), max_value=Decimal("80.00"), places=2
        ),
        num_weeks=st.integers(min_value=1, max_value=60),
    )
    def test_hypothesis_reference_period_invariants(
        self, leave_hours, pay_per_week, hours_per_week, num_weeks
    ):
        """
        Verifies reference period calculation invariants and
        bounds under property-based testing.
        """

        worker = Worker(
            id="WORKER-HYP",
            name="Hypothesis Worker",
            worker_type=WorkerType.IRREGULAR_HOURS,
            leave_year_start=date(2026, 1, 1),
        )
        current_period = PayPeriod(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 7),
            hours_worked=Decimal("0.00"),
            gross_pay=Decimal("0.00"),
        )

        historical = [
            PayPeriod(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 7),
                hours_worked=hours_per_week,
                gross_pay=pay_per_week,
            )
            for _ in range(num_weeks)
        ]

        calculator = ReferencePeriodCalculator()
        result = calculator.calculate(
            worker,
            current_period,
            historical_periods=historical,
            requested_leave_hours=leave_hours,
        )

        # Pay due is non-negative
        assert (result.holiday_pay_due >= Decimal("0.00")) is True

        # Precision is strictly 2 decimal places
        assert result.holiday_pay_due.as_tuple().exponent == -2

        # Evaluated weeks capped at min(num_weeks, 52)
        expected_weeks = min(num_weeks, 52)
        assert result.audit_metadata["weeks_evaluated_count"] == expected_weeks
