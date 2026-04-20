from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from api.database import db
import csv
import io
from datetime import date
from typing import Optional, List
import json

router = APIRouter(prefix="/data", tags=["Conflict Data API"])

@router.get("/events")
async def get_raw_events(
    country: Optional[str] = Query(None, description="ISO3 Country Code"),
    actor: Optional[str] = Query(None, description="Involved Actor"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = 100,
    offset: int = 0
):
    """
    Returns filterable conflict event data in our standard JSON format.
    """
    query = "SELECT * FROM conflict_events WHERE 1=1"
    args = []
    
    if country:
        args.append(country.upper())
        query += f" AND country_iso3 = ${len(args)}"
    if actor:
        args.append(f"%{actor}%")
        query += f" AND (actor1 ILIKE ${len(args)} OR actor2 ILIKE ${len(args)})"
    if start_date:
        args.append(start_date)
        query += f" AND event_date >= ${len(args)}"
    if end_date:
        args.append(end_date)
        query += f" AND event_date <= ${len(args)}"
    
    query += " ORDER BY event_time DESC LIMIT " + str(limit) + " OFFSET " + str(offset)
    
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]

@router.get("/acled")
async def get_acled_style_data(
    country: Optional[str] = Query(None),
    limit: int = 100
):
    """
    Returns data mapped to the ACLED (Armed Conflict Location & Event Data) schema.
    """
    events = await get_raw_events(country=country, limit=limit)
    acled_data = []
    
    for ev in events:
        acled_record = {
            "event_id_cnty": ev["event_id"],
            "event_date": ev["event_time"].strftime("%Y-%m-%d") if ev["event_time"] else None,
            "year": ev["event_time"].year if ev["event_time"] else None,
            "event_type": ev["event_type"],
            "actor1": ev["actor1"],
            "actor2": ev["actor2"],
            "country": ev["country"],
            "location": ev["city"],
            "latitude": ev["lat"],
            "longitude": ev["lon"],
            "source": ev["source"],
            "notes": ev["notes"],
            "fatalities": ev["fatalities"],
            "severity": ev["severity_score"]
        }
        acled_data.append(acled_record)
        
    return acled_data

@router.get("/export/csv")
async def export_csv(country: Optional[str] = None):
    """
    Streams a CSV file containing all conflict records.
    """
    query = "SELECT * FROM conflict_events"
    args = []
    if country:
        query += " WHERE country_iso3 = $1"
        args.append(country.upper())
    query += " ORDER BY event_time DESC"

    async def generate():
        async with db.pool.acquire() as conn:
            # We use a cursor for potentially large datasets to avoid memory spikes
            async with conn.transaction():
                output = io.StringIO()
                writer = None
                
                async for row in conn.cursor(query, *args):
                    data = dict(row)
                    # Exclude geometry for CSV
                    data.pop('geom', None)
                    
                    if writer is None:
                        writer = csv.DictWriter(output, fieldnames=data.keys())
                        writer.writeheader()
                    
                    writer.writerow(data)
                    yield output.getvalue()
                    output.seek(0)
                    output.truncate(0)

    filename = f"conflictiq_data_{date.today()}.csv"
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/geojson")
async def get_geojson(limit: int = 500):
    """
    Returns conflict events in GeoJSON format for mapping integrations.
    """
    query = """
    SELECT json_build_object(
        'type', 'FeatureCollection',
        'features', json_agg(ST_AsGeoJSON(t.*)::json)
    )
    FROM (
        SELECT event_id, title, event_type, fatalities, geom 
        FROM conflict_events 
        ORDER BY event_time DESC 
        LIMIT $1
    ) as t
    """
    async with db.pool.acquire() as conn:
        res = await conn.fetchval(query, limit)
        return json.loads(res) if res else {"type": "FeatureCollection", "features": []}
