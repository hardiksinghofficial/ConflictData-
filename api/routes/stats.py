from fastapi import APIRouter, Request
from api.database import db
import json
from datetime import date, timedelta
from collections import defaultdict
from fastapi.encoders import jsonable_encoder

router = APIRouter(tags=["Stats"])

async def check_cache(request: Request, cache_key: str):
    if db.redis:
        cached = await db.redis.get(cache_key)
        if cached:
            return json.loads(cached)
    return None

async def set_cache(cache_key: str, data: dict, ttl: int):
    if db.redis:
        await db.redis.setex(cache_key, ttl, json.dumps(jsonable_encoder(data)))

@router.get("/stats")
async def get_stats(request: Request, country: str = None, days: int = 30):
    cache_key = f"stats:{country}:{days}"
    cached = await check_cache(request, cache_key)
    if cached:
        return cached

    from_date = date.today() - timedelta(days=days)
    params = [from_date]
    query = "SELECT * FROM conflict_events WHERE event_date >= $1"
    if country:
        query += " AND country_iso3 = $2"
        params.append(country)
        
    async with db.pool.acquire() as conn:
        records = await conn.fetch(query, *params)
        
    stats_data = {
        "country": country if country else "Global",
        "period_days": days,
        "total_events": len(records),
        "by_type": defaultdict(int),
        "by_severity": defaultdict(int),
        "total_fatalities": 0,
        "civilian_fatalities": 0,
        "events_last_24h": 0
    }
    
    twenty_four_hours_ago = date.today() - timedelta(days=1)
    
    for r in records:
        stats_data["by_type"][r["event_type"] or "Unknown"] += 1
        stats_data["by_severity"][r["severity"] or "UNKNOWN"] += 1
        stats_data["total_fatalities"] += r["fatalities"] or 0
        stats_data["civilian_fatalities"] += r["fatalities_civilians"] or 0
        if r["event_date"] >= twenty_four_hours_ago:
            stats_data["events_last_24h"] += 1
            
    stats_data["by_type"] = dict(stats_data["by_type"])
    stats_data["by_severity"] = dict(stats_data["by_severity"])
    stats_data["trend"] = "STABLE" # Placeholder logic
    
    await set_cache(cache_key, stats_data, ttl=600) # 10min TTL
    return stats_data

@router.get("/active-conflicts")
async def get_active_conflicts(request: Request):
    cache_key = "active_conflicts"
    cached = await check_cache(request, cache_key)
    if cached:
        return cached
        
    query = "SELECT * FROM active_conflicts WHERE last_event_at >= NOW() - INTERVAL '7 days' ORDER BY last_event_at DESC LIMIT 20"
    async with db.pool.acquire() as conn:
        records = await conn.fetch(query)
        
    data = [dict(r) for r in records]
    for d in data:
        if d.get("start_date"):
            d["start_date"] = d["start_date"].isoformat()
        if d.get("last_event_at"):
            d["last_event_at"] = d["last_event_at"].isoformat() + "Z"
            
    await set_cache(cache_key, data, ttl=300) # 5min TTL for live monitor
    return data
