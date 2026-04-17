import httpx
import logging
from poller.db_inserter import upsert_event
from poller.rss_poller import extract_location_ner
from poller.geo_utils import geocode_nominatim_with_fallback
from datetime import datetime, timezone
import uuid

log = logging.getLogger(__name__)
GDELT_URL = 'https://api.gdeltproject.org/api/v2/doc/doc'

def passes_quality_filter(article):
    # Minimal filter to avoid junk
    return len(article.get('title', '')) > 10

async def poll_gdelt():
    # 1. Stagger startup to avoid simultaneous polling pressure
    await asyncio.sleep(10)
    
    params = {
        'query': 'conflict OR battle OR airstrike OR war sourcelang:English',
        'mode': 'artlist',
        'maxrecords': 100,
        'format': 'json',
    }
    
    data = None
    async with httpx.AsyncClient() as client:
        # 2. Retry Logic for 429 errors
        for attempt in range(3):
            try:
                r = await client.get(GDELT_URL, params=params, timeout=15.0)
                if r.status_code == 429:
                    wait = [15, 45][attempt] if attempt < 2 else 0
                    if wait:
                        log.warning(f"GDELT Rate Limited (429). Retrying in {wait}s...")
                        await asyncio.sleep(wait)
                        continue
                r.raise_for_status()
                data = r.json()
                break # Success
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
        location = extract_location_ner(title)
        
        # Defaults
        lat, lon, country, iso3 = (0.0, 0.0, "Unknown", "UNK")
        
        if location or title:
            lat_res, lon_res, country_res, iso3_res = await geocode_nominatim_with_fallback(location, title)
            if lat_res is not None:
                lat, lon, country, iso3 = lat_res, lon_res, country_res, iso3_res
        
        from poller.classifier import classify_event
        cat, sev, c_tags = classify_event(title)
        
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
            "event_type": "Violence",
            "severity": "MEDIUM",
            "severity_score": sev,
            "category": cat,
            "tags": c_tags,
            "title": title[:500],
            "source_url": article.get("url", ""),
            "fatalities": 0
        }
        
        await upsert_event(event)
        count += 1
        
    log.info(f"Successfully processed {count} events from GDELT.")
