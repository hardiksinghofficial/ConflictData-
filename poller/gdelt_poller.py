import httpx
import logging
from poller.db_inserter import upsert_event
from datetime import datetime, timezone
import uuid

log = logging.getLogger(__name__)
GDELT_URL = 'https://api.gdeltproject.org/api/v2/events/query'

def passes_quality_filter(article):
    return True

async def poll_gdelt():
    params = {
        'query': 'conflict OR battle OR airstrike OR war sourcelang:English',
        'mode': 'artlist',
        'maxrecords': 100,
        'format': 'json',
    }
    
    async with httpx.AsyncClient() as client:
        r = await client.get(GDELT_URL, params=params, timeout=15.0)
        r.raise_for_status()
        data = r.json()
        
    articles = data.get('articles', [])
    log.info(f"GDELT returned {len(articles)} articles.")
    
    count = 0
    for article in articles:
        if not passes_quality_filter(article):
             continue
             
        uniq = str(uuid.uuid5(uuid.NAMESPACE_URL, article.get('url', ''))).split('-')[0]
        event_time = datetime.now(timezone.utc).replace(tzinfo=None)
        
        event = {
            "event_id": f"CIQ-{event_time.strftime('%Y%m%d')}-GLB-{uniq}",
            "source": "GDELT",
            "source_reliability": "MEDIUM",
            "event_time": event_time,
            "event_date": event_time.date(),
            "country": "Ukraine",  
            "country_iso3": "UKR", 
            "lat": 48.5,           
            "lon": 38.0,           
            "geo_precision": 2,
            "event_type": "Battles",
            "severity": "MEDIUM",
            "severity_score": 6.5,
            "title": article.get("title", "")[:500],
            "source_url": article.get("url", ""),
            "fatalities": 0
        }
        
        await upsert_event(event)
        count += 1
        
    log.info(f"Successfully processed {count} events from GDELT.")
