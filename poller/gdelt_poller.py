import httpx
import logging
import asyncio
import uuid
import re
from datetime import datetime, timezone
from poller.db_inserter import upsert_event
from poller.geo_utils import geocode_ranked
from poller.classifier import classify_event_llm
from poller.deduplicator import is_duplicate_event

log = logging.getLogger(__name__)
GDELT_URL = 'https://api.gdeltproject.org/api/v2/doc/doc'

# Expanded noise patterns — historical, editorial, and non-kinetic content
NOISE_PATTERNS = [
    r"years ago", r"anniversary", r"memorial", r"remembers", r"history of", 
    r"how to watch", r"commemorate", r"museum", r"exhibition", r"biography",
    r"book review", r"opinion:", r"editorial:", r"analysis:", r"podcast",
    r"interview with", r"what you need to know", r"explained:", r"timeline of",
    r"trade war", r"war on drugs", r"war on poverty", r"culture war",
    r"star wars", r"price war", r"bidding war", r"turf war",
    r"fantasy football", r"world cup", r"olympic", r"nba ", r"nfl ",
    r"box office", r"movie", r"tv show", r"streaming", r"netflix",
    r"stock market", r"wall street", r"cryptocurrency", r"bitcoin",
    r"election results", r"campaign trail", r"poll shows", r"voter",
]

def passes_quality_filter(article):
    title = article.get('title', '')
    if len(title) < 20:
        return False
    
    title_lower = title.lower()
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, title_lower):
            log.debug(f"GDELT noise filter: {title[:60]}")
            return False
            
    return True

async def poll_gdelt():
    await asyncio.sleep(10)
    
    # Precision query — only actual kinetic/military terms, not broad "war" or "conflict"
    params = {
        'query': '(airstrike OR "armed clash" OR shelling OR artillery OR "drone strike" OR missile OR bombing OR "suicide attack" OR ambush OR mortar OR "killed in" OR "troops deployed" OR "military operation") sourcelang:English',
        'mode': 'artlist',
        'maxrecords': 75,
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
    skipped_noise = 0
    skipped_dupe = 0
    skipped_geo = 0
    
    for article in articles:
        if not passes_quality_filter(article):
             continue
             
        title = article.get("title", "").replace("\n", " ").strip()
        
        # Token-saving deduplication
        if await is_duplicate_event(title):
            skipped_dupe += 1
            continue

        try:
            ai_res = await classify_event_llm(title)
            
            # World Monitor Noise Gate
            if ai_res.get("is_noise"):
                log.debug(f"GDELT Skeptic Rejection: {title[:60]}... Reason: {ai_res.get('logic')}")
                skipped_noise += 1
                continue

            # High-Fidelity Geocoding
            geo_res = await geocode_ranked(
                ai_res.get("location"), 
                ai_res.get("country"),
                ai_res.get("location_admin1")
            )
            
            # Drop failed geocodes — don't pollute the map with (0,0)
            if geo_res.get("confidence", 0) == 0.0 and geo_res.get("method") == "failed":
                log.warning(f"GDELT: Dropping event with failed geocode: {title[:60]}")
                skipped_geo += 1
                continue
            
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
                "ai_analysis": ai_res.get("ai_analysis"),
                "strategic_relevance": ai_res.get("strategic_relevance", "LOW"),
            }
            
            await upsert_event(event)
            count += 1
            
            await asyncio.sleep(2.0)
            
        except Exception as e:
            log.error(f"Error processing GDELT article: {e}")
            await asyncio.sleep(5)
        
    log.info(f"GDELT: Processed {count} events. Rejected {skipped_noise} noise, {skipped_dupe} dupes, {skipped_geo} bad geo.")
