import csv
from unittest.mock import MagicMock, patch

import pytest  # noqa
from typer.testing import CliRunner

from gig_rights.cli.main import app

runner = CliRunner()


class TestCliCommands:
    """Unit and integration tests for the Typer CLI interface."""

    # 1. Classify Command Tests
    def test_classify_command_default(self):
        """Classify command runs with required --hours parameter."""

        result = runner.invoke(app, ["classify", "--hours", "0.0"])

        assert result.exit_code == 0
        assert "Worker Classification Result" in result.stdout
        assert "Classification" in result.stdout

    def test_classify_command_with_flags(self):
        """Classify command accepts --fixed-pattern and --unpaid-weeks flags."""

        result = runner.invoke(
            app,
            [
                "classify",
                "-h",
                "37.5",
                "--fixed-pattern",
                "--unpaid-weeks",
            ],
        )

        assert result.exit_code == 0
        assert "Worker Classification Result" in result.stdout

    def test_classify_command_missing_required_hours_fails(self):
        """Classify command fails when mandatory --hours flag is missing."""

        result = runner.invoke(app, ["classify"])

        assert result.exit_code != 0
        # Check result.output (combines stdout and stderr where Typer logs CLI errors)
        assert "Missing option" in result.output or "Error" in result.output

    # Calculate Command Tests
    @patch("gig_rights.cli.main.SessionLocal")
    @patch("gig_rights.cli.main.init_db")
    @patch("gig_rights.cli.main.AuditRepository")
    def test_calculate_command_accrual_success(
        self, mock_repo_cls, mock_init_db, mock_session_cls
    ):
        """Calculate command executes 12.07% accrual calculation and logs to audit repo."""

        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        result = runner.invoke(
            app,
            [
                "calculate",
                "--worker-id",
                "WORKER-001",
                "--hours",
                "37.5",
                "--pay",
                "750.0",
                "--start",
                "2026-07-01",
                "--end",
                "2026-07-07",
            ],
        )

        assert result.exit_code == 0
        assert "Calculation logged successfully!" in result.stdout
        assert "Entitlement Hours:" in result.stdout
        assert "Holiday Pay Due:" in result.stdout
        mock_repo.log_calculation.assert_called_once()

    @patch("gig_rights.cli.main.SessionLocal")
    @patch("gig_rights.cli.main.init_db")
    @patch("gig_rights.cli.main.AuditRepository")
    def test_calculate_command_rolled_up_pay_success(
        self, mock_repo_cls, mock_init_db, mock_session_cls
    ):
        """Calculate command executes rolled-up pay method when requested."""

        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        result = runner.invoke(
            app,
            [
                "calculate",
                "-w",
                "WORKER-IRR-001",
                "-t",
                "irregular_hours",
                "-m",
                "rolled_up_pay",
                "--hours",
                "20.0",
                "--pay",
                "400.0",
                "--start",
                "2026-07-01",
                "--end",
                "2026-07-07",
            ],
        )

        assert result.exit_code == 0
        assert "Calculation logged successfully!" in result.stdout

    @patch("gig_rights.cli.main.SessionLocal")
    @patch("gig_rights.cli.main.init_db")
    def test_calculate_command_unsupported_method_exits(
        self, mock_init_db, mock_session_cls
    ):
        """Calculate command rejects 52-week reference method with exit code 1."""

        result = runner.invoke(
            app,
            [
                "calculate",
                "-w",
                "WORKER-001",
                "-m",
                "52_week_reference_period",
                "--hours",
                "37.5",
                "--pay",
                "750.0",
                "--start",
                "2026-07-01",
                "--end",
                "2026-07-07",
            ],
        )

        assert result.exit_code == 1
        assert "Use API or batch mode" in result.stdout

    @patch("gig_rights.cli.main.RolledUpPayCalculator")
    @patch("gig_rights.cli.main.SessionLocal")
    @patch("gig_rights.cli.main.init_db")
    @patch("gig_rights.cli.main.AuditRepository")
    def test_calculate_command_handles_compliance_violation(
        self, mock_repo_cls, mock_init_db, mock_session_cls, mock_calc_cls
    ):
        """Catches ValueError exceptions and prints compliance error."""

        mock_calc = MagicMock()
        mock_calc.calculate.side_effect = ValueError(
            "Rolled-up holiday pay is unlawful for fixed-hours workers."
        )
        mock_calc_cls.return_value = mock_calc

        result = runner.invoke(
            app,
            [
                "calculate",
                "-w",
                "WORKER-FIXED",
                "-t",
                "regular_fixed",
                "-m",
                "rolled_up_pay",
                "--hours",
                "37.5",
                "--pay",
                "750.0",
                "--start",
                "2026-07-01",
                "--end",
                "2026-07-07",
            ],
        )

        # Normalize line wraps caused by Rich console output
        clean_stdout = " ".join(result.stdout.split())

        assert result.exit_code == 0
        assert "Compliance Violation Error:" in clean_stdout
        assert "unlawful for fixed-hours workers" in clean_stdout

    # Batch CSV Command Tests
    @patch("gig_rights.cli.main.SessionLocal")
    @patch("gig_rights.cli.main.init_db")
    @patch("gig_rights.cli.main.AuditRepository")
    def test_batch_csv_command_processes_file(
        self, mock_repo_cls, mock_init_db, mock_session_cls, tmp_path
    ):
        """Batch CSV command reads rows, calculates accrual, and records audit entries."""
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        csv_file = tmp_path / "test_pay_periods.csv"
        headers = [
            "worker_id",
            "worker_name",
            "worker_type",
            "start_date",
            "end_date",
            "hours_worked",
            "gross_pay",
        ]
        rows = [
            [
                "WORKER-001",
                "Alex Morgan",
                "irregular_hours",
                "2026-07-01",
                "2026-07-07",
                "37.50",
                "750.00",
            ],
            [
                "WORKER-002",
                "Jordan Lee",
                "part_year",
                "2026-07-01",
                "2026-07-07",
                "20.00",
                "400.00",
            ],
        ]

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

        result = runner.invoke(app, ["batch-csv", str(csv_file)])

        assert result.exit_code == 0
        assert "Successfully batch-processed 2 records" in result.stdout
        assert mock_repo.log_calculation.call_count == 2
