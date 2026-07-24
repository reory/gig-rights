"""Decision-support rules engine for UK worker classification under statutory rules.
Distinguishes between:
- Regular/Fixed hours workers
- Irregular-hours workers (eligible for 12.07% statutory accrual & rolled-up pay)
- Part-year workers (eligible for 12.07% statutory accrual & rolled-up pay)
"""

from enum import Enum

from loguru import logger
from pydantic import BaseModel, Field


class WorkerType(str, Enum):
    """Statutory categories under UK holiday regulations.
    Inheriting from (str, Enum) string comparison/JSON serialization
    out of the box while enforcing strict type-safety across the app.
    """

    REGULAR_FIXED = "regular_fixed"
    IRREGULAR_HOURS = "irregular_hours"
    PART_YEAR = "part_year"


class ClassificationInput(BaseModel):
    """Answers to decision-support questions regarding worker shift structure."""

    hours_vary_by_contractor: bool = Field(
        ...,
        description="Do the workers paid hours vary significantly under "
        "their contract?",
    )
    fixed_rotation_pattern: bool = Field(
        default=False,
        description="Are variations set by a predictable contractual pattern "
        "(e.g, 15h week 1, 20h week 2)?",
    )
    unpaid_weeks_in_leave_year: bool = Field(
        default=False,
        description="Are there periods of at least one full week in the leave year "
        "where no work/pay is expected?",
    )


class ClassificationResult(BaseModel):
    """Output classification decision, statutory eligibility, and legal rationale."""

    worker_type: WorkerType
    eligible_for_1207_accrual: bool
    rolled_up_pay_lawful: bool
    rationale: str
    compliance_warning: str | None = None 


class WorkerClassifier:
    """Rules engine for worker type classification."""

    @staticmethod
    def classify(input_data: ClassificationInput) -> ClassificationResult:
        logger.info(
            f"Evaluating worker classification | hours_vary: {input_data.hours_vary_by_contractor}, "
            f"fixed_rotation: {input_data.fixed_rotation_pattern}, "
            f"unpaid_weeks: {input_data.unpaid_weeks_in_leave_year}"
        )

        # Edge Case 1: Fixed rotating shift patterns (ACAS rule)
        # Even if hours vary week-to-week, if the pattern is fixed by contract,
        # they are NOT an irregular-hours worker under statutory rules.
        if input_data.hours_vary_by_contractor and input_data.fixed_rotation_pattern:
            logger.warning(
                "Classification result: REGULAR_FIXED | Reason: Fixed rotation pattern "
                "overrides varying hours."
                "Rolled_up pay would be unlawful."
            )
            return ClassificationResult(
                worker_type=WorkerType.REGULAR_FIXED,
                eligible_for_1207_accrual=False,
                rolled_up_pay_lawful=False,
                rationale=(
                    "Worker's hours vary, but follow a predictable rotating "
                    "pattern set out in their contract. Under ACAS/statutory "
                    "guidelines, this counts as fixed hours."
                ),
                compliance_warning=(
                    "Misclassifying a fixed-rotation worker as an "
                    "irregular-hours worker to apply "
                    "rolled-up pay is unlawful under statutory guidelines."
                ),
            )

        # Part year worker check
        if input_data.unpaid_weeks_in_leave_year:
            logger.info(
                "Classification result: PART_YEAR | Eligible for 12.07% "
                "and rolled-up pay."
            )
            return ClassificationResult(
                worker_type=WorkerType.PART_YEAR,
                eligible_for_1207_accrual=True,
                rolled_up_pay_lawful=True,
                rationale=(
                    "Worker is contracted for part of the year with at least "
                    "one week of unpaid non-working period during the leave year."
                ),
            )

        # Irregular-hours worker check
        if input_data.hours_vary_by_contractor:
            logger.info(
                "Classification result: IRREGULAR HOURS | Eligible for "
                "12.07% accrual and rolled-up pay."
            )
            return ClassificationResult(
                worker_type=WorkerType.IRREGULAR_HOURS,
                eligible_for_1207_accrual=True,
                rolled_up_pay_lawful=True,
                rationale=(
                    "Worker's paid hours vary genuinely in each pay period "
                    "under the terms of their contract."
                ),
            )

        # Standard fixed hours default
        logger.info(
            "Classification result: REGULAR_FIXED | Standard fixed-hours worker."
        )
        return ClassificationResult(
            worker_type=WorkerType.REGULAR_FIXED,
            eligible_for_1207_accrual=False,
            rolled_up_pay_lawful=False,
            rationale=(
                "Worker has fixed hours. Statutory holiday entitlement must "
                "be calculated using standard leave rules rather than the 12.07% "
                "accrual method."
            ),
        )
