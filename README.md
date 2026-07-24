# 📒 Gig-Rights
![Last Commit](https://img.shields.io/github/last-commit/reory/gig-rights?cacheSeconds=60)
![Repo Size](https://img.shields.io/github/repo-size/reory/gig-rights?cacheSeconds=60)
![License](https://img.shields.io/badge/License-MIT-green)

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org/)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)
[![Typer](https://img.shields.io/badge/CLI-Typer-009485?style=flat-square&logo=python&logoColor=white)](https://typer.tiangolo.com/)

GigRights is a UK statutory holiday compliance and audit engine (2026 rules) for irregular, part-year, and fixed-hours workers. It features decimal-precision calculations, immutable SQLite audit logs, a FastAPI service, a Typer CLI, and ReportLab PDF generation.

---

## 🚀 Key Features
- **Statutory Classification Engine:**
Automatically categorizes workers into regular_fixed, irregular_hours, or part_year based on contract terms and shift variability, protecting against unlawful rolled-up pay applications.

---

## 🧮 Multiple Calculation Strategies:

- **12.07% Statutory Accrual:** 
Implements standard percentage accrual for irregular/part-year workers.
- **Rolled-Up Pay Uplift:** 
Calculates 12.07% gross pay uplift with strict legal compliance guards preventing misuse on fixed-hours contracts.
- **52-Week Reference Period:** 
Computes average hourly rates using a 52-week lookback window with statutory zero-remuneration week exclusion (up to 104 weeks).
- **Immutable Audit Trail:** 
Append-only database architecture ensuring full regulatory audit compliance and historical traceability per worker.
- **FastAPI REST API:** 
Fully asynchronous endpoints for real-time classification, calculations, audit retrieval, and PDF streaming.
- **Typer CLI Interface:** 
Comprehensive command-line utility for local operations and batch `CSV` payroll processing.
- **PDF Compliance Reporting:** 
Generates professional `ReportLab` compliance statements and payslip breakdowns.
- **Rigorously Tested:** 
Comprehensive unit tests and property-based invariant tests using pytest and hypothesis.

---

## 📁 Project Directory Structure
```text
gig-rights
|
├── gig_rights/
|   ├── api/
|       └── routes.py          # FastAPI router endpoints (/classify, /calculate, /audit, /reports)
|   │   └── schemas.py         # Pydantic validation models & request/response payloads
|   ├── cli/
|   │   └── main.py            # Typer CLI application (classify, calculate, batch-csv)
|   ├── core/
|   │   ├── calculators/
|   │   │   ├── accrual.py     # 12.07% statutory accrual calculator
|   │   │   ├── base.py        # Abstract base calculator interface
|   │   │   ├── reference_period.py # 52-week lookback average calculator
|   │   │   └── rolled_up.py   # Rolled-up pay calculator with compliance guards
|   │   ├── classification.py  # Worker type decision-support rules engine
|   │   └── models.py          # Core domain models & calculation enums
|   ├── db/
|   │   ├── models.py          # SQLAlchemy ORM models (Workers & Append-only Audit Logs)
|   │   ├── repository.py      # Append-only data access repository layer
|   │   └── session.py         # SQLAlchemy engine & session configuration
|   ├── reports/
│   |   └── pdf_generator.py   # ReportLab PDF compliance statement generator
|   ├── main.py                # FastAPI app entrypoint & lifespan configuration
├── data/
|   └── test_pay_periods.csv   # csv of gig workers pay details
├── tests/                     # Pytest suite
│   ├── test_accrual_calculator.py
│   ├── test_classification.py
│   ├── test_cli.py
│   ├── test_main.py
│   ├── test_models.py
│   ├── test_pdf_generator.py
│   ├── test_reference_period_calculator.py
│   ├── test_repository.py
│   ├── test_rolled_up_calculator.py
│   ├── test_routes.py
│   └── test_session.py
├── Dockerfile             # Container configuration
├── docker-compose.yml     # Multi-container service orchestration
├── Makefile               # Task automation shortcuts
├── pyproject.toml         # Package definition & dependencies
└── README.md              # Project overview
```

---

## 🛠️ Installation & Setup
Clone the repository and navigate to the project root.
```text
git clone [https://github.com/reory/gig-rights.git](https://github.com/reory/gig-rights.git)
cd gig-rights
```
- Ensure Python 3.12+ is installed (configured via .python-version for Python 3.14 compatibility).

### Install dependencies using pip:
```Bash
pip install -e .
```

## 🖥️ Usage
- Running the FastAPI Server
- Start the API development server using Uvicorn:
```Bash
uv run uvicorn gig_rights.main:app --reload
```
The interactive API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Using the Typer CLI
- The package exposes a gig-rights command-line script:

### Classify a worker:
```Bash
gig-rights classify --hours 0.0 --unpaid-weeks
```

### Run a single calculation:
```Bash
gig-rights calculate --worker-id W-001 --hours 37.5 --pay 750.0 --start 2026-07-01 --end 2026-07-07
```

### Batch process a CSV of pay periods:
```Bash
gig-rights batch-csv data/test_pay_periods.csv
```

---

## 🐳 Docker & Makefile Setup

For containerized execution and quick task automation, **Gig-Rights** includes a `Dockerfile`, `docker-compose.yml`, and a `Makefile`.

### Quick Start with Docker Compose
Ensure Docker Desktop is running on your machine, then execute:

```bash
# Build and start services in background
docker compose up -d

# View live API logs
docker compose logs -f

# Stop container services
docker compose down
```

## ⚡ Makefile Shortcuts
- if you have make installed, you can use one-word shortcuts for common tasks:

| Command | Action |
| :--- | :--- |
| `make up` | Start Docker containers in background |
| `make build` | Rebuild image & start services |
| `make logs` | Stream live API logs from container |
| `make test-docker` | Run `pytest` suite inside Docker container |
| `make cli-batch` | Run CSV batch processor inside container |
| `make down` | Stop and remove running containers |
| `make clean` | Purge `__pycache__` and pytest artifacts |

---

## 🧪 Testing & Code Coverage
Run the Pytest suite with coverage reports using pytest:
```Bash
pytest
```

---

## 🧪 API Testing & Example Payloads

When running the FastAPI server (`uvicorn gig_rights.main:app --reload`), visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to access the interactive Swagger UI.

You can paste the sample payload below into the `POST/api/v1/calculate` endpoint to test background calculations and then go to `Get/api/v1/reports/{worker_id}/pdf` to download the PDF generation report:

- **Example**
```json
{
  "worker_id": "WORKER-001",
  "worker_name": "Alex Smith",
  "worker_type": "irregular_hours",
  "leave_year_start": "2026-01-01",
  "method": "12.07_percent_accrual",
  "current_period": {
    "start_date": "2026-07-01",
    "end_date": "2026-07-07",
    "hours_worked": 37.5,
    "gross_pay": 562.50
  },
  "requested_leave_hours": 0,
  "historical_periods": [
    {
      "start_date": "2026-06-24",
      "end_date": "2026-06-30",
      "hours_worked": 35.0,
      "gross_pay": 525.00
    }
  ]
}
```

---

## 📌 Developer Notes & Database Inspection

- When you run the calculation commands or batch-process CSV files, records are automatically committed to a local SQLite database (`gig_rights.db` located at the project root).

### Inspecting Saved Data
You can inspect the generated workers and audit logs using any of the following methods:

* **VS Code Extensions (Recommended):** Install **SQLite Viewer** or **Database Client**, right-click `gig_rights.db` in the file explorer, and choose **Open Database**.

* **SQLite CLI:**
```bash
sqlite3 gig_rights.db "SELECT * FROM workers;"
sqlite3 gig_rights.db "SELECT * FROM calculation_audits LIMIT 10;"
```

- **Python Shell:**

```python
from gig_rights.db.session import SessionLocal
from gig_rights.db.models import CalculationAuditDB

db = SessionLocal()
total_records = db.query(CalculationAuditDB).count()
print(f"Total audit logs in database: {total_records}")
```

---

## ⚠️ Important Notes: 
The audit log architecture is append-only to maintain UK statutory compliance traceability. Deleting or modifying individual calculation rows is strictly restricted at the repository layer.

---

## 🛣️ Roadmap Features

- [ ] **Rust Performance Core:** 
Re-implement heavy 52-week reference period calculations in Rust using PyO3 bindings 
to accelerate enterprise-scale batch processing.

- [ ] **Multi-Tenant SaaS Support:** 
Expand SQLite architecture to PostgreSQL with tenant isolation for multi-company 
payroll auditing.

- [ ] **Interactive Frontend Dashboard:** 
Build a modern web interface in React/Next.js for real-time compliance 
visualization and analytics.

- [ ] **Payroll System Integrations:** 
Add native sync adapters for major HR and accounting platforms like Xero, 
QuickBooks, and Sage.

- [ ] **Real-Time Compliance Alerts:** 
Implement Webhook, Slack, and email notifications for unlawful rolled-up pay or 
misclassification risks.

- [ ] **HMRC Audit Exports:** 
Generate official HMRC-compliant XML and CSV reports for statutory 
record-keeping inspections.

- [ ] **Worker Self-Service Portal:** 
Allow irregular workers to log in, view accrued statutory holiday entitlement, 
and submit leave requests.

- [ ] **Automated Anomaly Detection:** 
Incorporate machine learning to flag unusual shift patterns and proactive 
worker misclassification warnings.

---

* **Built by Roy Peters** 😊
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Roy%20Peters-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/roy-p-74980b382/)