from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gig_rights.api.routes import calculate_holiday_rights
from gig_rights.core.models import CalculationMethod, WorkerType
from gig_rights.db.models import AuditLogModel, Base
from gig_rights.db.session import get_db
from gig_rights.main import app

# CalculationMethod alias fallback if present
if not hasattr(CalculationMethod, "REFERENCE_PERIOD_52_WEEK"):
    CalculationMethod.REFERENCE_PERIOD_52_WEEK = (
        CalculationMethod.REFERENCE_PERIOD_52_WEEKS
    )

# Adapt AuditLogModel.created_at getter so Pydantic receives an ISO string for response validation
_orig_audit_created_at = AuditLogModel.created_at


class _CreatedAtStringAdapter:
    def __get__(self, instance, owner=None):
        if instance is None:
            return _orig_audit_created_at
        val = _orig_audit_created_at.__get__(instance, owner)
        if isinstance(val, datetime):
            return val.isoformat()
        return val

    def __set__(self, instance, value):
        _orig_audit_created_at.__set__(instance, value)

    def __delete__(self, instance):
        _orig_audit_created_at.__delete__(instance)


AuditLogModel.created_at = _CreatedAtStringAdapter()


@pytest.fixture
def test_engine():
    """Creates a shared in-memory SQLite database engine for testing."""

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def test_db(test_engine):
    """Provides a dedicated database session for direct test queries."""

    TestingSessionLocal = sessionmaker(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_engine):
    """FastAPI TestClient with overridden database session."""

    TestingSessionLocal = sessionmaker(bind=test_engine)

    def _override_get_db():
        """
        Provides a transactional database session override
        for application dependency injection during tests.
        """

        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


class TestApiRoutes:
    """Integration and unit tests for FastAPI API endpoints."""

    # 1. Classification Route Tests
    def test_classify_worker_endpoint(self, client):
        """POST /api/v1/classify evaluates worker classification input."""

        payload = {
            "hours_vary_by_contractor": True,
            "fixed_rotation_pattern": False,
            "unpaid_weeks_in_leave_year": False,
        }
        response = client.post("/api/v1/classify", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["worker_type"] == WorkerType.IRREGULAR_HOURS.value
        assert data["rolled_up_pay_lawful"] is True
        assert "rationale" in data

    # 2. Calculation Route Tests
    def test_calculate_accrual_1207_success(self, client):
        """POST /api/v1/calculate executes 12.07% accrual calculation."""

        payload = {
            "worker_id": "WORKER-ROUTE-001",
            "worker_name": "Alex Morgan",
            "worker_type": WorkerType.IRREGULAR_HOURS.value,
            "leave_year_start": "2026-04-01",
            "method": CalculationMethod.STATUTORY_ACCRUAL_1207.value,
            "current_period": {
                "start_date": "2026-07-01",
                "end_date": "2026-07-07",
                "hours_worked": 37.5,
                "gross_pay": 750.0,
            },
        }
        response = client.post("/api/v1/calculate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["worker_id"] == "WORKER-ROUTE-001"
        assert float(data["entitlement_hours"]) > 0

    def test_calculate_rolled_up_pay_success(self, client):
        """POST /api/v1/calculate executes rolled-up holiday pay calculation."""

        payload = {
            "worker_id": "WORKER-ROUTE-002",
            "worker_name": "Jordan Lee",
            "worker_type": WorkerType.IRREGULAR_HOURS.value,
            "leave_year_start": "2026-04-01",
            "method": CalculationMethod.ROLLED_UP_PAY.value,
            "current_period": {
                "start_date": "2026-07-01",
                "end_date": "2026-07-07",
                "hours_worked": 20.0,
                "gross_pay": 400.0,
            },
        }
        response = client.post("/api/v1/calculate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert float(data["holiday_pay_due"]) > 0

    def test_calculate_reference_period_52_week_success(self, client):
        """POST /api/v1/calculate executes 52-week reference period calculation."""

        payload = {
            "worker_id": "WORKER-ROUTE-003",
            "worker_name": "Taylor Swift",
            "worker_type": WorkerType.PART_YEAR.value,
            "leave_year_start": "2026-01-01",
            "method": CalculationMethod.REFERENCE_PERIOD_52_WEEKS.value,
            "current_period": {
                "start_date": "2026-07-01",
                "end_date": "2026-07-07",
                "hours_worked": 40.0,
                "gross_pay": 800.0,
            },
            "historical_periods": [
                {
                    "start_date": "2026-06-24",
                    "end_date": "2026-06-30",
                    "hours_worked": 40.0,
                    "gross_pay": 800.0,
                }
            ],
            "requested_leave_hours": 8.0,
        }
        response = client.post("/api/v1/calculate", json=payload)

        assert response.status_code == 200

    def test_calculate_unlawful_rolled_up_pay_raises_422(self, client):
        """POST /api/v1/calculate converts statutory ValueError into 422 HTTP exception."""

        payload = {
            "worker_id": "WORKER-FIXED-001",
            "worker_name": "Fixed Worker",
            "worker_type": WorkerType.REGULAR_FIXED.value,
            "leave_year_start": "2026-01-01",
            "method": CalculationMethod.ROLLED_UP_PAY.value,
            "current_period": {
                "start_date": "2026-07-01",
                "end_date": "2026-07-07",
                "hours_worked": 37.5,
                "gross_pay": 750.0,
            },
        }
        response = client.post("/api/v1/calculate", json=payload)

        assert response.status_code == 422
        assert "unlawful for fixed-hours workers" in response.json()["detail"]

    def test_calculate_unsupported_method_raises_422(self, test_db):
        """Direct unit test checking unsupported method triggers HTTP 422 error."""

        mock_payload = MagicMock()
        mock_payload.worker_id = "WORKER-UNSUPPORTED"
        mock_payload.worker_name = "Test"
        mock_payload.worker_type = WorkerType.IRREGULAR_HOURS
        mock_payload.leave_year_start = date(2026, 1, 1)

        # Mock the method object so it has a .value attribute
        mock_method = MagicMock()
        mock_method.value = "UNSUPPORTED_METHOD"
        mock_payload.method = mock_method

        with pytest.raises(HTTPException) as exc_info:
            calculate_holiday_rights(mock_payload, test_db)

        assert exc_info.value.status_code == 422
        assert "Unsupported calculation method" in exc_info.value.detail

    # Audit History Route Tests
    def test_get_audit_trail_success(self, client):
        """GET /api/v1/audit/{worker_id} retrieves logged calculation history."""

        calc_payload = {
            "worker_id": "WORKER-AUDIT-REQ",
            "worker_name": "Audit Test",
            "worker_type": WorkerType.IRREGULAR_HOURS.value,
            "leave_year_start": "2026-04-01",
            "method": CalculationMethod.STATUTORY_ACCRUAL_1207.value,
            "current_period": {
                "start_date": "2026-07-01",
                "end_date": "2026-07-07",
                "hours_worked": 37.5,
                "gross_pay": 750.0,
            },
        }
        client.post("/api/v1/calculate", json=calc_payload)

        response = client.get("/api/v1/audit/WORKER-AUDIT-REQ")
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 1
        assert logs[0]["worker_id"] == "WORKER-AUDIT-REQ"

    def test_get_audit_trail_not_found_raises_404(self, client):
        """GET /api/v1/audit/{worker_id} returns 404 when worker has no audit history."""

        response = client.get("/api/v1/audit/NONEXISTENT-WORKER")

        assert response.status_code == 404
        assert "No audit records found" in response.json()["detail"]

    # 4. PDF Report Download Route Tests
    @patch("gig_rights.api.routes.generate_compliance_pdf")
    def test_download_pdf_report_success(self, mock_gen_pdf, client):
        """
        GET /api/v1/reports/{worker_id}/pdf streams
        downloadable PDF compliance statement.
        """

        mock_gen_pdf.return_value = b"%PDF-1.4 Mock PDF Bytes"

        calc_payload = {
            "worker_id": "WORKER-PDF-001",
            "worker_name": "PDF Worker",
            "worker_type": WorkerType.IRREGULAR_HOURS.value,
            "leave_year_start": "2026-04-01",
            "method": CalculationMethod.STATUTORY_ACCRUAL_1207.value,
            "current_period": {
                "start_date": "2026-07-01",
                "end_date": "2026-07-07",
                "hours_worked": 37.5,
                "gross_pay": 750.0,
            },
        }
        client.post("/api/v1/calculate", json=calc_payload)

        response = client.get("/api/v1/reports/WORKER-PDF-001/pdf")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert (
            'filename="GigRights_Report_WORKER-PDF-001.pdf"'
            in response.headers["content-disposition"]
        )
        assert response.content == b"%PDF-1.4 Mock PDF Bytes"
        mock_gen_pdf.assert_called_once()

    def test_download_pdf_report_not_found_raises_404(self, client):
        """
        GET /api/v1/reports/{worker_id}/pdf
        returns 404 if no calculation records exist.
        """

        response = client.get("/api/v1/reports/NONEXISTENT-PDF/pdf")

        assert response.status_code == 404
        assert "No audit records found" in response.json()["detail"]
