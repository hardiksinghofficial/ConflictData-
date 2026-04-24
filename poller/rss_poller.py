import feedparser
import logging
import uuid
import asyncio
from datetime import datetime, timezone
from poller.db_inserter import upsert_event
from poller.geo_utils import geocode_ranked
from poller.classifier import classify_event_llm
from poller.deduplicator import is_duplicate_event

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
                     'missile','killed','fatalities','troops','offensive', 'war', 'army',
                     'bombing', 'explosion', 'drone', 'artillery', 'clashes', 'ambush',
                     'insurgent', 'militant', 'terrorist', 'combat', 'mortar']

async def poll_rss():
    log.info("Polling RSS Feeds with AI Intelligence...")
    count = 0
    skipped_noise = 0
    skipped_dupe = 0
    
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get('title','')
                summary = entry.get('summary', '')
                title_lower = title.lower()
                summary_lower = summary.lower()
                
                # Pre-filter: Only process likely conflict news
                if not any(kw in title_lower or kw in summary_lower for kw in CONFLICT_KEYWORDS):
                    continue
                
                # Token-saving deduplication
                if await is_duplicate_event(title):
                    skipped_dupe += 1
                    continue
                
                # AI-Powered Classification
                ai_res = await classify_event_llm(title, summary)
                
                # World Monitor Noise Gate
                if ai_res.get("is_noise"):
                    log.debug(f"RSS Skeptic Rejection: {title[:60]}... Reason: {ai_res.get('logic')}")
                    skipped_noise += 1
                    continue

                # High-Fidelity Geocoding
                geo_res = await geocode_ranked(
                    ai_res.get("location"), 
                    ai_res.get("country"),
                    ai_res.get("location_admin1")
                )
                
                # Drop failed geocodes — don't pollute the map
                if geo_res.get("confidence", 0) == 0.0 and geo_res.get("method") == "failed":
                    log.warning(f"RSS: Dropping event with failed geocode: {title[:60]}")
                    continue

                event_time = datetime.now(timezone.utc).replace(tzinfo=None)
                uniq = str(uuid.uuid5(uuid.NAMESPACE_URL, entry.get('link', ''))).split('-')[0]
                
                event = {
                    "event_id": f"CIQ-{event_time.strftime('%Y%m%d')}-RSS-{uniq}",
                    "source": "RSS",
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
                    "notes": ai_res.get("notes"),
                    "source_url": entry.get("link", ""),
                    "actor1": ai_res.get("actor1"),
                    "actor2": ai_res.get("actor2"),
                    "fatalities": ai_res.get("fatalities", 0),
                    "ai_analysis": ai_res.get("ai_analysis"),
                    "strategic_relevance": ai_res.get("strategic_relevance", "LOW"),
                }
                
                await upsert_event(event)
                count += 1
                
                # Rate limit compliance
                await asyncio.sleep(2.0)
                
        except Exception as e:
            log.error(f"Error parsing RSS {url}: {e}")
            await asyncio.sleep(5)

    log.info(f"RSS: Processed {count} events. Rejected {skipped_noise} noise, {skipped_dupe} duplicates.")
