from fastapi import APIRouter, HTTPException
from api.intel_engine import (
    get_daily_sitrep, get_conflict_trends, get_world_hotspots, 
    get_priority_monitor, get_active_frontlines, get_actor_activity,
    get_strategic_forecast, get_strategic_theaters
)

router = APIRouter(prefix="/intel", tags=["Intelligence"])

@router.get("/theaters")
async def theaters():
    """Get active conflict theaters for the Situation Map (SITMAP)."""
    try:
        return await get_strategic_theaters()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sitrep")
async def sitrep():
    """Get a global Situation Report of the last 24 hours."""
    try:
        return await get_daily_sitrep()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast")
async def forecast():
    """Get an AI-derived strategic forecast and risk level."""
    try:
        return await get_strategic_forecast()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/actors")
async def actors():
    """Get tracking data for the most active conflict actors."""
    try:
        return await get_actor_activity()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends")
async def trends():
    """Identify countries with surging conflict levels."""
    try:
        return await get_conflict_trends()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hotspots")
async def hotspots():
    """Find the top 20 active conflict clusters globally."""
    try:
        return await get_world_hotspots()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitor")
async def monitor():
    """Get the 'Top Level' monitor of critical events (Airstrikes, Bombings, etc)."""
    try:
        return await get_priority_monitor()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/frontlines")
async def frontlines():
    """Get active frontline clusters (Ongoing high-intensity conflict zones)."""
    try:
        return await get_active_frontlines()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
