import logging
from typing import Tuple, Optional
from geopy.geocoders import Nominatim

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

# Country Centroids (Fallback for when only country is known)
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

def get_geolocator():
    global _geolocator
    if not _geolocator:
        _geolocator = Nominatim(user_agent='conflictiq-v2-dev')
    return _geolocator

def infer_coordinates(text: str, source_url: str = "") -> Tuple[float, float, str, str]:
    """
    Tries multiple strategies to generate valid coordinates for an event title/text.
    Returns (lat, lon, country_name, country_iso3)
    """
    text_lower = text.lower()
    
    # Strategy 1: Source-based defaults
    if "kyivindependent" in source_url.lower():
        # Almost certainly Ukraine if nothing else matches
        default = COUNTRY_CENTROIDS["ukraine"]
    else:
        default = (0.0, 0.0, "Unknown", "UNK")

    # Strategy 2: Hotspot Keyword Matching
    for keyword, coords in HOTSPOTS.items():
        if keyword in text_lower:
            log.info(f"Matched Hotspot: {keyword}")
            return coords

    # Strategy 3: Country Centroid Matching
    for country, coords in COUNTRY_CENTROIDS.items():
        if country in text_lower:
            log.info(f"Matched Country Centroid: {country}")
            return coords

    # Strategy 4: Nominatim Geocoding (attempt from text directly)
    # This is handled by the caller (rss_poller/gdelt_poller) who calls geocode_nominatim
    # but we can return the default if all fails.
    
    return default

def geocode_nominatim_with_fallback(place: str, title_context: str = "") -> Tuple[Optional[float], Optional[float], str, str]:
    """
    Full geocoding flow: Nominatim -> Hotspots -> Country Centroids
    """
    if not place:
        return infer_coordinates(title_context)

    try:
        loc = get_geolocator().geocode(place, addressdetails=True, timeout=10)
        if loc:
            addr = loc.raw.get('address', {})
            country = addr.get('country', "Unknown")
            iso = addr.get('ISO3166-1:alpha3', addr.get('country_code', "UNK")).upper()
            if len(iso) > 3: iso = iso[:3]
            return (loc.latitude, loc.longitude, country, iso)
    except Exception as e:
        log.warning(f"Geocode failed for {place}: {e}")

    # If Nominatim fails or returns nothing, fall back to inference from the place name or title
    return infer_coordinates(place + " " + title_context)
