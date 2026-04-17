import feedparser
import spacy
from geopy.geocoders import Nominatim
from poller.db_inserter import upsert_event
import logging
from datetime import datetime, timezone
import uuid

log = logging.getLogger(__name__)

RSS_FEEDS = [
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.aljazeera.com/xml/rss/all.xml',
    'https://kyivindependent.com/feed',
]

CONFLICT_KEYWORDS = ['battle','strike','attack','shelling','airstrike',
                     'missile','killed','fatalities','troops','offensive', 'war', 'army']

from poller.geo_utils import geocode_nominatim_with_fallback, extract_location_ner, get_nlp

def geocode_nominatim(place: str):
    return geocode_nominatim_with_fallback(place)

def build_event(entry, lat, lon, country, iso3, source='RSS'):
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
        "event_type": "Violence",
        "severity": "LOW",
        "severity_score": 3.0,
        "title": entry.get("title", "")[:500],
        "notes": entry.get("summary", "")[:1000],
        "source_url": entry.get("link", "")
    }

async def poll_rss():
    log.info("Polling RSS Feeds...")
    count = 0
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get('title','').lower()
                summary = entry.get('summary', '').lower()
                
                if not any(kw in title or kw in summary for kw in CONFLICT_KEYWORDS):
                    continue
                
                text_to_examine = title + ". " + summary
                location = extract_location_ner(text_to_examine)
                
                # Default to center of world/unknown
                lat, lon, country, iso3 = (0.0, 0.0, "Unknown", "UNK")
                
                if location or title:
                    log.info(f"Attempting to geocode with context: {location or 'None'} | Title: {title}")
                    # Use the improved geocoder with fallback logic
                    lat_res, lon_res, country_res, iso3_res = geocode_nominatim_with_fallback(location, title)
                    if lat_res is not None:
                        lat, lon, country, iso3 = lat_res, lon_res, country_res, iso3_res
                        log.info(f"Geocoded successfully to {lat}, {lon}")
                    else:
                        log.warning(f"Could not geocode even with inference: {title}")
                
                from poller.classifier import classify_event
                cat, sev, c_tags = classify_event(title, summary)
                
                event = build_event(entry, lat, lon, country, iso3, source='RSS')
                event['category'] = cat
                event['severity_score'] = sev
                # Add classification tags to existing tags
                if 'tags' not in event or not event['tags']:
                    event['tags'] = c_tags
                else:
                    event['tags'] = list(set(event['tags'] + c_tags))
                
                await upsert_event(event)
                count += 1
        except Exception as e:
            log.error(f"Error parsing RSS {url}: {e}")

    log.info(f"Successfully processed {count} events from RSS.")
