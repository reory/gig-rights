from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from gig_rights.core.classification import WorkerType
from gig_rights.core.models import (
    CalculationMethod,
    CalculationResult,
    PayPeriod,
    Worker,
)


class TestModelsUnit:
    """Unit tests for Pydantic v2 domain models in core/models.py."""

    def test_calculation_method_enum_values_and_str_inheritance(self):
        """
        CalculationMethod enum members behave as string
        instances for JSON/SQL serialization.
        """

        assert CalculationMethod.STATUTORY_ACCRUAL_1207 == "12.07_percent_accrual"
        assert CalculationMethod.ROLLED_UP_PAY == "rolled_up_pay"
        assert CalculationMethod.REFERENCE_PERIOD_52_WEEKS == "52_week_reference_period"
        assert isinstance(CalculationMethod.ROLLED_UP_PAY, str)

    def test_pay_period_valid_instantiation(self):
        """PayPeriod accepts valid non-negative decimal hours and gross pay."""

        period = PayPeriod(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 7),
            hours_worked=Decimal("37.50"),
            gross_pay=Decimal("750.00"),
        )
        assert period.hours_worked == Decimal("37.50")
        assert period.gross_pay == Decimal("750.00")

    def test_pay_period_negative_hours_raises_validation_error(self):
        """PayPeriod enforces hours_worked >= 0.0 via Field validation."""

        with pytest.raises(ValidationError) as exc_info:
            PayPeriod(
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 7),
                hours_worked=Decimal("-0.01"),
                gross_pay=Decimal("100.00"),
            )
        assert "hours_worked" in str(exc_info.value)

    def test_pay_period_negative_gross_pay_raises_validation_error(self):
        """PayPeriod enforces gross_pay >= 0.0 via Field validation."""

        with pytest.raises(ValidationError) as exc_info:
            PayPeriod(
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 7),
                hours_worked=Decimal("10.00"),
                gross_pay=Decimal("-50.00"),
            )
        assert "gross_pay" in str(exc_info.value)

    def test_worker_valid_instantiation_and_dump(self):
        """Worker model instantiates correctly and serializes worker_type cleanly."""

        worker = Worker(
            id="WORKER-001",
            name="Alex Morgan",
            worker_type=WorkerType.IRREGULAR_HOURS,
            leave_year_start=date(2026, 1, 1),
        )
        assert worker.id == "WORKER-001"
        assert worker.worker_type == WorkerType.IRREGULAR_HOURS

        data = worker.model_dump()
        assert data["worker_type"] == "irregular_hours"

    def test_calculation_result_serialization(self):
        """
        CalculationResult serializes to dictionary
        cleanly with audit metadata intact.
        """

        result = CalculationResult(
            worker_id="WORKER-001",
            method_used=CalculationMethod.ROLLED_UP_PAY,
            pay_period_start=date(2026, 7, 1),
            pay_period_end=date(2026, 7, 7),
            entitlement_hours=Decimal("4.53"),
            holiday_pay_due=Decimal("90.53"),
            audit_metadata={"accrual_rate": "0.1207"},
        )
        data = result.model_dump()
        assert data["worker_id"] == "WORKER-001"
        assert data["method_used"] == "rolled_up_pay"
        assert data["entitlement_hours"] == Decimal("4.53")
        assert data["audit_metadata"]["accrual_rate"] == "0.1207"


class TestModelsHypothesis:
    """Property-based invariant tests for domain models."""
    
    @settings(deadline=None)
    @given(
        hours=st.decimals(
            min_value=Decimal("0.00"), max_value=Decimal("1000.00"), places=2
        ),
        gross=st.decimals(
            min_value=Decimal("0.00"), max_value=Decimal("100000.00"), places=2
        ),
    )
    def test_hypothesis_pay_period_serialization_round_trip(
        self, hours: Decimal, gross: Decimal
    ):
        """Any valid non-negative pay period must survive a dump and parse round-trip."""

        period = PayPeriod(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 7),
            hours_worked=hours,
            gross_pay=gross,
        )
        assert period.hours_worked >= Decimal("0.00")
        assert period.gross_pay >= Decimal("0.00")

        dumped = period.model_dump()
        reparsed = PayPeriod(**dumped)
        assert reparsed == period
