import os
import asyncpg
import logging
import json
from typing import Dict, Any, Optional
import ssl
from poller.conflict_tracker import identify_or_create_conflict

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
        if "neon.tech" in db_url or "aws.neon.tech" in db_url:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
        _pool = await asyncpg.create_pool(db_url, ssl=ssl_context)
    return _pool

async def upsert_event(event: Dict[str, Any]):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Guard: Reject events that failed geocoding entirely
        if event.get("lat", 0) == 0.0 and event.get("lon", 0) == 0.0:
            log.warning(f"Dropping event with (0,0) coordinates: {event.get('title', '')[:60]}")
            return None

        # Use Conflict Tracker to group events
        try:
            conflict_id, conflict_name = await identify_or_create_conflict(conn, event)
        except Exception as e:
            log.warning(f"Conflict tracking failed: {e}")
            conflict_id, conflict_name = None, None

        # --- WORLD MONITOR TRIANGULATION: Proximity Search ---
        # Search for an event within 10km and +/- 12 hours
        search_query = """
        SELECT event_id, verification_count, source_urls FROM conflict_events 
        WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint($1, $2), 4326), 10000)
          AND event_time >= $3::timestamp - INTERVAL '12 hours'
          AND event_time <= $3::timestamp + INTERVAL '12 hours'
        LIMIT 1;
        """
        existing = await conn.fetchrow(search_query, event["lon"], event["lat"], event["event_time"])
        
        if existing:
            # INTERFACE: Update existing event with new source and increment verification
            log.info(f"Triangulation Successful: Merging {event['event_id']} with existing {existing['event_id']}")
            update_query = """
            UPDATE conflict_events SET
                verification_count = verification_count + 1,
                source_urls = array_append(source_urls, $2),
                severity_score = GREATEST(severity_score, $3),
                notes = notes || '\n[UPDATE] ' || $4,
                ingested_at = NOW()
            WHERE event_id = $1;
            """
            await conn.execute(update_query, existing["event_id"], event.get("source_url"), event.get("severity_score", 0.0), event.get("notes", ""))
            return existing["event_id"]


        query = """
        INSERT INTO conflict_events (
            event_id, source, source_reliability, event_time, event_date,
            country, country_iso3, region, admin1, admin2, city,
            lat, lon, geom, geo_precision,
            event_type, event_subtype, interaction_code,
            actor1, actor1_type, actor2, actor2_type,
            fatalities, fatalities_civilians, fatalities_confidence,
            severity, severity_score, title, notes, tags, source_url, category,
            conflict_id, conflict_name,
            geo_confidence, geo_method, geocode_provider, location_raw,
            ai_analysis, strategic_relevance, source_urls
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
            $12::double precision, $13::double precision, ST_SetSRID(ST_MakePoint($13::double precision, $12::double precision), 4326), $14,
            $15, $16, $17, $18, $19, $20, $21,
            $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33,
            $34, $35, $36, $37, $38, $39, ARRAY[$30]::text[]
        )
        ON CONFLICT (event_id) DO UPDATE SET
            severity_score = EXCLUDED.severity_score,
            notes = EXCLUDED.notes,
            category = EXCLUDED.category,
            geo_precision = EXCLUDED.geo_precision,
            geo_confidence = EXCLUDED.geo_confidence,
            geo_method = EXCLUDED.geo_method,
            location_raw = EXCLUDED.location_raw,
            ai_analysis = EXCLUDED.ai_analysis,
            conflict_id = EXCLUDED.conflict_id,
            conflict_name = EXCLUDED.conflict_name,
            strategic_relevance = EXCLUDED.strategic_relevance,
            ingested_at = NOW();
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
            event["title"],
            event.get("notes"),
            event.get("tags", []),
            event.get("source_url"),
            event.get("category", "GENERAL"),
            conflict_id,
            conflict_name,
            event.get("geo_confidence"),
            event.get("geo_method"),
            event.get("geocode_provider"),
            event.get("location_raw"),
            event.get("ai_analysis"),
            event.get("strategic_relevance", "LOW")
        )
        
        try:
            await conn.execute(query, *values)
            
            # Real-time Broadcast: Notify the WebSocket listener with Enriched Intel
            payload = {
                "event_id": event["event_id"],
                "title": event["title"],
                "city": event.get("city"),
                "country": event["country"],
                "country_iso3": event.get("country_iso3"),
                "lat": event["lat"],
                "lon": event["lon"],
                "geo_precision": event.get("geo_precision", 3),
                "geo_confidence": event.get("geo_confidence", 0.0),
                "severity_score": event.get("severity_score", 0.0),
                "event_type": event.get("event_type"),
                "category": event.get("category", "GENERAL"),
                "event_time": str(event["event_time"]),
                "actor1": event.get("actor1"),
                "weapon": event.get("weapon"),
                "fatalities": event.get("fatalities", 0),
                "notes": event.get("notes", ""),
                "ai_analysis": event.get("ai_analysis", ""),
                "strategic_relevance": event.get("strategic_relevance", "LOW"),
                "verification_count": 1,
                "source_urls": [event.get("source_url", "")],
                "source_url": event.get("source_url", "")
            }
            await conn.execute(f"SELECT pg_notify('new_conflict_event', $1)", json.dumps(payload))
            log.debug(f"Upserted and Enriched Notified event {event['event_id']}")
        except Exception as e:
            log.error(f"Failed to upsert/notify event {event['event_id']}: {e}")

async def prune_old_events():
    pool = await get_pool()
    query = "DELETE FROM conflict_events WHERE event_time < NOW() - INTERVAL '18 months';"
    try:
        async with pool.acquire() as conn:
            await conn.execute(query)
            log.info("Pruned old events.")
    except Exception as e:
        log.error(f"Failed to prune old events: {e}")
async def retroactive_cleanup():
    log.info("Starting retroactive data cleanup...")
    pool = await get_pool()
    queries = [
        "UPDATE conflict_events SET country_iso3 = TRIM(country_iso3)",
        "UPDATE conflict_events SET country_iso3 = 'BLR' WHERE country_iso3 = 'BY'",
        "UPDATE conflict_events SET country_iso3 = 'THA' WHERE country_iso3 = 'TH'",
        "UPDATE conflict_events SET country_iso3 = 'RUS' WHERE country_iso3 = 'RU'",
        "UPDATE conflict_events SET country_iso3 = 'USA' WHERE country_iso3 = 'US'",
        "UPDATE conflict_events SET country_iso3 = 'SDN' WHERE country_iso3 = 'SD'",
        "UPDATE conflict_events SET country_iso3 = 'ETH' WHERE country_iso3 = 'ET'",
        # Fix Event Types
        "UPDATE conflict_events SET event_type = 'Airstrike / Artillery' WHERE event_type = 'Violence' AND (title ILIKE '%air strike%' OR title ILIKE '%airstrike%' OR title ILIKE '%shelling%' OR title ILIKE '%missile%')",
        "UPDATE conflict_events SET event_type = 'Terrorist Attack' WHERE event_type = 'Violence' AND (title ILIKE '%terror%' OR title ILIKE '%suicide%' OR title ILIKE '%bombing%' OR title ILIKE '%blast%')",
        "UPDATE conflict_events SET event_type = 'Armed Clash' WHERE event_type = 'Violence' AND (title ILIKE '%clash%' OR title ILIKE '%battle%' OR title ILIKE '%fighting%')",
        "UPDATE conflict_events SET event_type = 'Strategic Report' WHERE event_type = 'Violence' AND (title ILIKE '%report%' OR title ILIKE '%analysis%')"
    ]
    try:
        async with pool.acquire() as conn:
            for q in queries:
                await conn.execute(q)
            log.info("Retroactive cleanup complete.")
    except Exception as e:
        log.error(f"Failed retroactive cleanup: {e}")
