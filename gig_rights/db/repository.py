"""Append-only repository layer for statutory calculation persistence."""

from loguru import logger
from sqlalchemy.orm import Session

from gig_rights.core.models import CalculationResult, PayPeriod, Worker
from gig_rights.db.models import AuditLogModel, WorkerModel


class AuditRepository:
    """
    Data access layer enforcing append-only persistence semantics.
    Guarantees immutable calculation histories for compliance audits.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_worker(self, worker: Worker) -> WorkerModel:
        """Retrieves an existing worker or creates a new profile record."""

        existing = (
            self.db.query(WorkerModel).filter(WorkerModel.id == worker.id).first()
        )
        if existing:
            logger.debug(f"Retrieved existing worker profile | Worker ID: {worker.id}")
            return existing

        db_worker = WorkerModel(
            id=worker.id,
            name=worker.name,
            worker_type=worker.worker_type.value,
            leave_year_start=worker.leave_year_start,
        )
        self.db.add(db_worker)
        self.db.commit()
        self.db.refresh(db_worker)
        logger.info(f"Created new worker profile | Worker ID: {db_worker.id}")
        return db_worker

    def log_calculation(
        self, result: CalculationResult, current_period: PayPeriod
    ) -> AuditLogModel:
        """Appends an immutable calculation entry to the audit trail."""

        log_entry = AuditLogModel(
            worker_id=result.worker_id,
            method_used=result.method_used.value,
            pay_period_start=result.pay_period_start,
            pay_period_end=result.pay_period_end,
            hours_worked=current_period.hours_worked,
            gross_pay=current_period.gross_pay,
            entitlement_hours=result.entitlement_hours,
            holiday_pay_due=result.holiday_pay_due,
            audit_metadata=result.audit_metadata,
        )
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        logger.success(
            f"Appended immutable audit record | Log ID: {log_entry.id} | "
            f"Worker ID: {result.worker_id} | Method: {result.method_used.value}"
        )
        return log_entry

    def get_worker_audit_history(self, worker_id: str) -> list[AuditLogModel]:
        """Retrieves full chronological audit trail for a worker."""

        history = (
            self.db.query(AuditLogModel)
            .filter(AuditLogModel.worker_id == worker_id)
            .order_by(AuditLogModel.created_at.desc())
            .all()
        )
        logger.debug(
            f"Retrieved audit trail | Worker ID: {worker_id} "
            "| Records found: {len(history)}"
        )
        return history
