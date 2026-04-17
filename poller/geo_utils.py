import logging
import pycountry
from typing import Tuple, Optional, List
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
}

# Country Centroids
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
    "lebanon": (33.8547, 35.8623, "Lebanon", "LBN"),
    "iran": (32.4279, 53.688, "Iran", "IRN"),
}

_geolocator = None
_nlp = None

def get_geolocator():
    global _geolocator
    if not _geolocator:
        _geolocator = Nominatim(user_agent='conflictiq-v3-accuracy')
    return _geolocator

def get_nlp():
    global _nlp
    if not _nlp:
        # Use medium model for much better NER accuracy
        try:
            _nlp = spacy.load('en_core_web_md')
        except:
            _nlp = spacy.load('en_core_web_sm')
    return _nlp

def extract_location_entities(text: str) -> List[str]:
    nlp = get_nlp()
    doc = nlp(text)
    return [ent.text for ent in doc.ents if ent.label_ in ['GPE', 'LOC']]

def get_country_iso2(name: str) -> Optional[str]:
    try:
        results = pycountry.countries.search_fuzzy(name)
        if results:
            return results[0].alpha_2
    except:
        pass
    return None

def infer_coordinates(text: str, source_url: str = "") -> Tuple[float, float, str, str]:
    text_lower = text.lower()
    
    if "kyivindependent" in source_url.lower():
        return COUNTRY_CENTROIDS["ukraine"]

    for keyword, coords in HOTSPOTS.items():
        if keyword in text_lower:
            return coords

    for country, coords in COUNTRY_CENTROIDS.items():
        if country in text_lower:
            return coords

    return (0.0, 0.0, "Unknown", "UNK")

def geocode_nominatim_with_fallback(place: str, title_context: str = "") -> Tuple[Optional[float], Optional[float], str, str]:
    geolocator = get_geolocator()
    
    # 1. Extract context (countries) from the title
    all_entities = extract_location_entities(title_context)
    country_filters = []
    
    for ent in all_entities:
        iso2 = get_country_iso2(ent)
        if iso2:
            country_filters.append(iso2)
    
    # 2. Attempt Geocoding with Country Context
    search_query = place if place else title_context
    if not search_query:
        return (0.0, 0.0, "Unknown", "UNK")

    try:
        # Pass country_codes filter to Nominatim to disambiguate
        params = {"query": search_query, "addressdetails": True, "timeout": 15}
        if country_filters:
            params["country_codes"] = country_filters
            
        loc = geolocator.geocode(**params)
        
        if loc:
            addr = loc.raw.get('address', {})
            country = addr.get('country', "Unknown")
            iso = addr.get('ISO3166-1:alpha3', addr.get('country_code', "UNK")).upper()
            if len(iso) > 3: iso = iso[:3]
            return (loc.latitude, loc.longitude, country, iso)
    except Exception as e:
        log.warning(f"Accuracy Geocode failed: {e}")

    # 3. Fallback to Inference (Hotspots/Centroids)
    return infer_coordinates(search_query + " " + title_context)

def extract_location_ner(text: str):
    # Wrapper for backward compatibility
    entities = extract_location_entities(text)
    return entities[0] if entities else None
