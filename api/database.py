import os
import asyncpg
import redis.asyncio as redis_async
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ciq:ciq_password@localhost:5432/conflictiq")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

class Database:
    pool: Optional[asyncpg.Pool] = None
    redis: Optional[redis_async.Redis] = None

db = Database()

async def connect_db():
    db.pool = await asyncpg.create_pool(DATABASE_URL)
    db.redis = redis_async.from_url(REDIS_URL, decode_responses=True)

async def disconnect_db():
    if db.pool:
        await db.pool.close()
    if db.redis:
        await db.redis.close()

async def get_db_connection():
    async with db.pool.acquire() as conn:
        yield conn

def get_redis():
    return db.redis
