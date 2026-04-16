from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.database import connect_db, disconnect_db, db
from api.routes import conflicts, stats, websocket

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_db()
    yield
    # Shutdown
    await disconnect_db()

app = FastAPI(
    title="ConflictIQ API",
    version="2.0",
    description="Real-time conflict intelligence API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production replace with origins from env
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(conflicts.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    row_count = 0
    if db.pool:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT count(*) FROM conflict_events")
            row_count = row["count"] if row else 0
            
    return {
        "status": "OK",
        "events_total": row_count,
        "database_connected": db.pool is not None,
        "redis_connected": db.redis is not None
    }
