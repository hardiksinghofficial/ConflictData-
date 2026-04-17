from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from api.ai_logic import ai_service
from api.intel_engine import get_world_hotspots
import logging

log = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI Military Analyst"])

@router.get("/analyze")
async def analyze_conflicts():
    """
    Streams a real-time situation report (SITREP) based on latest hotspot data.
    Uses SSE for token-by-token "thinking" effect.
    """
    try:
        # 1. Fetch live context
        hotspots = await get_world_hotspots()
        context = "Latest global conflict hotspots:\n"
        for h in hotspots:
            context += f"- {h['country_iso3']}: {h['event_count']} events detected near {h['lat']}, {h['lon']}\n"
        
        prompt = f"""
        CONTEXT DATA:
        {context}

        TASK:
        Provide a strategic situation report. Identify the top 2 highest risk areas. 
        Analyze the strategic implications for global stability. 
        Be concise, professional, and tactical.
        """
        
        # 2. Return SSE Stream
        async def event_generator():
            async for token in ai_service.stream_analysis(prompt):
                yield {"data": token}
        
        return EventSourceResponse(event_generator())
        
    except Exception as e:
        log.error(f"SITREP Failure: {e}")
        raise HTTPException(status_code=500, detail="Intelligence Link Offline")
