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
    # Prefer GPE (Geopolitical Entities), fallback to LOC (Non-GPE locations)
    places = [ent.text for ent in doc.ents if ent.label_ in ['GPE', 'LOC']]
    return places[0] if places else None

def geocode_nominatim(place: str):
    if not place: return (None, None, "Unknown", "UNK")
    try:
        loc = get_geolocator().geocode(place, addressdetails=True)
        if loc:
            addr = loc.raw.get('address', {})
            country = addr.get('country', "Unknown")
            iso = addr.get('ISO3166-1:alpha3', addr.get('country_code', "UNK")).upper()
            if len(iso) > 3: iso = iso[:3]
            return (loc.latitude, loc.longitude, country, iso)
    except Exception as e:
        log.warning(f"Geocode failed for {place}: {e}")
    return (None, None, "Unknown", "UNK")

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
                
                if location:
                    log.info(f"Attempting to geocode location: {location}")
                    g_res = geocode_nominatim(location)
                    if g_res[0] is not None:
                        lat, lon, country, iso3 = g_res
                        log.info(f"Geocoded {location} to {lat}, {lon}")
                    else:
                        log.warning(f"Could not geocode extracted location: {location}")
                
                event = build_event(entry, lat, lon, country, iso3, source='RSS')
                await upsert_event(event)
                count += 1
        except Exception as e:
            log.error(f"Error parsing RSS {url}: {e}")

    log.info(f"Successfully processed {count} events from RSS.")
