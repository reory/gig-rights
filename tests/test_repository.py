from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gig_rights.core.models import (
    CalculationMethod,
    CalculationResult,
    PayPeriod,
    Worker,
    WorkerType,
)
from gig_rights.db.models import Base, WorkerModel
from gig_rights.db.repository import AuditRepository


@pytest.fixture
def db_session():
    """
    Provides a fresh in-memory SQLite database session
    for each test and disposes of the engine.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class TestAuditRepository:
    """Unit tests for AuditRepository persistence and query operations."""

    @pytest.fixture
    def sample_worker(self):
        """Provides a sample worker instance for testing."""

        return Worker(
            id="WORKER-AUDIT-001",
            name="Alex Morgan",
            worker_type=WorkerType.IRREGULAR_HOURS,
            leave_year_start=date(2026, 4, 1),
        )

    @pytest.fixture
    def sample_pay_period(self):
        """Provides a sample pay period instance for testing."""

        return PayPeriod(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 7),
            hours_worked=Decimal("37.50"),
            gross_pay=Decimal("750.00"),
        )

    @pytest.fixture
    def sample_calc_result(self, sample_worker, sample_pay_period):
        """Provides a sample calculation result instance for testing."""

        return CalculationResult(
            worker_id=sample_worker.id,
            method_used=CalculationMethod.STATUTORY_ACCRUAL_1207,
            pay_period_start=sample_pay_period.start_date,
            pay_period_end=sample_pay_period.end_date,
            entitlement_hours=Decimal("4.53"),
            holiday_pay_due=Decimal("90.53"),
            audit_metadata={"rule": "12.07% Statutory Accrual"},
        )

    # Worker Persistence Tests
    def test_get_or_create_worker_creates_new_record(self, db_session, sample_worker):
        """Creates a new worker record in DB when ID doesn't exist."""

        repo = AuditRepository(db_session)
        db_worker = repo.get_or_create_worker(sample_worker)

        assert db_worker.id == sample_worker.id
        assert db_worker.name == sample_worker.name
        assert db_worker.worker_type == sample_worker.worker_type.value
        assert db_worker.leave_year_start == sample_worker.leave_year_start

        db_record = db_session.query(WorkerModel).filter_by(id=sample_worker.id).first()
        assert db_record is not None

    def test_get_or_create_worker_idempotent_for_existing_record(
        self, db_session, sample_worker
    ):
        """Retrieves existing worker record without creating duplicate entries."""

        repo = AuditRepository(db_session)

        first_call = repo.get_or_create_worker(sample_worker)
        second_call = repo.get_or_create_worker(sample_worker)

        assert first_call.id == second_call.id
        count = db_session.query(WorkerModel).filter_by(id=sample_worker.id).count()
        assert count == 1

    # Calculation Audit Logging Tests
    def test_log_calculation_appends_immutable_entry(
        self, db_session, sample_worker, sample_pay_period, sample_calc_result
    ):
        """Appends a calculation log entry to the audit trail with accurate fields."""

        repo = AuditRepository(db_session)
        repo.get_or_create_worker(sample_worker)

        log_entry = repo.log_calculation(sample_calc_result, sample_pay_period)

        assert log_entry.id is not None
        assert log_entry.worker_id == sample_worker.id
        assert log_entry.method_used == CalculationMethod.STATUTORY_ACCRUAL_1207.value
        assert Decimal(str(log_entry.hours_worked)) == Decimal("37.50")
        assert Decimal(str(log_entry.gross_pay)) == Decimal("750.00")
        assert Decimal(str(log_entry.entitlement_hours)) == Decimal("4.53")
        assert Decimal(str(log_entry.holiday_pay_due)) == Decimal("90.53")
        assert log_entry.audit_metadata == {"rule": "12.07% Statutory Accrual"}

    def test_get_worker_audit_history_returns_ordered_records(
        self, db_session, sample_worker, sample_pay_period, sample_calc_result
    ):
        """
        Returns full audit history for a
        worker ordered newest-first (created_at desc).
        """

        repo = AuditRepository(db_session)
        repo.get_or_create_worker(sample_worker)

        entry1 = repo.log_calculation(sample_calc_result, sample_pay_period)
        entry2 = repo.log_calculation(sample_calc_result, sample_pay_period)

        history = repo.get_worker_audit_history(sample_worker.id)

        assert len(history) == 2
        assert history[0].id == entry2.id
        assert history[1].id == entry1.id

    def test_get_worker_audit_history_isolates_records_by_worker(
        self, db_session, sample_worker, sample_pay_period, sample_calc_result
    ):
        """Audit history queries only return records for the requested worker_id."""

        repo = AuditRepository(db_session)
        repo.get_or_create_worker(sample_worker)
        repo.log_calculation(sample_calc_result, sample_pay_period)

        other_worker = Worker(
            id="WORKER-AUDIT-002",
            name="Jordan Lee",
            worker_type=WorkerType.REGULAR_FIXED,
            leave_year_start=date(2026, 1, 1),
        )
        repo.get_or_create_worker(other_worker)

        history_other = repo.get_worker_audit_history("WORKER-AUDIT-002")
        assert len(history_other) == 0

        history_main = repo.get_worker_audit_history(sample_worker.id)
        assert len(history_main) == 1
