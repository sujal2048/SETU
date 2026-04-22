import asyncpg
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID
from app.schemas import PaymentEvent

async def ingest_event(conn: asyncpg.Connection, event: PaymentEvent):
    # Upsert merchant
    await conn.execute('''
        INSERT INTO merchants (id, name, created_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
    ''', event.merchant_id, event.merchant_name)

    # Insert transaction if not exists
    await conn.execute('''
        INSERT INTO transactions (id, merchant_id, amount, currency, created_at, updated_at)
        VALUES ($1, $2, $3, $4, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    ''', event.transaction_id, event.merchant_id, event.amount, event.currency)

    # Insert event (idempotent via ON CONFLICT DO NOTHING)
    status = await conn.execute('''
        INSERT INTO events (id, transaction_id, event_type, timestamp, created_at)
        VALUES ($1, $2, $3, $4, NOW())
        ON CONFLICT (id) DO NOTHING
    ''', event.event_id, event.transaction_id, event.event_type, event.timestamp)

    # If the event was already there, status will be "INSERT 0 0"
    if status == "INSERT 0 1":
        # Event is new, update transaction state
        if event.event_type in ["payment_initiated", "payment_processed", "payment_failed"]:
            payment_status = event.event_type.replace("payment_", "")
            await conn.execute('''
                UPDATE transactions 
                SET payment_status = $1, updated_at = NOW()
                WHERE id = $2
            ''', payment_status, event.transaction_id)
        elif event.event_type == "settled":
            await conn.execute('''
                UPDATE transactions 
                SET settlement_status = 'settled', updated_at = NOW()
                WHERE id = $1
            ''', event.transaction_id)
            
    return status == "INSERT 0 1"

async def list_transactions(conn: asyncpg.Connection, 
                            merchant_id: Optional[str], 
                            status: Optional[str], 
                            start_date: Optional[datetime], 
                            end_date: Optional[datetime], 
                            limit: int, 
                            offset: int):
    query = """
        SELECT * FROM transactions
        WHERE 1=1
    """
    args = []
    idx = 1
    
    if merchant_id:
        query += f" AND merchant_id = ${idx}"
        args.append(merchant_id)
        idx += 1
    if status:
        query += f" AND (payment_status = ${idx} OR settlement_status = ${idx})"
        args.append(status)
        idx += 1
    if start_date:
        query += f" AND created_at >= ${idx}"
        args.append(start_date)
        idx += 1
    if end_date:
        query += f" AND created_at <= ${idx}"
        args.append(end_date)
        idx += 1
        
    query += f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx+1}"
    args.extend([limit, offset])
    
    records = await conn.fetch(query, *args)
    return [dict(r) for r in records]

async def get_transaction(conn: asyncpg.Connection, tx_id: UUID):
    query = """
        SELECT t.*, m.name as merchant_name, 
               (
                   SELECT json_agg(json_build_object(
                       'event_id', e.id,
                       'event_type', e.event_type,
                       'timestamp', e.timestamp
                   ) ORDER BY e.timestamp ASC)
                   FROM events e WHERE e.transaction_id = t.id
               ) as history
        FROM transactions t
        JOIN merchants m ON t.merchant_id = m.id
        WHERE t.id = $1
    """
    record = await conn.fetchrow(query, tx_id)
    if record:
        record_dict = dict(record)
        import json
        if isinstance(record_dict.get('history'), str):
            record_dict['history'] = json.loads(record_dict['history'])
        return record_dict
    return None

async def get_reconciliation_summary(conn: asyncpg.Connection):
    query = """
        SELECT merchant_id, TO_CHAR(created_at, 'YYYY-MM-DD') as date, 
               payment_status, settlement_status, 
               COUNT(*) as total_transactions, SUM(amount) as total_amount
        FROM transactions
        GROUP BY merchant_id, TO_CHAR(created_at, 'YYYY-MM-DD'), payment_status, settlement_status
        ORDER BY date DESC, merchant_id
    """
    records = await conn.fetch(query)
    return [dict(r) for r in records]

async def get_discrepancies(conn: asyncpg.Connection):
    query = """
        SELECT * FROM transactions
        WHERE 
          (payment_status = 'failed' AND settlement_status = 'settled') OR
          (payment_status = 'initiated' AND settlement_status = 'settled') OR
          (payment_status = 'processed' AND (settlement_status != 'settled' OR settlement_status IS NULL) AND updated_at < NOW() - INTERVAL '2 days')
    """
    records = await conn.fetch(query)
    return [dict(r) for r in records]
