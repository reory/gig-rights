"""FastAPI router endpoints for classification, calculation, and audit history."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from loguru import logger
from sqlalchemy.orm import Session

from gig_rights.api.schemas import AuditLogResponse, CalculationRequest
from gig_rights.core.calculators.accrual import AccrualCalculator
from gig_rights.core.calculators.reference_period import ReferencePeriodCalculator
from gig_rights.core.calculators.rolled_up import RolledUpPayCalculator
from gig_rights.core.classification import (
    ClassificationInput,
    ClassificationResult,
    WorkerClassifier,
)
from gig_rights.core.models import CalculationMethod, CalculationResult, Worker
from gig_rights.db.repository import AuditRepository
from gig_rights.db.session import get_db
from gig_rights.reports.pdf_generator import generate_compliance_pdf

router = APIRouter(prefix="/api/v1", tags=["Statutory Holiday Rights"])


@router.post("/classify", response_model=ClassificationResult)
def classify_worker(input_data: ClassificationInput) -> ClassificationResult:
    """Evaluates shift patterns to determine statutory worker classification."""

    logger.info("API: Processing worker classification request")
    result = WorkerClassifier.classify(input_data)
    logger.info(
        f"API: Classification completed -> Worker Type: {result.worker_type.value}"
    )
    return result


@router.post("/calculate", response_model=CalculationResult)
def calculate_holiday_rights(
    payload: CalculationRequest,
    db: Annotated[Session, Depends(get_db)],
) -> CalculationResult:
    """Executes statutory calculation and records an immutable entry in the audit log."""

    logger.info(
        f"API: Received calculation request | Worker ID: {payload.worker_id} | Method: {payload.method.value}"
    )

    worker = Worker(
        id=payload.worker_id,
        name=payload.worker_name,
        worker_type=payload.worker_type,
        leave_year_start=payload.leave_year_start,
    )

    repo = AuditRepository(db)
    repo.get_or_create_worker(worker)

    try:
        # Select strategy pattern instance based on calculation method
        if payload.method == CalculationMethod.STATUTORY_ACCRUAL_1207:
            logger.debug(
                "API: Executing Statutory Accrual (12.07%) calculator strategy"
            )
            calculator = AccrualCalculator()
            result = calculator.calculate(worker, payload.current_period)

        elif payload.method == CalculationMethod.ROLLED_UP_PAY:
            logger.debug("API: Executing Rolled-Up Pay calculator strategy")
            calculator = RolledUpPayCalculator()
            result = calculator.calculate(worker, payload.current_period)

        elif payload.method == CalculationMethod.REFERENCE_PERIOD_52_WEEKS:
            logger.debug("API: Executing 52-Week Reference Period calculator strategy")
            calculator = ReferencePeriodCalculator()
            result = calculator.calculate(
                worker,
                payload.current_period,
                historical_periods=payload.historical_periods or [],
                requested_leave_hours=payload.requested_leave_hours or Decimal("0.0"),
            )

        else:
            logger.error(
                f"API: Unsupported calculation method requested: {payload.method}"
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported calculation method: {payload.method}",
            )

    except ValueError as err:
        # Catches statutory compliance violations (e.g. rolled-up pay for fixed workers)
        logger.warning(
            f"API: Compliance guard triggered | Worker ID: {payload.worker_id} | Error: {err}"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(err)
        )

    # Save to append-only audit log
    repo.log_calculation(result, payload.current_period)
    logger.success(
        f"API: Calculation logged successfully for worker {payload.worker_id}"
    )

    return result


@router.get("/audit/{worker_id}", response_model=list[AuditLogResponse])
def get_worker_audit_trail(
    worker_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[AuditLogResponse]:
    """Retrieves full chronological calculation audit history for a given worker."""

    logger.info(f"API: Fetching audit history | Worker ID: {worker_id}")

    repo = AuditRepository(db)
    records = repo.get_worker_audit_history(worker_id)
    if not records:
        logger.warning(
            f"API: Audit trail requested but no records found | Worker ID: {worker_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit records found for worker ID: {worker_id}",
        )
    logger.debug(
        f"API: Returned {len(records)} audit log entries for worker {worker_id}"
    )
    return records


@router.get(
    "/reports/{worker_id}/pdf",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Returns a PDF compliance report.",
        }
    },
)
def download_worker_pdf_report(
    worker_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> Response:
    """
    Generates and streams a downloadable PDF
    compliance statement for a given worker.
    """
    logger.info(f"API: PDF report download requested | Worker ID: {worker_id}")

    repo = AuditRepository(db)
    records = repo.get_worker_audit_history(worker_id)
    if not records:
        logger.warning(
            f"API: Cannot generate PDF, zero audit records found | Worker ID: {worker_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit records found for worker ID: {worker_id}. "
            "Please run a calculation first.",
        )

    # Grab the latest calculation record for the worker
    latest_record = records[0]

    # Safely retrieve worker classification
    worker_type = (
        latest_record.worker.worker_type if latest_record.worker else "irregular_hours"
    )

    # Safely retrieve statutory rationale from metadata (or generate fallback)
    rationale = ""
    if isinstance(latest_record.audit_metadata, dict):
        rationale = latest_record.audit_metadata.get("rationale", "")
    if not rationale:
        rationale = f"Statutory holiday entitlement calculated using method: {latest_record.method_used}."

    logger.debug(
        f"API: Generating PDF compliance binary payload for worker {worker_id}"
    )
    pdf_bytes = generate_compliance_pdf(
        worker_id=latest_record.worker_id,
        worker_type=str(worker_type),
        pay_period_start=str(latest_record.pay_period_start),
        pay_period_end=str(latest_record.pay_period_end),
        hours_worked=float(latest_record.hours_worked),
        gross_pay=float(latest_record.gross_pay),
        accrued_hours=float(
            latest_record.entitlement_hours
        ),  # Maps entitlement_hours -> accrued_hours
        holiday_pay_due=float(latest_record.holiday_pay_due),
        rationale=rationale,
    )

    logger.success(f"API: Streaming PDF report for worker {worker_id}")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="GigRights_Report_{worker_id}.pdf"'
        },
    )
