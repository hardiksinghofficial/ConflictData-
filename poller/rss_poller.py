import feedparser
import logging
import uuid
import asyncio
from datetime import datetime, timezone
from poller.db_inserter import upsert_event
from poller.geo_utils import geocode_ranked
from poller.classifier import classify_event_llm

log = logging.getLogger(__name__)

RSS_FEEDS = [
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.aljazeera.com/xml/rss/all.xml',
    'https://kyivindependent.com/feed',
    'https://www.crisisgroup.org/rss/crisiswatch.xml',
    'https://news.un.org/feed/subscribe/en/news/all/rss.xml',
    'https://www.hrw.org/rss/news',
]

CONFLICT_KEYWORDS = ['battle','strike','attack','shelling','airstrike',
                     'missile','killed','fatalities','troops','offensive', 'war', 'army']

def build_event(entry, geo_res, ai_res, source='RSS'):
    event_time = datetime.now(timezone.utc).replace(tzinfo=None)
    uniq = str(uuid.uuid5(uuid.NAMESPACE_URL, entry.get('link', ''))).split('-')[0]
    return {
        "event_id": f"CIQ-{event_time.strftime('%Y%m%d')}-RSS-{uniq}",
        "source": source,
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
        "severity": "HIGH" if ai_res["severity_score"] > 7 else "MEDIUM" if ai_res["severity_score"] > 4 else "LOW",
        "severity_score": ai_res.get("severity_score", 3.0),
        "category": ai_res.get("category", "GENERAL"),
        "tags": ai_res.get("tags", []),
        "title": entry.get("title", "")[:500],
        "notes": ai_res.get("notes") or entry.get("summary", "")[:1000],
        "source_url": entry.get("link", ""),
        "actor1": ai_res.get("actor1"),
        "actor2": ai_res.get("actor2"),
        "fatalities": ai_res.get("fatalities", 0)
    }

async def poll_rss():
    log.info("Polling RSS Feeds with AI Intelligence...")
    count = 0
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get('title','').lower()
                summary = entry.get('summary', '').lower()
                
                # Pre-filter to save LLM tokens (Only process likely conflict news)
                if not any(kw in title or kw in summary for kw in CONFLICT_KEYWORDS):
                    continue
                
                # 1. AI-Powered Insight (Swapped to FIRST so we get high-fidelity location)
                ai_res = await classify_event_llm(entry.get('title',''), entry.get('summary',''))
                
                # 2. High-Fidelity Geocoding using AI-extracted entities
                geo_res = await geocode_ranked(
                    ai_res.get("location"), 
                    ai_res.get("country"),
                    ai_res.get("location_admin1")
                )
                
                event = build_event(entry, geo_res, ai_res, source='RSS')
                await upsert_event(event)
                count += 1
                
                # 3. Throttling: respect Nominatim "1 req/sec" + AI rate limits
                await asyncio.sleep(2.0)
                
        except Exception as e:
            log.error(f"Error parsing RSS {url}: {e}")
            await asyncio.sleep(5) # Cooldown on failure

    log.info(f"Successfully processed {count} events from RSS with AI Intelligence.")
