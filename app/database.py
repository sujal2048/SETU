import os
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL)

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

db = Database()

async def get_db():
    if not db.pool:
        raise Exception("Database not connected")
    async with db.pool.acquire() as conn:
        yield conn
