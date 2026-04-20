import logging
import pycountry
import asyncio
from typing import Tuple, Optional, List, Dict
from geopy.geocoders import Nominatim
import spacy
from api.database import db
import json

log = logging.getLogger(__name__)

# Tactical Centroids for major conflict zones (High precision manual overrides)
HOTSPOTS = {
    "gaza": (31.3547, 34.3088, "Palestine", "PSE"),
    "west bank": (31.9522, 35.2332, "Palestine", "PSE"),
    "donbas": (48.0, 37.8, "Ukraine", "UKR"),
    "donetsk": (48.0196, 37.8018, "Ukraine", "UKR"),
    "luhansk": (48.574, 39.307, "Ukraine", "UKR"),
    "kharkiv": (49.9935, 36.2304, "Ukraine", "UKR"),
    "avdiivka": (48.1366, 37.7347, "Ukraine", "UKR"),
    "red sea": (20.0, 38.0, "International Waters", "INT"),
    "taiwan strait": (24.0, 119.0, "Taiwan", "TWN"),
    "south china sea": (12.0, 113.0, "International Waters", "INT"),
    "darfur": (13.0, 25.0, "Sudan", "SDN"),
    "khartoum": (15.5007, 32.5599, "Sudan", "SDN"),
    "tigray": (13.5, 39.0, "Ethiopia", "ETH"),
    "kabul": (34.555, 69.207, "Afghanistan", "AFG"),
    "mali": (17.57, -3.99, "Mali", "MLI"),
    "hormuz": (26.5, 56.5, "International Waters", "INT"),
}

COUNTRY_CENTROIDS = {
    "ukraine": (48.3794, 31.1656, "Ukraine", "UKR"),
    "russia": (61.524, 105.3188, "Russia", "RUS"),
    "israel": (31.0461, 34.8516, "Israel", "ISR"),
    "palestine": (31.9522, 35.2332, "Palestine", "PSE"),
    "sudan": (12.8628, 30.2176, "Sudan", "SDN"),
    "myanmar": (21.9162, 95.956, "Myanmar", "MMR"),
    "yemen": (15.5527, 48.5164, "Yemen", "YEM"),
    "ethiopia": (9.145, 40.4897, "Ethiopia", "ETH"),
    "syria": (34.8021, 38.9968, "Syria", "SYR"),
    "iraq": (33.2232, 43.6793, "Iraq", "IRQ"),
    "iran": (32.4279, 53.6880, "Iran", "IRN"),
    "pakistan": (30.3753, 69.3451, "Pakistan", "PAK"),
    "afghanistan": (33.9391, 67.7100, "Afghanistan", "AFG"),
    "lebanon": (33.8547, 35.8623, "Lebanon", "LBN"),
    "somalia": (5.1521, 46.1996, "Somalia", "SOM"),
    "drc": (-4.0383, 21.7587, "DR Congo", "COD"),
    "mali": (17.5707, -3.9962, "Mali", "MLI"),
    "nigeria": (9.0820, 8.6753, "Nigeria", "NGA"),
    "libya": (26.3351, 17.2283, "Libya", "LBY"),
    "taiwan": (23.6978, 120.9605, "Taiwan", "TWN"),
}

_geolocator = None
_nlp = None

def get_geolocator():
    global _geolocator
    if not _geolocator:
        _geolocator = Nominatim(user_agent='conflictiq-tactical-v4')
    return _geolocator

async def get_cached_geo(key: str) -> Optional[Tuple]:
    if db.redis:
        res = await db.redis.get(f"geo:{key}")
        if res: return tuple(json.loads(res))
    return None

async def set_cached_geo(key: str, val: Tuple):
    if db.redis:
        await db.redis.setex(f"geo:{key}", 86400 * 7, json.dumps(val)) # 1 week cache

async def geocode_nominatim_with_fallback(place: str, country_name: str = "") -> Tuple[float, float, str, str]:
    """
    High-Fidelity geocoding with Redis caching and guaranteed country fallbacks.
    """
    # 1. Hotspot check
    sq_lower = (place or country_name).lower()
    for kw, coords in HOTSPOTS.items():
        if kw in sq_lower: return coords

    # 2. Redis Cache check
    cache_key = f"{place}|{country_name}".lower().strip()
    cached = await get_cached_geo(cache_key)
    if cached: return cached

    # 3. Country-only check (If we only have country, use centroid immediately)
    if not place or place.lower() == country_name.lower():
        centroid = COUNTRY_CENTROIDS.get(country_name.lower())
        if centroid: return centroid

    # 4. Deep Geocoding via Nominatim
    geolocator = get_geolocator()
    try:
        # Respect Nominatim rate limits (1 req/sec)
        await asyncio.sleep(1.2)
        
        query = f"{place}, {country_name}" if country_name else place
        loc = geolocator.geocode(query, addressdetails=True, timeout=10)
        
        if loc:
            addr = loc.raw.get('address', {})
            country = addr.get('country', country_name or "Unknown")
            iso = addr.get('ISO3166-1:alpha3', "UNK").upper()
            res = (loc.latitude, loc.longitude, country, iso)
            await set_cached_geo(cache_key, res)
            return res
    except Exception as e:
        log.warning(f"Nominatim 429 or Error: {e}. Switching to tactical fallbacks.")

    # 5. Zero-Unknown Fallback Policy
    if country_name:
        country_lower = country_name.lower()
        # Check predefined centroids
        if country_lower in COUNTRY_CENTROIDS:
            return COUNTRY_CENTROIDS[country_lower]
        
        # Last ditch: try to geocode just the country name (and cache it)
        try:
            loc = geolocator.geocode(country_name)
            if loc:
                res = (loc.latitude, loc.longitude, country_name, "UNK")
                await set_cached_geo(country_name.lower(), res)
                return res
        except: pass

    # If absolutely everything fails, return Global Centroid but NEVER 'Unknown'
    return (0.0, 0.0, "International Waters", "INT")

def extract_location_entities(text: str) -> Dict:
    # Legacy NER - kept for compatibility but superseded by AI extraction
    return {"GPE": [], "LOC": []}

def get_country_iso3(name: str) -> Optional[str]:
    try:
        c = pycountry.countries.search_fuzzy(name)
        if c: return c[0].alpha_3
    except: pass
    return None
