import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.database import connect_db, disconnect_db, db
from api.routes import conflicts, stats, websocket, intel, intel_hub, ai_analyst

log = logging.getLogger("api.main")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — wrapped so a DB hiccup doesn't kill the whole process
    try:
        await connect_db()
        log.info("Database and Redis connected successfully.")
    except Exception as e:
        log.error(f"Startup DB/Redis connection failed (will retry on requests): {e}")
    yield
    # Shutdown
    try:
        await disconnect_db()
    except Exception as e:
        log.error(f"Error during shutdown disconnect: {e}")

app = FastAPI(
    title="ConflictIQ API",
    version="2.0",
    description="Real-time conflict intelligence API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(conflicts.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")
app.include_router(intel.router, prefix="/api/v1")
app.include_router(intel_hub.router, prefix="/api/v1")
app.include_router(ai_analyst.router, prefix="/api/v1")

@app.get("/", tags=["Root"])
async def root():
    return {"service": "ConflictIQ API", "version": "2.0", "status": "running"}

@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    row_count = 0
    db_ok = False
    if db.pool:
        try:
            async with db.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT count(*) FROM conflict_events")
                row_count = row["count"] if row else 0
                db_ok = True
        except Exception as e:
            log.error(f"Health check DB query failed: {e}")
    return {
        "status": "OK",
        "events_total": row_count,
        "database_connected": db_ok,
        "redis_connected": db.redis is not None,
    }
