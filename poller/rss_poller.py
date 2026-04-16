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

nlp = None
geolocator = None

def get_nlp():
    global nlp
    if not nlp:
        try:
            log.info("Loading spacy model...")
            nlp = spacy.load('en_core_web_sm')
        except Exception as e:
            log.error(f"Spacy load failed: {e}")
            nlp = None
    return nlp

def get_geolocator():
    global geolocator
    if not geolocator:
        geolocator = Nominatim(user_agent='conflictiq-v2-dev')
    return geolocator

def extract_location_ner(text: str):
    nlp_model = get_nlp()
    if not nlp_model or not text:
        return None
    doc = nlp_model(text)
    places = [ent.text for ent in doc.ents if ent.label_ == 'GPE']
    return places[0] if places else None

def geocode_nominatim(place: str):
    if not place: return (None, None)
    try:
        loc = get_geolocator().geocode(place)
        if loc:
            return (loc.latitude, loc.longitude)
    except Exception as e:
        log.warning(f"Geocode failed for {place}: {e}")
    return (None, None)

def build_event(entry, lat, lon, source='RSS'):
    event_time = datetime.now(timezone.utc).replace(tzinfo=None)
    uniq = str(uuid.uuid5(uuid.NAMESPACE_URL, entry.get('link', ''))).split('-')[0]
    return {
        "event_id": f"CIQ-{event_time.strftime('%Y%m%d')}-RSS-{uniq}",
        "source": source,
        "source_reliability": "MEDIUM",
        "event_time": event_time,
        "event_date": event_time.date(),
        "country": "Unknown",  
        "country_iso3": "UNK", 
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
                lat, lon = (0.0, 0.0)
                
                if location:
                    geocoded_lat, geocoded_lon = geocode_nominatim(location)
                    if geocoded_lat is not None and geocoded_lon is not None:
                        lat, lon = geocoded_lat, geocoded_lon
                
                event = build_event(entry, lat, lon, source='RSS')
                await upsert_event(event)
                count += 1
        except Exception as e:
            log.error(f"Error parsing RSS {url}: {e}")

    log.info(f"Successfully processed {count} events from RSS.")
