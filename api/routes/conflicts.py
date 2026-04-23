from fastapi import APIRouter, Query, Depends, HTTPException, Request
from typing import Optional, List
from datetime import date, timedelta
from api.database import db
import json
from fastapi.encoders import jsonable_encoder

router = APIRouter(prefix="/conflicts", tags=["Conflicts"])

async def check_cache(request: Request, cache_key: str):
    if db.redis:
        cached = await db.redis.get(cache_key)
        if cached:
            return json.loads(cached)
    return None

async def set_cache(cache_key: str, data: dict, ttl: int):
    if db.redis:
        await db.redis.setex(cache_key, ttl, json.dumps(jsonable_encoder(data)))

@router.get("")
async def get_conflicts(
    request: Request,
    country: Optional[str] = None,
    category: Optional[str] = None,
    from_date: Optional[date] = Query(default_factory=lambda: date.today() - timedelta(days=7)),
    to_date: Optional[date] = Query(default_factory=lambda: date.today()),
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    min_fatalities: int = 0,
    tags: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0
):
    cache_key = f"conflicts:{country}:{category}:{from_date}:{to_date}:{event_type}:{severity}:{min_fatalities}:{tags}:{limit}:{offset}"
    cached = await check_cache(request, cache_key)
    if cached:
        cached["meta"]["from_cache"] = True
        return cached

    query = "SELECT * FROM conflict_events WHERE event_date >= $1 AND event_date <= $2"
    params = [from_date, to_date]
    idx = 3

    if country:
        query += f" AND country_iso3 = ${idx}"
        params.append(country)
        idx += 1
    if category:
        query += f" AND category = ${idx}"
        params.append(category.upper())
        idx += 1
    if event_type:
        query += f" AND event_type = ${idx}"
        params.append(event_type)
        idx += 1
    if severity:
        query += f" AND severity = ${idx}"
        params.append(severity)
        idx += 1
    if min_fatalities > 0:
        query += f" AND fatalities >= ${idx}"
        params.append(min_fatalities)
        idx += 1
    if tags:
        tag_list = tags.split(',')
        query += f" AND tags @> ${idx}"
        params.append(tag_list)
        idx += 1

    query += f" ORDER BY event_time DESC LIMIT ${idx} OFFSET ${idx+1}"
    params.extend([limit, offset])

    async with db.pool.acquire() as conn:
        records = await conn.fetch(query, *params)
        
    data = [dict(r) for r in records]
    for d in data:
        # asyncpg returns dates and datetime as objects
        d["event_time"] = d["event_time"].isoformat() + "Z" if d["event_time"] else None
        d["event_date"] = d["event_date"].isoformat() if d["event_date"] else None
        d["ingested_at"] = d["ingested_at"].isoformat() + "Z" if d.get("ingested_at") else None
        # New Precision Metadata
        d["geo_confidence"] = float(d.get("geo_confidence") or 0.0)
        d["is_approximate"] = d.get("geo_precision", 3) >= 3
        d["ai_analysis"] = d.get("ai_analysis")
        if d.get("geom"): del d["geom"]

    response = {
        "status": 200,
        "success": True,
        "count": len(data),
        "data": data,
        "meta": {
            "from_cache": False,
            "page": (offset // limit) + 1,
            "per_page": limit
        }
    }

    await set_cache(cache_key, response, ttl=300) # 5 minutes TTL
    return response

@router.get("/recent")
async def get_recent_conflicts(request: Request, days: int = 7, limit: int = 100):
    cache_key = f"conflicts:recent:{days}:{limit}"
    cached = await check_cache(request, cache_key)
    if cached:
        cached["meta"]["from_cache"] = True
        return cached

    from_date = date.today() - timedelta(days=days)
    query = "SELECT * FROM conflict_events WHERE event_date >= $1 ORDER BY event_time DESC LIMIT $2"
    
    async with db.pool.acquire() as conn:
        records = await conn.fetch(query, from_date, limit)
        
    data = [dict(r) for r in records]
    for d in data:
        d["event_time"] = d["event_time"].isoformat() + "Z" if d["event_time"] else None
        d["event_date"] = d["event_date"].isoformat() if d["event_date"] else None
        d["ingested_at"] = d["ingested_at"].isoformat() + "Z" if d.get("ingested_at") else None
        d["geo_confidence"] = float(d.get("geo_confidence") or 0.0)
        d["is_approximate"] = d.get("geo_precision", 3) >= 3
        d["ai_analysis"] = d.get("ai_analysis")
        if d.get("geom"): del d["geom"]

    response = {
        "status": 200,
        "success": True,
        "count": len(data),
        "data": data,
        "meta": {"from_cache": False}
    }
    await set_cache(cache_key, response, ttl=300)
    return response
@router.get("/ongoing")
async def get_ongoing_conflicts(request: Request, limit: int = 50):
    """Returns only MILITARY/MILITANT events from the last 48 hours."""
    cache_key = f"conflicts:ongoing:{limit}"
    cached = await check_cache(request, cache_key)
    if cached: return cached

    query = """
    SELECT * FROM conflict_events 
    WHERE event_time >= NOW() - INTERVAL '7 days'
    AND category IN ('MILITARY', 'MILITANT', 'TERRORIST')
    ORDER BY event_time DESC LIMIT $1
    """
    async with db.pool.acquire() as conn:
        records = await conn.fetch(query, limit)
    
    data = [dict(r) for r in records]
    for d in data:
        d["event_time"] = d["event_time"].isoformat() + "Z" if d["event_time"] else None
        d["geo_confidence"] = float(d.get("geo_confidence") or 0.0)
        d["is_approximate"] = d.get("geo_precision", 3) >= 3
        if d.get("geom"): del d["geom"]
    
    res = {"status": 200, "success": True, "count": len(data), "data": data}
    await set_cache(cache_key, res, ttl=60) # Short TTL for live data
    return res

@router.get("/historical")
async def get_historical_conflicts(request: Request, days_ago: int = 2, limit: int = 100):
    """Returns military events older than the specified timeframe (default 2 days)."""
    cache_key = f"conflicts:historical:{days_ago}:{limit}"
    cached = await check_cache(request, cache_key)
    if cached: return cached

    query = """
    SELECT * FROM conflict_events 
    WHERE event_time < NOW() - INTERVAL '$1 days'
    AND category IN ('MILITARY', 'MILITANT', 'TERRORIST')
    ORDER BY event_time DESC LIMIT $2
    """
    # Note: Using parameterized interval is tricky in asyncpg, so we simplify
    query = query.replace("$1", str(days_ago))
    async with db.pool.acquire() as conn:
        records = await conn.fetch(query, limit)

    data = [dict(r) for r in records]
    for d in data:
        d["event_time"] = d["event_time"].isoformat() + "Z" if d["event_time"] else None
        d["geo_confidence"] = float(d.get("geo_confidence") or 0.0)
        d["is_approximate"] = d.get("geo_precision", 3) >= 3
        if d.get("geom"): del d["geom"]

    res = {"status": 200, "success": True, "count": len(data), "data": data}
    await set_cache(cache_key, res, ttl=3600) # Long TTL for history
    return res

@router.get("/near")
async def get_conflicts_near(
    request: Request,
    lat: float,
    lon: float,
    radius_km: int = 50,
    days: int = 7,
    limit: int = 100
):
    cache_key = f"conflicts:near:{lat}:{lon}:{radius_km}:{days}:{limit}"
    cached = await check_cache(request, cache_key)
    if cached:
        cached["meta"]["from_cache"] = True
        return cached

    from_date = date.today() - timedelta(days=days)
    query = """
    SELECT * FROM conflict_events 
    WHERE event_date >= $1 
    AND ST_DWithin(geom, ST_SetSRID(ST_MakePoint($2, $3), 4326)::geography, $4 * 1000)
    ORDER BY event_time DESC LIMIT $5
    """
    
    async with db.pool.acquire() as conn:
        records = await conn.fetch(query, from_date, lon, lat, radius_km, limit)
        
    data = [dict(r) for r in records]
    for d in data:
        d["event_time"] = d["event_time"].isoformat() + "Z" if d["event_time"] else None
        d["event_date"] = d["event_date"].isoformat() if d["event_date"] else None
        d["ingested_at"] = d["ingested_at"].isoformat() + "Z" if d.get("ingested_at") else None
        d["geo_confidence"] = float(d.get("geo_confidence") or 0.0)
        d["is_approximate"] = d.get("geo_precision", 3) >= 3
        if d.get("geom"): del d["geom"]

    response = {
        "status": 200,
        "success": True,
        "count": len(data),
        "data": data,
        "meta": {"from_cache": False}
    }
    await set_cache(cache_key, response, ttl=300)
    return response

@router.get("/country/{iso3}")
async def get_conflicts_country(request: Request, iso3: str, days: int = 30, limit: int = 100):
    cache_key = f"conflicts:country:{iso3}:{days}:{limit}"
    cached = await check_cache(request, cache_key)
    if cached:
        cached["meta"]["from_cache"] = True
        return cached

    from_date = date.today() - timedelta(days=days)
    query = "SELECT * FROM conflict_events WHERE country_iso3 = $1 AND event_date >= $2 ORDER BY event_time DESC LIMIT $3"
    
    async with db.pool.acquire() as conn:
        records = await conn.fetch(query, iso3.upper(), from_date, limit)
        
    data = [dict(r) for r in records]
    for d in data:
        d["event_time"] = d["event_time"].isoformat() + "Z" if d["event_time"] else None
        d["event_date"] = d["event_date"].isoformat() if d["event_date"] else None
        d["ingested_at"] = d["ingested_at"].isoformat() + "Z" if d.get("ingested_at") else None
        d["geo_confidence"] = float(d.get("geo_confidence") or 0.0)
        d["is_approximate"] = d.get("geo_precision", 3) >= 3
        if d.get("geom"): del d["geom"]

    response = {
        "status": 200,
        "success": True,
        "count": len(data),
        "data": data,
        "meta": {"from_cache": False}
    }
    await set_cache(cache_key, response, ttl=300)
    return response

@router.get("/{event_id}")
async def get_conflict_detail(event_id: str):
    query = "SELECT * FROM conflict_events WHERE event_id = $1"
    async with db.pool.acquire() as conn:
        record = await conn.fetchrow(query, event_id)
        
    if not record:
        raise HTTPException(status_code=404, detail="Event not found")
        
    d = dict(record)
    d["event_time"] = d["event_time"].isoformat() + "Z" if d["event_time"] else None
    d["event_date"] = d["event_date"].isoformat() if d["event_date"] else None
    d["ingested_at"] = d["ingested_at"].isoformat() + "Z" if d.get("ingested_at") else None
    d["geo_confidence"] = float(d.get("geo_confidence") or 0.0)
    d["is_approximate"] = d.get("geo_precision", 3) >= 3
    d["ai_analysis"] = d.get("ai_analysis")
    if d.get("geom"): del d["geom"]

    return {
        "status": 200,
        "success": True,
        "data": d,
        "meta": {"from_cache": False}
    }

@router.get("/clusters")
async def get_clusters(precision: float = Query(1.0, ge=0.1, le=5.0), days: int = 7):
    """
    Cluster events for map display using a grid-based approach.
    Precision 1.0 = ~111km grid. Precision 0.1 = ~11km grid.
    """
    from_date = date.today() - timedelta(days=days)
    query = """
    SELECT 
        ST_X(ST_Centroid(ST_Collect(geom::geometry))) as lon,
        ST_Y(ST_Centroid(ST_Collect(geom::geometry))) as lat,
        COUNT(*) as count,
        mode() WITHIN GROUP (ORDER BY category) as main_category,
        mode() WITHIN GROUP (ORDER BY severity) as main_severity
    FROM conflict_events
    WHERE event_date >= $1
    GROUP BY ST_SnapToGrid(geom::geometry, $2)
    """
    async with db.pool.acquire() as conn:
        records = await conn.fetch(query, from_date, precision)
        
    return {
        "status": 200,
        "count": len(records),
        "data": [dict(r) for r in records]
    }
