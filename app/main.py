from fastapi import FastAPI, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from uuid import UUID
import uvicorn

from app.database import db, get_db
from app.schemas import PaymentEvent, TransactionFilter, TransactionDetails, TransactionWithHistory, ReconciliationSummary, Discrepancy
from app import crud

app = FastAPI(title="Setu Payment Reconciliation API")

@app.on_event("startup")
async def startup_event():
    await db.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await db.disconnect()

@app.post("/events", status_code=201)
async def ingest_event(event: PaymentEvent, conn = Depends(get_db)):
    inserted = await crud.ingest_event(conn, event)
    if not inserted:
        return {"status": "ignored", "message": "Event already processed"}
    return {"status": "success", "message": "Event ingested successfully"}

@app.get("/transactions", response_model=List[TransactionDetails])
async def list_transactions(
    merchant_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conn = Depends(get_db)
):
    return await crud.list_transactions(conn, merchant_id, status, start_date, end_date, limit, offset)

@app.get("/transactions/{transaction_id}", response_model=TransactionWithHistory)
async def get_transaction(transaction_id: UUID, conn = Depends(get_db)):
    tx = await crud.get_transaction(conn, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx

@app.get("/reconciliation/summary", response_model=List[ReconciliationSummary])
async def get_reconciliation_summary(conn = Depends(get_db)):
    return await crud.get_reconciliation_summary(conn)

@app.get("/reconciliation/discrepancies", response_model=List[Discrepancy])
async def get_discrepancies(conn = Depends(get_db)):
    return await crud.get_discrepancies(conn)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
