from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Any
from decimal import Decimal
from uuid import UUID

class PaymentEvent(BaseModel):
    event_id: UUID
    event_type: str
    transaction_id: UUID
    merchant_id: str
    merchant_name: str
    amount: Decimal
    currency: str
    timestamp: datetime

class TransactionFilter(BaseModel):
    merchant_id: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class TransactionBase(BaseModel):
    id: UUID
    merchant_id: str
    amount: Decimal
    currency: str
    payment_status: Optional[str] = None
    settlement_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class TransactionDetails(TransactionBase):
    merchant_name: str

class TransactionWithHistory(TransactionDetails):
    history: Optional[List[dict]] = None

class ReconciliationSummary(BaseModel):
    merchant_id: str
    date: str
    payment_status: Optional[str] = None
    settlement_status: Optional[str] = None
    total_transactions: int
    total_amount: Decimal

class Discrepancy(TransactionBase):
    pass
