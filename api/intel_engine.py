from api.database import db
from datetime import date, timedelta
import logging
import json
from api.ai_logic import ai_service

log = logging.getLogger(__name__)

async def get_daily_sitrep():
    """Generates a summary of the last 24h of conflict activity including tactical details."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    query = """
    SELECT 
        COUNT(*) as total_events,
        SUM(fatalities) as total_fatalities,
        mode() WITHIN GROUP (ORDER BY country) as top_country,
        mode() WITHIN GROUP (ORDER BY category) as top_category,
        mode() WITHIN GROUP (ORDER BY actor1) as most_active_actor
    FROM conflict_events 
    WHERE event_date >= $1
    """
    
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, yesterday)
        
    if not row or row['total_events'] == 0:
        return {"summary": "Stable. No major conflict events reported in the last 24h.", "intensity": "LOW"}

    summary = f"Global Intelligence Alert: Intensity is {'HIGH' if row['total_events'] > 20 else 'STABLE'}. "
    summary += f"{row['total_events']} tactical events reported. "
    summary += f"Major theater: {row['top_country']} ({row['top_category']} activity). "
    if row['most_active_actor']:
        summary += f"Primary actor identified: {row['most_active_actor']}. "
    summary += f"Total estimated fatalities: {row.get('total_fatalities', 0)}."

    return {
        "summary": summary,
        "intensity": "HIGH" if row['total_events'] > 20 else "MEDIUM",
        "stats": dict(row)
    }

async def get_actor_activity():
    """Tracks top 10 actors involved in recent conflicts."""
    query = """
    SELECT actor1, COUNT(*) as involvement_count, SUM(fatalities) as fatal_impact
    FROM conflict_events
    WHERE event_time >= NOW() - INTERVAL '7 days'
      AND actor1 IS NOT NULL
    GROUP BY actor1
    ORDER BY involvement_count DESC
    LIMIT 10
    """
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query)
    return [dict(r) for r in rows]

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
    WHERE curr.cnt > 3 AND (prev.cnt IS NULL OR (curr.cnt > prev.cnt))
    ORDER BY surge_percentage DESC NULLS LAST
    LIMIT 10
    """
    
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query, last_7d, prev_7d)
        
    return [dict(r) for r in rows]

async def get_strategic_forecast():
    """Uses LLM to analyze trends and forecast potential escalations."""
    trends = await get_conflict_trends()
    hotspots = await get_world_hotspots()
    
    if not trends:
        return {"forecast": "Insufficient data for strategic forecasting.", "risk_level": "LOW"}

    prompt = f"""
    As a Senior Strategic Analyst, provide a brief (2-3 sentence) tactical forecast for the following hotspots:
    
    Surge Data: {json.dumps(trends[:3])}
    Recent Hotspots: {json.dumps(hotspots[:3])}
    
    Identify the most critical region for potential escalation in the next 72 hours.
    """
    
    forecast_text = ""
    async for chunk in ai_service.stream_analysis(prompt):
        forecast_text += chunk
        
    return {
        "forecast": forecast_text.strip(),
        "risk_level": "CRITICAL" if any(t['surge_percentage'] and t['surge_percentage'] > 100 for t in trends) else "MODERATE",
        "timestamp": str(date.today())
    }

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

async def get_active_frontlines():
    """Identifies active frontline clusters based on intensity and recency."""
    query = """
    SELECT 
        ST_X(ST_Centroid(ST_Collect(geom::geometry))) as lon,
        ST_Y(ST_Centroid(ST_Collect(geom::geometry))) as lat,
        COUNT(*) as event_count,
        country,
        country_iso3,
        MAX(severity_score) as highest_severity,
        mode() WITHIN GROUP (ORDER BY event_type) as primary_engagement
    FROM conflict_events
    WHERE event_time >= NOW() - INTERVAL '48 hours'
    AND category IN ('MILITARY', 'MILITANT')
    GROUP BY country, country_iso3, ST_SnapToGrid(geom::geometry, 1.5)
    HAVING COUNT(*) >= 2
    ORDER BY event_count DESC
    """
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query)
    return [dict(r) for r in rows]
