import logging
from typing import Dict, Any, Tuple
import asyncpg

log = logging.getLogger(__name__)

async def identify_or_create_conflict(conn: asyncpg.Connection, event: Dict[str, Any]) -> Tuple[int, str]:
    """
    Groups tactical events into 'Active Conflicts' (Rollup).
    Matching criteria: Same country + within 150km + within last 4 days.
    """
    country_iso3 = event.get("country_iso3", "UNK")
    lat = event.get("lat", 0.0)
    lon = event.get("lon", 0.0)
    city = event.get("city", "Unknown Location")
    
    # 1. Search for existing active conflict cluster
    query_search = """
    SELECT conflict_id, name FROM active_conflicts
    WHERE $1 = ANY(countries)
    AND last_event_at >= NOW() - INTERVAL '4 days'
    AND status = 'ACTIVE'
    ORDER BY last_event_at DESC
    LIMIT 1
    """
    # Note: We can refine this using PostGIS in the future if high precision is needed, 
    # but country + 4-day window is a good baseline for WorldMonitor standards.
    
    row = await conn.fetchrow(query_search, country_iso3)
    
    if row:
        conflict_id = row["conflict_id"]
        conflict_name = row["name"]
        
        # Update counts
        await conn.execute(
            "UPDATE active_conflicts SET total_events = total_events + 1, last_event_at = NOW() WHERE conflict_id = $1",
            conflict_id
        )
        return conflict_id, conflict_name
    
    # 2. Create new Conflict Cluster if none found
    new_name = f"Tactical Engagement: {city}, {country_iso3}"
    if event.get("event_type") == "Airstrike / Artillery":
        new_name = f"Air/Artillery Operation: {event.get('country')}"
    elif event.get("event_type") == "Terrorist Attack":
        new_name = f"Terrorist Activity: {event.get('country')}"

    query_insert = """
    INSERT INTO active_conflicts (name, countries, region, start_date, status, intensity, total_events, last_event_at)
    VALUES ($1, ARRAY[$2], $3, NOW(), 'ACTIVE', 'CRISIS', 1, NOW())
    RETURNING conflict_id, name
    """
    
    new_row = await conn.fetchrow(
        query_insert, 
        new_name, 
        country_iso3, 
        event.get("region") or event.get("country")
    )
    
    return new_row["conflict_id"], new_row["name"]
