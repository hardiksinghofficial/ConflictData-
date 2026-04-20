import httpx
import logging
import asyncio
import uuid
import re
from datetime import datetime, timezone
from poller.db_inserter import upsert_event
from poller.rss_poller import extract_location_ner
from poller.geo_utils import geocode_nominatim_with_fallback
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
             
        title = article.get("title", "")
        # GDELT titles can be messy, clean them up if needed
        title = title.replace("\n", " ").strip()
        
        location = extract_location_ner(title)
        
        # Defaults
        lat, lon, country, iso3 = (0.0, 0.0, "Unknown", "UNK")
        
        if location or title:
            lat_res, lon_res, country_res, iso3_res = await geocode_nominatim_with_fallback(location, title)
            if lat_res is not None:
                lat, lon, country, iso3 = lat_res, lon_res, country_res, iso3_res
        
        # --- NEW: AI-POWERED CLASSIFICATION ---
        ai_res = await classify_event_llm(title)
        
        uniq = str(uuid.uuid5(uuid.NAMESPACE_URL, article.get('url', ''))).split('-')[0]
        event_time = datetime.now(timezone.utc).replace(tzinfo=None)
        
        event = {
            "event_id": f"CIQ-{event_time.strftime('%Y%m%d')}-GLB-{uniq}",
            "source": "GDELT",
            "source_reliability": "MEDIUM",
            "event_time": event_time,
            "event_date": event_time.date(),
            "country": country,
            "country_iso3": iso3,
            "lat": lat,
            "lon": lon,
            "geo_precision": 2 if lat != 0 else 3,
            "event_type": ai_res["event_type"],
            "severity": "HIGH" if ai_res["severity_score"] > 7 else "MEDIUM" if ai_res["severity_score"] > 4 else "LOW",
            "severity_score": ai_res["severity_score"],
            "category": ai_res["category"],
            "tags": ai_res["tags"],
            "title": title[:500],
            "source_url": article.get("url", ""),
            "actor1": ai_res.get("actor1"),
            "actor2": ai_res.get("actor2"),
            "fatalities": ai_res.get("fatalities", 0),
            "notes": ai_res.get("notes"),
        }
        
        await upsert_event(event)
        count += 1
        
    log.info(f"Successfully processed {count} events from GDELT with AI Intelligence.")
