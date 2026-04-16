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
    
    # Use Upstash Serverless REST if provided, otherwise Local Redis
    upstash_url = os.getenv("UPSTASH_REDIS_REST_URL")
    upstash_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    
    if upstash_url and upstash_token:
        from upstash_redis.asyncio import Redis as UpstashRedis
        db.redis = UpstashRedis(url=upstash_url, token=upstash_token)
    else:
        db.redis = redis_async.from_url(REDIS_URL, decode_responses=True)

async def disconnect_db():
    if db.pool:
        await db.pool.close()
    if db.redis and hasattr(db.redis, 'close') and callable(db.redis.close):
        await db.redis.close()

async def get_db_connection():
    async with db.pool.acquire() as conn:
        yield conn

def get_redis():
    return db.redis
