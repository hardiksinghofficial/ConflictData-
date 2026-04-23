import httpx
import logging
import asyncio
import uuid
import re
from datetime import datetime, timezone
from poller.db_inserter import upsert_event
from poller.geo_utils import geocode_ranked
from poller.classifier import classify_event_llm

log = logging.getLogger(__name__)
GDELT_URL = 'https://api.gdeltproject.org/api/v2/doc/doc'

# List of keywords that usually indicate non-tactical news or "noise"
NOISE_PATTERNS = [
    r"years ago", r"anniversary", r"memorial", r"remembers", r"history of", 
    r"how to watch", r"commemorate", r"museum", r"exhibition", r"biography"
]

def passes_quality_filter(article):
    title = article.get('title', '')
    if len(title) < 15:
        return False
    
    # Filter out historical retrospectives / noise
    title_lower = title.lower()
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, title_lower):
            log.debug(f"Filtering out noise: {title}")
            return False
            
    return True

async def poll_gdelt():
    # Stagger startup to avoid simultaneous polling pressure
    await asyncio.sleep(10)
    
    params = {
        'query': '(conflict OR battle OR airstrike OR war OR "armed clash" OR "suicide bombing") sourcelang:English',
        'mode': 'artlist',
        'maxrecords': 100,
        'format': 'json',
    }
    
    data = None
    async with httpx.AsyncClient() as client:
        for attempt in range(3):
            try:
                r = await client.get(GDELT_URL, params=params, timeout=20.0)
                if r.status_code == 429:
                    wait = [20, 60][attempt] if attempt < 2 else 0
                    if wait:
                        log.warning(f"GDELT Rate Limited (429). Retrying in {wait}s...")
                        await asyncio.sleep(wait)
                        continue
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:
                log.error(f"GDELT Poll Attempt {attempt+1} failed: {e}")
                if attempt < 2: await asyncio.sleep(10)
        
    if not data:
        log.error("Failed to fetch GDELT data after retries.")
        return
        
    articles = data.get('articles', [])
    log.info(f"GDELT returned {len(articles)} articles.")
    
    count = 0
    for article in articles:
        if not passes_quality_filter(article):
             continue
             
        title = article.get("title", "").replace("\n", " ").strip()
        
        # 1. AI-Powered Insight (Swapped to FIRST for better geography)
        try:
            ai_res = await classify_event_llm(title)
            
            # 2. High-Fidelity Geocoding using AI-extracted entities
            geo_res = await geocode_ranked(
                ai_res.get("location"), 
                ai_res.get("country"),
                ai_res.get("location_admin1")
            )
            
            uniq = str(uuid.uuid5(uuid.NAMESPACE_URL, article.get('url', ''))).split('-')[0]
            event_time = datetime.now(timezone.utc).replace(tzinfo=None)
            
            event = {
                "event_id": f"CIQ-{event_time.strftime('%Y%m%d')}-GLB-{uniq}",
                "source": "GDELT",
                "source_reliability": "MEDIUM",
                "event_time": event_time,
                "event_date": event_time.date(),
                "country": geo_res["country"],
                "country_iso3": geo_res["iso3"],
                "admin1": geo_res.get("admin1"),
                "lat": geo_res["lat"],
                "lon": geo_res["lon"],
                "geo_precision": geo_res["precision"],
                "geo_confidence": geo_res["confidence"],
                "geo_method": geo_res["method"],
                "geocode_provider": geo_res["provider"],
                "location_raw": ai_res.get("location_raw"),
                "event_type": ai_res.get("event_type", "Other"),
                "severity": "HIGH" if ai_res.get("severity_score", 0) > 7 else "MEDIUM" if ai_res.get("severity_score", 0) > 4 else "LOW",
                "severity_score": ai_res.get("severity_score", 3.0),
                "category": ai_res.get("category", "GENERAL"),
                "tags": ai_res.get("tags", []),
                "title": title[:500],
                "source_url": article.get("url", ""),
                "actor1": ai_res.get("actor1"),
                "actor2": ai_res.get("actor2"),
                "fatalities": ai_res.get("fatalities", 0),
                "notes": ai_res.get("notes"),
            }
            
            await upsert_event(event)
            count += 1
            
            # 3. Rate Limit Compliance (2s sleep)
            await asyncio.sleep(2.0)
            
        except Exception as e:
            log.error(f"Error processing GDELT article: {e}")
            await asyncio.sleep(5)
        
    log.info(f"Successfully processed {count} events from GDELT with AI Intelligence.")
