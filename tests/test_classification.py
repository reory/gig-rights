import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from gig_rights.core.classification import (
    ClassificationInput,
    ClassificationResult,
    WorkerClassifier,
    WorkerType,
)


class TestWorkerClassifierUnit:
    """Unit tests for the UK worker classification decision-support rules engine."""

    def test_fixed_rotation_pattern_takes_precedence_as_regular_fixed(self):
        """Edge Case 1: Fixed rotation patterns count as regular fixed hours (ACAS rule)."""

        input_data = ClassificationInput(
            hours_vary_by_contractor=True,
            fixed_rotation_pattern=True,
            unpaid_weeks_in_leave_year=False,
        )
        result = WorkerClassifier.classify(input_data)

        assert result.worker_type == WorkerType.REGULAR_FIXED
        assert result.eligible_for_1207_accrual is False
        assert result.rolled_up_pay_lawful is False
        assert "predictable rotating pattern" in result.rationale
        assert result.compliance_warning is not None
        assert "Misclassifying a fixed-rotation worker" in result.compliance_warning

    def test_part_year_worker_classification(self):
        """
        Part-year workers with full unpaid weeks qualify for
        12.07% accrual and rolled-up pay.
        """

        input_data = ClassificationInput(
            hours_vary_by_contractor=False,
            fixed_rotation_pattern=False,
            unpaid_weeks_in_leave_year=True,
        )
        result = WorkerClassifier.classify(input_data)

        assert result.worker_type == WorkerType.PART_YEAR
        assert result.eligible_for_1207_accrual is True
        assert result.rolled_up_pay_lawful is True
        assert "unpaid non-working period" in result.rationale
        assert result.compliance_warning is None

    def test_irregular_hours_worker_classification(self):
        """Genuinely varying hours without rotation qualify as irregular-hours workers."""

        input_data = ClassificationInput(
            hours_vary_by_contractor=True,
            fixed_rotation_pattern=False,
            unpaid_weeks_in_leave_year=False,
        )
        result = WorkerClassifier.classify(input_data)

        assert result.worker_type == WorkerType.IRREGULAR_HOURS
        assert result.eligible_for_1207_accrual is True
        assert result.rolled_up_pay_lawful is True
        assert "vary genuinely in each pay period" in result.rationale
        assert result.compliance_warning is None

    def test_default_regular_fixed_hours_classification(self):
        """Standard fixed-hours workers fall back to regular fixed classification."""

        input_data = ClassificationInput(
            hours_vary_by_contractor=False,
            fixed_rotation_pattern=False,
            unpaid_weeks_in_leave_year=False,
        )
        result = WorkerClassifier.classify(input_data)

        assert result.worker_type == WorkerType.REGULAR_FIXED
        assert result.eligible_for_1207_accrual is False
        assert result.rolled_up_pay_lawful is False
        assert "standard leave rules" in result.rationale
        assert result.compliance_warning is None

    def test_validation_error_on_missing_required_field(self):
        """Pydantic should raise a ValidationError if hours_vary_by_contractor is omitted."""

        with pytest.raises(ValidationError):
            ClassificationInput()


class TestWorkerClassifierHypothesis:
    """Property-based invariant tests across all combinations of classification inputs."""
    
    @settings(deadline=None)
    @given(
        hours_vary=st.booleans(),
        fixed_rotation=st.booleans(),
        unpaid_weeks=st.booleans(),
    )
    def test_hypothesis_classification_invariants(
        self, hours_vary: bool, fixed_rotation: bool, unpaid_weeks: bool
    ):
        input_data = ClassificationInput(
            hours_vary_by_contractor=hours_vary,
            fixed_rotation_pattern=fixed_rotation,
            unpaid_weeks_in_leave_year=unpaid_weeks,
        )
        result = WorkerClassifier.classify(input_data)

        # Result is a valid ClassificationResult instance
        assert isinstance(result, ClassificationResult)

        # 12.07% eligibility and rolled-up pay legality always move together
        assert result.eligible_for_1207_accrual == result.rolled_up_pay_lawful

        # REGULAR_FIXED workers can never receive 12.07% accrual or rolled-up pay
        if result.worker_type == WorkerType.REGULAR_FIXED:
            assert result.eligible_for_1207_accrual is False
            assert result.rolled_up_pay_lawful is False

        # IRREGULAR_HOURS and PART_YEAR workers must be eligible for 12.07% accrual
        if result.worker_type in (WorkerType.IRREGULAR_HOURS, WorkerType.PART_YEAR):
            assert result.eligible_for_1207_accrual is True
            assert result.rolled_up_pay_lawful is True

        # Compliance warning is populated ONLY for fixed rotation
        # misclassification attempts
        if hours_vary and fixed_rotation:
            assert result.compliance_warning is not None
        else:
            assert result.compliance_warning is None
