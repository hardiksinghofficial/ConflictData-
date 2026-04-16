import os
import asyncpg
import logging
from typing import Dict, Any

log = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ciq:ciq_password@localhost:5432/conflictiq")
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

_pool = None

async def get_pool():
    global _pool
    if not _pool:
        db_url = DATABASE_URL
        if '?' in db_url:
            db_url = db_url.split('?')[0]
            
        ssl_context = None
        if "neon.tech" in db_url:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
        _pool = await asyncpg.create_pool(db_url, ssl=ssl_context)
    return _pool

async def upsert_event(event: Dict[str, Any]):
    pool = await get_pool()
    query = """
    INSERT INTO conflict_events (
        event_id, source, source_reliability, event_time, event_date,
        country, country_iso3, region, admin1, admin2, city,
        lat, lon, geom, geo_precision,
        event_type, event_subtype, interaction_code,
        actor1, actor1_type, actor2, actor2_type,
        fatalities, fatalities_civilians, fatalities_confidence,
        severity, severity_score, title, notes, tags, source_url
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
        $12::numeric, $13::numeric, ST_SetSRID(ST_MakePoint($13::double precision, $12::double precision), 4326), $14::smallint,
        $15, $16, $17, $18, $19, $20, $21,
        $22, $23, $24, $25, $26::numeric, $27, $28, $29, $30
    )
    ON CONFLICT (event_id) DO NOTHING;
    """
    
    values = (
        event["event_id"],
        event.get("source", "UNKNOWN"),
        event.get("source_reliability", "MEDIUM"),
        event["event_time"],
        event["event_date"],
        event["country"],
        event["country_iso3"],
        event.get("region"),
        event.get("admin1"),
        event.get("admin2"),
        event.get("city"),
        event["lat"],
        event["lon"],
        event.get("geo_precision", 3),
        event.get("event_type"),
        event.get("event_subtype"),
        event.get("interaction_code"),
        event.get("actor1"),
        event.get("actor1_type"),
        event.get("actor2"),
        event.get("actor2_type"),
        event.get("fatalities", 0),
        event.get("fatalities_civilians", 0),
        event.get("fatalities_confidence", "LOW"),
        event.get("severity", "LOW"),
        event.get("severity_score", 0.0),
        event.get("title"),
        event.get("notes"),
        event.get("tags", []),
        event.get("source_url")
    )
    
    try:
        async with pool.acquire() as conn:
            await conn.execute(query, *values)
            log.debug(f"Upserted event {event['event_id']}")
    except Exception as e:
        log.error(f"Failed to upsert event {event['event_id']}: {e}")

async def prune_old_events():
    log.info("Running automatic pruning of old events...")
    pool = await get_pool()
    query = """
    DELETE FROM conflict_events WHERE event_time < NOW() - INTERVAL '18 months';
    """
    try:
        async with pool.acquire() as conn:
            await conn.execute(query)
            log.info("Pruned old events.")
    except Exception as e:
        log.error(f"Failed to prune old events: {e}")
