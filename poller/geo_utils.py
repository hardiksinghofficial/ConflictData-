import logging
import pycountry
import asyncio
from typing import Tuple, Optional, List, Dict
from geopy.geocoders import Nominatim
import spacy

log = logging.getLogger(__name__)

# Predefined Hotspots for common conflict zones (High precision manual overrides)
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
}

_geolocator = None
_nlp = None
_geo_cache = {}

def get_geolocator():
    global _geolocator
    if not _geolocator:
        _geolocator = Nominatim(user_agent='conflictiq-tactical-v4')
    return _geolocator

def get_nlp():
    global _nlp
    if not _nlp:
        try:
            _nlp = spacy.load('en_core_web_md')
        except:
            _nlp = spacy.load('en_core_web_sm')
    return _nlp

def extract_location_entities(text: str) -> Dict[str, List[str]]:
    """
    Extracts locations and categorizes them by hierarchy.
    """
    nlp = get_nlp()
    doc = nlp(text)
    locs = {"GPE": [], "LOC": []}
    for ent in doc.ents:
        if ent.label_ in ['GPE', 'LOC']:
            locs[ent.label_].append(ent.text)
    return locs

def get_country_iso3(name: str) -> Optional[str]:
    try:
        # Check standard common names first
        name_map = {"gaza": "PSE", "west bank": "PSE", "taiwan": "TWN", "russia": "RUS", "usa": "USA"}
        if name.lower() in name_map:
            return name_map[name.lower()]
            
        c = pycountry.countries.search_fuzzy(name)
        if c: return c[0].alpha_3
    except: pass
    return None

async def geocode_nominatim_with_fallback(place: str, context_text: str = "") -> Tuple[Optional[float], Optional[float], str, str]:
    """
    Hierarchical geocoding with intelligent fallbacks.
    """
    geolocator = get_geolocator()
    search_query = place if place else context_text
    if not search_query:
        return (0.0, 0.0, "Unknown", "UNK")

    # 1. Hotspot check
    sq_lower = search_query.lower()
    for kw, coords in HOTSPOTS.items():
        if kw in sq_lower:
            return coords

    # 2. Cache check
    cache_key = f"{place}|{context_text}"
    if cache_key in _geo_cache:
        return _geo_cache[cache_key]

    # 3. Hierarchy extraction
    entities = extract_location_entities(context_text or search_query)
    
    # Try to build a specific query: "City, Country"
    final_query = search_query
    country_hint = None
    if entities["GPE"]:
        # If we have multiple GPEs, the last one is often the country
        country_hint = entities["GPE"][-1]
        if len(entities["GPE"]) > 1:
            final_query = f"{entities['GPE'][0]}, {country_hint}"

    await asyncio.sleep(1.0) # Modest throttling

    try:
        params = {"query": final_query, "addressdetails": True, "timeout": 10}
        
        # Add country filter if hint exists
        iso2 = None
        if country_hint:
            try:
                c = pycountry.countries.search_fuzzy(country_hint)
                if c: iso2 = c[0].alpha_2
            except: pass
        if iso2: params["country_codes"] = [iso2]

        loc = geolocator.geocode(**params)
        
        if loc:
            addr = loc.raw.get('address', {})
            country = addr.get('country', "Unknown")
            iso = addr.get('ISO3166-1:alpha3', "UNK").upper()
            
            # Map validation: ensure we didn't get a random street in a different country
            if iso2 and addr.get('country_code', '').upper() != iso2.upper():
                log.warning(f"Geocode mismatch: expected {iso2} but got {addr.get('country_code')}. Falling back.")
            else:
                res = (loc.latitude, loc.longitude, country, iso)
                _geo_cache[cache_key] = res
                return res
    except Exception as e:
        log.warning(f"Nominatim Error: {e}")

    # 4. Final Fallback to Country Centroid
    if country_hint:
        ch_lower = country_hint.lower()
        if ch_lower in COUNTRY_CENTROIDS:
            return COUNTRY_CENTROIDS[ch_lower]
        
        # Try generic country geocode
        try:
            loc = geolocator.geocode(country_hint)
            if loc:
                return (loc.latitude, loc.longitude, country_hint, "UNK")
        except: pass

    return (0.0, 0.0, "Unknown", "UNK")

def extract_location_ner(text: str):
    locs = extract_location_entities(text)
    all_locs = locs["GPE"] + locs["LOC"]
    return all_locs[0] if all_locs else None
