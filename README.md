# Setu Payment Reconciliation Service

A high-performance backend service designed to ingest payment lifecycle events, maintain robust transaction states, and expose APIs for reconciliation and discrepancy detection.

---

## 🚀 Live Demo
**Interactive API Documentation (Swagger):** [https://setu-reconciliation-api.onrender.com/docs](https://setu-reconciliation-api.onrender.com/docs)  
**Base API URL:** `https://setu-reconciliation-api.onrender.com`

*The production database is populated with over 10,000 real-world sample events.*

---

## 🏗️ Architecture & Technical Explanation

This service is built prioritizing **performance**, **database-level data integrity**, and **simplicity**.

*   **Web Framework**: **FastAPI** (Python). Chosen for its native asynchronous capabilities, incredible performance, and built-in OpenAPI (Swagger) documentation generation.
*   **Database**: **PostgreSQL**. Chosen for its robust ACID compliance and powerful aggregation capabilities.
*   **Database Driver**: **`asyncpg`**. We bypass heavy ORMs (like SQLAlchemy) and use raw, asynchronous SQL. The assignment emphasized that *"SQL design matters more than Python cleverness"*, and using raw SQL ensures that filtering, pagination, and aggregations are strictly offloaded to the database engine.

### How It Works: Handling Idempotency & State

Payment systems often send duplicate events. The architecture handles this elegantly at the database layer to guarantee idempotency without race conditions:

1.  **Event Ingestion**: When an event payload hits the `/events` endpoint, the system attempts to insert the event into the `events` table using the payload's `event_id` as the Primary Key.
2.  **Conflict Resolution**: We use PostgreSQL's `INSERT ... ON CONFLICT (id) DO NOTHING`. 
    *   If the event is **new**, Postgres inserts it, and the Python layer subsequently updates the parent `transactions` table with the new status (`payment_status` or `settlement_status`).
    *   If the event is a **duplicate**, Postgres safely ignores the insert. The Python layer detects that no new row was added, leaves the transaction state completely untouched, and returns a graceful `200 OK` to the client.

This completely prevents state corruption, even under high concurrency.

---

## 🗄️ Database Model

The database is heavily normalized to support fast, complex queries:

1.  **`merchants`**: Stores unique merchant identifiers and names.
2.  **`transactions`**: The central source of truth for a single payment. It maintains the absolute latest state of both the `payment_status` (e.g., initiated, processed, failed) and `settlement_status` (e.g., pending, settled). Heavily indexed for fast filtering.
3.  **`events`**: An append-only, immutable ledger of all incoming lifecycle events, mapped via `transaction_id`.

---

## 💼 Use Cases & API Features

The system supports Operations Teams in tracking down discrepancies through the following endpoints:

### 1. Event Ingestion (`POST /events`)
Accepts webhook payloads. Updates or creates merchants, tracks the transaction, and logs the event history. Highly idempotent.

### 2. Transaction Listing (`GET /transactions`)
Allows Ops teams to search through millions of transactions efficiently. 
*   **Filters Supported**: `merchant_id`, `status` (matches either payment or settlement status), `start_date`, `end_date`.
*   **Pagination**: Handled via `limit` and `offset` which translates directly to SQL.

### 3. Fetch Transaction Details (`GET /transactions/{id}`)
Given a specific `transaction_id`, returns the current flattened state of the transaction along with a fully ordered `history` array of every event that transaction has ever seen.

### 4. Reconciliation Summary (`GET /reconciliation/summary`)
Provides a high-level view for finance teams. Groups transactions by `merchant`, `date`, `payment_status`, and `settlement_status`, returning the total counts and total monetary volume (`amount`) for each bucket. Aggregated entirely via SQL `GROUP BY`.

### 5. Discrepancy Detection (`GET /reconciliation/discrepancies`)
Automatically flags transactions sitting in impossible or unhealthy states. Identifies scenarios such as:
*   A payment marked as **failed**, but somehow a **settled** event was recorded.
*   A payment marked as **initiated**, but somehow **settled**.
*   A payment marked as **processed** but the settlement never arrived after a specific threshold (e.g., > 2 days).

---

## 💻 Local Setup & Testing

To run the system locally for code review or testing:

**Prerequisites:**
*   Python 3.11+
*   PostgreSQL running locally

**Steps:**
1.  **Clone the repo** and set up your virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    ```
2.  **Set Database URL**:
    ```bash
    # Set this to your local postgres credentials
    export DATABASE_URL="postgresql://username:password@localhost:5432/setu_db"
    ```
3.  **Initialize the Schema**:
    ```bash
    # This securely creates all required tables and indexes
    python -m app.init_db
    ```
4.  **Start the API Server**:
    ```bash
    uvicorn app.main:app --reload
    ```
5.  **Ingest Sample Data**:
    ```bash
    # In a new terminal, run this script to populate the local DB with 10k events
    python -m app.script_ingest
    ```

---

## ⚖️ Assumptions & Tradeoffs

*   **Raw SQL over Alembic/ORM**: To keep the project extremely lightweight, fast, and reviewable, I opted out of heavy ORMs and migration tools (like Alembic). A single `init_db.py` script serves as the DDL source of truth.
*   **Independent State Columns**: `payment_status` and `settlement_status` are tracked as two independent columns in the `transactions` table rather than a single linear `status` column. This intentionally allows the system to capture impossible states (e.g., failed payment + successful settlement) so they can be flagged by the discrepancy endpoint, rather than overwriting the previous status.
