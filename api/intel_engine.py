from api.database import db
from datetime import date, timedelta
import logging

log = logging.getLogger(__name__)

async def get_daily_sitrep():
    """Generates a summary of the last 24h of conflict activity."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    query = """
    SELECT 
        COUNT(*) as total_events,
        SUM(fatalities) as total_fatalities,
        mode() WITHIN GROUP (ORDER BY country) as top_country,
        mode() WITHIN GROUP (ORDER BY category) as top_category
    FROM conflict_events 
    WHERE event_date >= $1
    """
    
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, yesterday)
        
    if not row or row['total_events'] == 0:
        return {"summary": "Stable. No major conflict events reported in the last 24h.", "intensity": "LOW"}

    summary = f"Intensity is HIGH. {row['total_events']} events reported globally. "
    summary += f"Major focus in {row['top_country']} with heavy {row['top_category']} activity. "
    summary += f"Total reported fatalities: {row.get('total_fatalities', 0)}."

    return {
        "summary": summary,
        "intensity": "HIGH" if row['total_events'] > 20 else "MEDIUM",
        "stats": dict(row)
    }

async def get_conflict_trends():
    """Identifies countries where violence is surging compared to previous week."""
    last_7d = date.today() - timedelta(days=7)
    prev_7d = date.today() - timedelta(days=14)
    
    query = """
    WITH current_week AS (
        SELECT country_iso3, COUNT(*) as cnt FROM conflict_events 
        WHERE event_date >= $1 GROUP BY country_iso3
    ),
    previous_week AS (
        SELECT country_iso3, COUNT(*) as cnt FROM conflict_events 
        WHERE event_date >= $2 AND event_date < $1 GROUP BY country_iso3
    )
    SELECT 
        curr.country_iso3, 
        curr.cnt as current_count, 
        prev.cnt as previous_count,
        ROUND(((curr.cnt - COALESCE(prev.cnt, 0))::numeric / NULLIF(prev.cnt, 0)) * 100, 2) as surge_percentage
    FROM current_week curr
    LEFT JOIN previous_week prev ON curr.country_iso3 = prev.country_iso3
    WHERE curr.cnt > 5 AND (prev.cnt IS NULL OR (curr.cnt > prev.cnt))
    ORDER BY surge_percentage DESC NULLS LAST
    LIMIT 10
    """
    
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query, last_7d, prev_7d)
        
    return [dict(r) for r in rows]

async def get_world_hotspots():
    """Finds geographic clusters of intense activity."""
    query = """
    SELECT 
        ST_X(ST_Centroid(ST_Collect(geom::geometry))) as lon,
        ST_Y(ST_Centroid(ST_Collect(geom::geometry))) as lat,
        COUNT(*) as event_count,
        country_iso3
    FROM conflict_events
    WHERE event_date >= NOW() - INTERVAL '72 hours'
    GROUP BY country_iso3, ST_SnapToGrid(geom::geometry, 1.0)
    HAVING COUNT(*) > 2
    ORDER BY event_count DESC
    LIMIT 20
    """
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query)
    return [dict(r) for r in rows]
async def get_priority_monitor():
    """Returns the most critical/severe events for the 'Top Level' dashboard feed."""
    query = """
    SELECT * FROM conflict_events
    WHERE severity_score >= 8.5 
       OR event_type IN ('Airstrike / Artillery', 'Terrorist Attack')
    ORDER BY event_time DESC
    LIMIT 15
    """
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query)
    return [dict(r) for r in rows]
