import asyncio
import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

async def init_db():
    print("Connecting to database to initialize schema...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Create merchants table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS merchants (
                id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        
        # Create transactions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id UUID PRIMARY KEY,
                merchant_id VARCHAR REFERENCES merchants(id),
                amount DECIMAL NOT NULL,
                currency VARCHAR NOT NULL,
                payment_status VARCHAR,
                settlement_status VARCHAR,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        
        # Create events table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id UUID PRIMARY KEY,
                transaction_id UUID REFERENCES transactions(id),
                event_type VARCHAR NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        
        # Create indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_merchant ON transactions(merchant_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_payment_status ON transactions(payment_status);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_settlement_status ON transactions(settlement_status);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_events_transaction ON events(transaction_id);")
        
        print("Database schema initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(init_db())
