import feedparser
import logging
import uuid
from datetime import datetime, timezone
from poller.db_inserter import upsert_event
from poller.geo_utils import geocode_nominatim_with_fallback, extract_location_ner
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

def build_event(entry, lat, lon, country, iso3, ai_res, source='RSS'):
    event_time = datetime.now(timezone.utc).replace(tzinfo=None)
    uniq = str(uuid.uuid5(uuid.NAMESPACE_URL, entry.get('link', ''))).split('-')[0]
    return {
        "event_id": f"CIQ-{event_time.strftime('%Y%m%d')}-RSS-{uniq}",
        "source": source,
        "source_reliability": "MEDIUM",
        "event_time": event_time,
        "event_date": event_time.date(),
        "country": country,  
        "country_iso3": iso3, 
        "lat": lat,           
        "lon": lon,           
        "geo_precision": 3,
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
                # This significantly reduces 'Unknown' results
                lat, lon, country, iso3 = await geocode_nominatim_with_fallback(
                    ai_res.get("location"), 
                    ai_res.get("country")
                )
                
                event = build_event(entry, lat, lon, country, iso3, ai_res, source='RSS')
                await upsert_event(event)
                count += 1
                
                # 3. Throttling: respect Nominatim "1 req/sec" + AI rate limits
                await asyncio.sleep(2.0)
                
        except Exception as e:
            log.error(f"Error parsing RSS {url}: {e}")
            await asyncio.sleep(5) # Cooldown on failure

    log.info(f"Successfully processed {count} events from RSS with AI Intelligence.")
