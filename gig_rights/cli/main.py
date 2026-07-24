"""
Typer CLI application for local calculations, worker classification,
and batch CSV processing.
"""

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from gig_rights.core.calculators.accrual import AccrualCalculator
from gig_rights.core.calculators.rolled_up import RolledUpPayCalculator
from gig_rights.core.classification import ClassificationInput, WorkerClassifier
from gig_rights.core.models import CalculationMethod, PayPeriod, Worker, WorkerType
from gig_rights.db.repository import AuditRepository
from gig_rights.db.session import Base, SessionLocal, engine

app = typer.Typer(
    name="gig-rights",
    help="GigRights CLI: Statutory holiday entitlement calculations and compliance auditing.",
    add_completion=False,
)

console = Console()


def init_db():
    """Ensure database tables exist before running CLI commands."""

    logger.debug("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)


@app.command("classify")
def classify_cmd(
    contracted_hours: float = typer.Option(
        ..., "--hours", "-h", help="Contracted hours per period (0 if variable)"
    ),
    has_fixed_pattern: bool = typer.Option(
        False, "--fixed-pattern", help="Set if worker has a fixed rotating pattern"
    ),
    has_unpaid_weeks: bool = typer.Option(
        False, "--unpaid-weeks", help="Set if worker has unpaid non-working weeks"
    ),
):
    """Classify a worker under UK statutory regulations based on contract terms."""

    logger.info(
        f"Executing worker classification | Hours: {contracted_hours} | "
        f"Fixed Pattern: {has_fixed_pattern} | Unpaid Weeks: {has_unpaid_weeks}"
    )

    inp = ClassificationInput(
        hours_vary_by_contractor=(contracted_hours == 0.0 or has_fixed_pattern),
        fixed_rotation_pattern=has_fixed_pattern,
        unpaid_weeks_in_leave_year=has_unpaid_weeks,
    )

    result = WorkerClassifier.classify(inp)
    logger.info(
        f"Classification result: {result.worker_type.value} | "
        f"Rolled-Up Lawful: {result.rolled_up_pay_lawful} "
    )

    table = Table(title="Worker Classification Result")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Classification", result.worker_type.value)
    table.add_row(
        "Rolled-Up Pay Allowed?", "YES" if result.rolled_up_pay_lawful else "NO"
    )
    table.add_row("Legal Reasoning", result.rationale)

    if result.compliance_warning:
        logger.warning(f"Compliance warning issued: {result.compliance_warning}")
        table.add_row(
            "Compliance Warning", f"[bold red]{result.compliance_warning}[/bold red]"
        )

    console.print(table)


@app.command("calculate")
def calculate_cmd(
    worker_id: str = typer.Option(
        ..., "--worker-id", "-w", help="Worker unique identifier"
    ),
    worker_name: str = typer.Option("CLI Worker", "--name", "-n", help="Worker name"),
    worker_type: Annotated[
        WorkerType,
        typer.Option(
            "--type",
            "-t",
            help="Worker classification",
        ),
    ] = WorkerType.IRREGULAR_HOURS,
    method: Annotated[
        CalculationMethod,
        typer.Option("--method", "-m"),
    ] = CalculationMethod.STATUTORY_ACCRUAL_1207,
    hours_worked: float = typer.Option(
        ..., "--hours", help="Hours worked in pay period"
    ),
    gross_pay: float = typer.Option(
        ..., "--pay", help="Gross pay earned in pay period"
    ),
    period_start: str = typer.Option(
        ..., "--start", help="Period start date (YYYY-MM-DD)"
    ),
    period_end: str = typer.Option(..., "--end", help="Period end date (YYYY-MM-DD)"),
):
    """Run a single statutory calculation and commit the entry to the audit log."""
    logger.info(
        f"Initiating single calculaton | Worker ID: {worker_id} | Method: {method.value}"
    )
    init_db()

    start_date = datetime.strptime(period_start, "%Y-%m-%d").date()  # noqa: DTZ007
    end_date = datetime.strptime(period_end, "%Y-%m-%d").date()  # noqa: DTZ007

    worker = Worker(
        id=worker_id,
        name=worker_name,
        worker_type=worker_type,
        leave_year_start=start_date,
    )
    pay_period = PayPeriod(
        start_date=start_date,
        end_date=end_date,
        hours_worked=Decimal(str(hours_worked)),
        gross_pay=Decimal(str(gross_pay)),
    )

    db = SessionLocal()
    try:
        repo = AuditRepository(db)
        repo.get_or_create_worker(worker)

        if method == CalculationMethod.STATUTORY_ACCRUAL_1207:
            calc = AccrualCalculator()
            res = calc.calculate(worker, pay_period)
        elif method == CalculationMethod.ROLLED_UP_PAY:
            calc = RolledUpPayCalculator()
            res = calc.calculate(worker, pay_period)
        else:
            logger.error(
                f"Unsupoorted CLI calculation method requested: {method.value}"
            )
            console.print(
                "[bold red]Use API or batch mode for 52-week "
                "reference period calculations.[/bold red]"
            )
            raise typer.Exit(code=1)

        repo.log_calculation(res, pay_period)
        logger.success(f"Calculation successfully logged for worker {worker_id}")

        console.print("[bold green]✓ Calculation logged successfully![/bold green]")
        console.print(f"Entitlement Hours: [bold]{res.entitlement_hours} hrs[/bold]")
        console.print(f"Holiday Pay Due: [bold]£{res.holiday_pay_due}[/bold]")

    except ValueError as err:
        logger.error(f"Compliance Violation error: {err}")
        console.print(f"[bold red]Compliance Violation Error:[/bold red] {err}")
    finally:
        db.close()


@app.command("batch-csv")
def batch_csv_cmd(
    csv_file: Annotated[
        Path,
        typer.Argument(
            ..., help="Path to CSV containing pay period records", exists=True
        ),
    ],
):
    """
    Batch process a CSV of worker pay periods and record statutory calculations
    into the audit log.
    Expected CSV columns: worker_id, worker_name, worker_type, start_date,
    end_date, hours_worked, gross_pay
    """

    logger.info(f"Starting CSV batch processing for: {csv_file}")

    init_db()
    db = SessionLocal()
    repo = AuditRepository(db)

    processed_count = 0
    try:
        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                start_date = datetime.strptime(row["start_date"], "%Y-%m-%d").date()  # noqa: DTZ007
                end_date = datetime.strptime(row["end_date"], "%Y-%m-%d").date()  # noqa: DTZ007
                w_type = WorkerType(row["worker_type"])

                worker = Worker(
                    id=row["worker_id"],
                    name=row["worker_name"],
                    worker_type=w_type,
                    leave_year_start=start_date,
                )
                pay_period = PayPeriod(
                    start_date=start_date,
                    end_date=end_date,
                    hours_worked=Decimal(row["hours_worked"]),
                    gross_pay=Decimal(row["gross_pay"]),
                )

                repo.get_or_create_worker(worker)

                calc = AccrualCalculator()
                res = calc.calculate(worker, pay_period)
                repo.log_calculation(res, pay_period)

                processed_count += 1
                logger.debug(
                    f"Processed row {processed_count} | Worker ID: {row['worker_id']}"
                )
        logger.success(
            f"Batch processing completed | Processed {processed_count} records from {csv_file.name}"
        )
        console.print(
            f"[bold green]✓ Successfully batch-processed {processed_count} "
            f"records from {csv_file.name}[/bold green]"
        )
    except Exception as err:  # noqa: BLE001
        logger.exception(f"Failed during batch CSV processing for {csv_file.name}")
        console.print(f"[bold red]Batch Processing Error:[bold red] {err}")
    finally:
        db.close()


if __name__ == "__main__":
    app()
