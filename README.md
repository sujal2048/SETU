# Setu Payment Reconciliation Service

This is a lightweight, high-performance backend service to ingest payment lifecycle events, maintain transaction state, and expose APIs for reconciliation.

## Architecture Overview

*   **Framework**: FastAPI (Python) - Chosen for high performance, async support, and auto-generated API documentation.
*   **Database**: PostgreSQL - Chosen for robust ACID guarantees and powerful SQL aggregation/filtering capabilities. We use `asyncpg` for extremely fast async database operations.
*   **Design Philosophy**: "SQL design matters more than Python cleverness." Filtering, sorting, and aggregations are offloaded entirely to Postgres.

## Data Model & Idempotency

The database schema is heavily normalized for efficient querying:
1.  **`merchants`**: Stores unique merchant identifiers and names.
2.  **`transactions`**: Stores the aggregated state of a single payment flow (`amount`, `payment_status`, `settlement_status`). Indexed for fast status/date filtering.
3.  **`events`**: Append-only log of all incoming lifecycle events.

**Idempotency Strategy**: 
We use the `event_id` as the Primary Key for the `events` table. The ingest API uses a PostgreSQL `INSERT ... ON CONFLICT (id) DO NOTHING` query. 
*   If an event is new, it is inserted, and the parent `transaction` state is updated.
*   If a duplicate event is received, Postgres ignores the insert, the transaction state is untouched, and the API returns a successful `200 OK` response.

## Local Setup

### Prerequisites
*   Python 3.11+
*   PostgreSQL running locally (or via Docker)

### Steps
1.  Clone the repository.
2.  Create a virtual environment and install dependencies:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Or `.\venv\Scripts\Activate.ps1` on Windows
    pip install -r requirements.txt
    ```
3.  Set your `DATABASE_URL` environment variable (defaults to `postgresql://postgres:postgres@localhost:5432/postgres`):
    ```bash
    export DATABASE_URL="postgresql://username:password@localhost:5432/setu_db"
    ```
4.  Initialize the database schema:
    ```bash
    python -m app.init_db
    ```
5.  Start the FastAPI application:
    ```bash
    uvicorn app.main:app --reload
    ```
6.  The API will be available at `http://localhost:8000`. You can view the interactive Swagger UI at `http://localhost:8000/docs`.

## Ingesting Sample Data

A script is provided to ingest the 10,000+ events from `sample_events.json`:
```bash
python -m app.script_ingest
```

## API Documentation

FastAPI auto-generates interactive API documentation. Start the server and visit:
*   **Swagger UI**: `http://localhost:8000/docs`
*   **ReDoc**: `http://localhost:8000/redoc`

Endpoints available:
*   `POST /events`: Ingest a payment event.
*   `GET /transactions`: List transactions with filters (`merchant_id`, `status`, `start_date`, `end_date`), pagination (`limit`, `offset`).
*   `GET /transactions/{id}`: Fetch transaction details and its event history.
*   `GET /reconciliation/summary`: Get summarized transaction counts and amounts grouped by merchant, date, and status.
*   `GET /reconciliation/discrepancies`: Identify transactions with conflicting states (e.g., settled but failed, or processed but never settled).

## Public Deployment (Render)

This repository is configured for 1-click deployment on **Render.com**.

1.  Push this code to a public GitHub repository.
2.  Log into Render and click **New > Blueprint**.
3.  Connect your GitHub repository.
4.  Render will read the `render.yaml` file and automatically provision:
    *   A managed PostgreSQL Database.
    *   A Web Service running the FastAPI application.
5.  The `start.sh` script automatically runs the `init_db.py` script before starting the server to ensure the schema is applied.

## Assumptions & Tradeoffs

*   **Raw SQL over ORM**: SQLAlchemy was intentionally excluded. Writing raw SQL via `asyncpg` provides maximum performance and complete control over the queries, honoring the requirement to push logic to the database.
*   **Schema Init**: A simple `init_db.py` script is used instead of a heavy migration tool like Alembic to keep the project incredibly simple and robust to review and deploy.
*   **State Machine**: We assume `payment_status` and `settlement_status` are distinct. The `payment_processed` event updates payment status, while `settled` updates the settlement status independently. This helps flag discrepancies where a settlement arrives for a failed payment.
