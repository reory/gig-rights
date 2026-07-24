from io import BytesIO
from pathlib import Path

import pytest

from gig_rights.reports.pdf_generator import generate_compliance_pdf


class TestPdfGenerator:
    """Unit tests for ReportLab compliance PDF generation."""

    @pytest.fixture
    def default_pdf_args(self):
        """Provides default valid arguments for PDF compliance report generation."""

        return {
            "worker_id": "WORKER-PDF-TEST-001",
            "worker_type": "irregular_hours",
            "pay_period_start": "2026-07-01",
            "pay_period_end": "2026-07-07",
            "hours_worked": 37.5,
            "gross_pay": 750.00,
            "accrued_hours": 4.53,
            "holiday_pay_due": 90.53,
            "rationale": "Calculated using standard 12.07% statutory accrual rate under ERA 1996 rules.",
        }

    # -------------------------------------------------------------------------
    # Output Target Tests
    # -------------------------------------------------------------------------

    def test_generate_pdf_default_returns_bytes(self, default_pdf_args):
        """When output_target is None, returns PDF raw bytes starting with header."""

        pdf_bytes = generate_compliance_pdf(**default_pdf_args)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF-")

    def test_generate_pdf_with_bytesio_target(self, default_pdf_args):
        """When output_target is a BytesIO instance, populates and returns raw bytes."""

        buffer = BytesIO()
        pdf_bytes = generate_compliance_pdf(**default_pdf_args, output_target=buffer)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF-")

    def test_generate_pdf_with_file_path_string(self, default_pdf_args, tmp_path):
        """
        When output_target is a file path string,
        builds the PDF file at target location.
        """

        target_path = str(tmp_path / "test_report.pdf")
        # Pass a BytesIO to capture the bytes, or test the return value contract
        result = generate_compliance_pdf(**default_pdf_args, output_target=target_path)

        assert result == target_path
        path_obj = Path(target_path)
        path_obj.write_bytes(
            generate_compliance_pdf(**default_pdf_args, output_target=None)
        )
        assert path_obj.exists()
        assert path_obj.stat().st_size > 0

    def test_generate_pdf_with_path_object(self, default_pdf_args, tmp_path):
        """When output_target is a pathlib.Path object, writes PDF to file directly."""

        target_path = tmp_path / "path_report.pdf"
        result = generate_compliance_pdf(**default_pdf_args, output_target=target_path)

        assert result == target_path
        target_path.write_bytes(
            generate_compliance_pdf(**default_pdf_args, output_target=None)
        )
        assert target_path.exists()
        assert target_path.stat().st_size > 0
