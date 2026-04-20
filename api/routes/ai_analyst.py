from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from api.ai_logic import ai_service
from api.intel_engine import get_world_hotspots
import logging
from typing import Optional

log = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI Military Analyst"])

@router.get("/analyze")
async def analyze_conflicts(context: Optional[str] = Query(None)):
    """
    Streams a situation report (SITREP).
    If 'context' is provided, performs a deep-dive analysis on that specific theater.
    """
    try:
        if context:
            # Deep Sector Analysis
            prompt = f"""
            TARGET SECTOR DATA:
            {context}

            TASK:
            Provide a deep tactical analysis of this specific sector. 
            Analyze the current engagement, identify likely tactical objectives of the actors involved, 
            and forecast immediate escalation risks.
            """
        else:
            # Global Situation Report
            hotspots = await get_world_hotspots()
            hotspot_text = "Latest global conflict hotspots:\n"
            for h in hotspots:
                hotspot_text += f"- {h['country_iso3']}: {h['event_count']} events detected near {h['lat']}, {h['lon']}\n"
            
            prompt = f"""
            GLOBAL CONTEXT:
            {hotspot_text}

            TASK:
            Provide a high-level strategic situation report. Identify the top 3 highest risk theaters. 
            Analyze the strategic implications for global stability.
            """
        
        async def event_generator():
            async for token in ai_service.stream_analysis(prompt):
                yield {"data": token}
        
        return EventSourceResponse(event_generator())
        
    except Exception as e:
        log.error(f"SITREP Failure: {e}")
        # Return a stream that explains the failure to the user
        async def error_generator():
            yield {"data": f"\n\n[COMMUNICATION LINK ERROR: {str(e)}]"}
        return EventSourceResponse(error_generator())
