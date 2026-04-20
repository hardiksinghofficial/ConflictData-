import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.database import connect_db, disconnect_db, db
from api.routes import conflicts, stats, websocket, intel, intel_hub, ai_analyst
import os
from contextlib import asynccontextmanager

log = logging.getLogger("api.main")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — wrapped so a DB hiccup doesn't kill the whole process
    try:
        await connect_db()
        from api.bootstrap import bootstrap_db
        await bootstrap_db()
        log.info("Database and Redis connected successfully. Bootstrap complete.")
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

# Mount API Routers
app.include_router(conflicts.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")
app.include_router(intel.router, prefix="/api/v1")
app.include_router(intel_hub.router, prefix="/api/v1")
app.include_router(ai_analyst.router, prefix="/api/v1")

# --- Frontend Serving Layer ---
# Check if frontend/dist exists
front_dist = os.path.join(os.getcwd(), "frontend", "dist")

if os.path.exists(front_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(front_dist, "assets")), name="assets")
    
    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(front_dist, "index.html"))

    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        # Only serve index for non-API routes
        if full_path.startswith("api/v1") or full_path.startswith("health") or full_path.startswith("docs"):
            return None # FastAPI will handle via routing
        
        # Check if it's a static file that exists
        file_path = os.path.join(front_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        return FileResponse(os.path.join(front_dist, "index.html"))
else:
    @app.get("/", tags=["Root"])
    async def root():
        return {"service": "ConflictIQ API", "version": "2.0", "status": "running", "frontend": "not_found"}

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
