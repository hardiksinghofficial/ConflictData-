import logging
import pycountry
import asyncio
import re
from typing import Tuple, Optional, List, Dict
from geopy.geocoders import Nominatim
from api.database import db
import json

log = logging.getLogger(__name__)

# Tactical Centroids for major conflict zones (High precision manual overrides)
# These bypass Nominatim entirely for reliable, instant geocoding of known hotspots.
HOTSPOTS = {
    # --- UKRAINE FRONTLINE ---
    "gaza": (31.3547, 34.3088, "Palestine", "PSE"),
    "gaza strip": (31.3547, 34.3088, "Palestine", "PSE"),
    "rafah": (31.2768, 34.2457, "Palestine", "PSE"),
    "khan younis": (31.3462, 34.3015, "Palestine", "PSE"),
    "khan yunis": (31.3462, 34.3015, "Palestine", "PSE"),
    "jabalia": (31.5281, 34.4831, "Palestine", "PSE"),
    "deir al-balah": (31.4180, 34.3509, "Palestine", "PSE"),
    "nuseirat": (31.4416, 34.3963, "Palestine", "PSE"),
    "west bank": (31.9522, 35.2332, "Palestine", "PSE"),
    "jenin": (32.4610, 35.3008, "Palestine", "PSE"),
    "tulkarm": (32.3104, 35.0286, "Palestine", "PSE"),
    # --- UKRAINE ---
    "donbas": (48.0, 37.8, "Ukraine", "UKR"),
    "donetsk": (48.0196, 37.8018, "Ukraine", "UKR"),
    "luhansk": (48.574, 39.307, "Ukraine", "UKR"),
    "kharkiv": (49.9935, 36.2304, "Ukraine", "UKR"),
    "avdiivka": (48.1366, 37.7347, "Ukraine", "UKR"),
    "bakhmut": (48.5954, 38.0003, "Ukraine", "UKR"),
    "zaporizhzhia": (47.8388, 35.1396, "Ukraine", "UKR"),
    "kherson": (46.6354, 32.6169, "Ukraine", "UKR"),
    "mariupol": (47.0958, 37.5494, "Ukraine", "UKR"),
    "pokrovsk": (48.2833, 37.1833, "Ukraine", "UKR"),
    "kursk": (51.7304, 36.1927, "Russia", "RUS"),
    "crimea": (45.3, 34.1, "Ukraine", "UKR"),
    "odesa": (46.4825, 30.7233, "Ukraine", "UKR"),
    "kyiv": (50.4501, 30.5234, "Ukraine", "UKR"),
    # --- RED SEA / YEMEN ---
    "red sea": (20.0, 38.0, "International Waters", "INT"),
    "hodeidah": (14.7980, 42.9540, "Yemen", "YEM"),
    "sanaa": (15.3694, 44.1910, "Yemen", "YEM"),
    "aden": (12.7855, 45.0187, "Yemen", "YEM"),
    # --- SUDAN ---
    "darfur": (13.0, 25.0, "Sudan", "SDN"),
    "khartoum": (15.5007, 32.5599, "Sudan", "SDN"),
    "el fasher": (13.6300, 25.3500, "Sudan", "SDN"),
    "port sudan": (19.6158, 37.2164, "Sudan", "SDN"),
    # --- HORN OF AFRICA ---
    "tigray": (13.5, 39.0, "Ethiopia", "ETH"),
    "mogadishu": (2.0469, 45.3182, "Somalia", "SOM"),
    # --- ASIA ---
    "kabul": (34.555, 69.207, "Afghanistan", "AFG"),
    "kandahar": (31.6133, 65.7101, "Afghanistan", "AFG"),
    "myanmar": (21.9162, 95.956, "Myanmar", "MMR"),
    # --- SAHEL ---
    "mali": (17.57, -3.99, "Mali", "MLI"),
    "burkina faso": (12.3714, -1.5197, "Burkina Faso", "BFA"),
    # --- MARITIME ---
    "hormuz": (26.5, 56.5, "International Waters", "INT"),
    "taiwan strait": (24.0, 119.0, "Taiwan", "TWN"),
    "south china sea": (12.0, 113.0, "International Waters", "INT"),
    # --- MIDDLE EAST ---
    "aleppo": (36.2021, 37.1343, "Syria", "SYR"),
    "idlib": (35.9306, 36.6339, "Syria", "SYR"),
    "beirut": (33.8938, 35.5018, "Lebanon", "LBN"),
    "baghdad": (33.3152, 44.3661, "Iraq", "IRQ"),
    "mosul": (36.3350, 43.1189, "Iraq", "IRQ"),
    # --- AFRICA ---
    "goma": (-1.6785, 29.2284, "DR Congo", "COD"),
    "beni": (0.4900, 29.4700, "DR Congo", "COD"),
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

def get_geolocator():
    global _geolocator
    if not _geolocator:
        _geolocator = Nominatim(user_agent='conflictiq-tactical-v4')
    return _geolocator

def normalize_location_text(text: str) -> str:
    if not text: return ""
    t = text.lower()
    # Remove noise patterns but preserve critical infrastructure identifiers
    t = re.sub(r'\b(near|outside|north of|south of|east of|west of|frontline near|region of|area of)\b', '', t)
    # Be careful not to remove 'base' or 'port' here
    t = re.sub(r'\b(city|province|district|oblast|state)\b', '', t)
    # Simplify whitespace
    return ' '.join(t.split()).strip()

async def get_cached_geo(key: str) -> Optional[Dict]:
    if db.redis:
        res = await db.redis.get(f"geo_v2:{key}")
        if res: return json.loads(res)
    return None

async def set_cached_geo(key: str, val: Dict):
    if db.redis:
        await db.redis.setex(f"geo_v2:{key}", 86400 * 14, json.dumps(val))

async def geocode_ranked(place: str, country: str, admin1: str = None) -> Dict:
    """
    Ranked Multi-Candidate Geocoding with Reverse Validation.
    Target: Exactly point error <= 10km for Precision 1.
    """
    clean_place = normalize_location_text(place)
    clean_country = normalize_location_text(country)
    
    # 1. Hotspot override check
    for kw, coords in HOTSPOTS.items():
        if re.search(fr'\b{kw}\b', clean_place) or re.search(fr'\b{kw}\b', clean_country):
            return {
                "lat": coords[0], "lon": coords[1], "country": coords[2], "iso3": coords[3],
                "precision": 1, "confidence": 0.95, "method": "hotspot_override", "provider": "static"
            }

    cache_key = f"{clean_place}|{clean_country}|{admin1 or ''}".strip()
    cached = await get_cached_geo(cache_key)
    if cached: return cached

    geolocator = get_geolocator()
    try:
        await asyncio.sleep(1.1)
        query = f"{clean_place}, {clean_country}" if clean_country else clean_place
        candidates = geolocator.geocode(query, addressdetails=True, exactly_one=False, limit=5, timeout=10)
        
        if not candidates:
            # Fallback to Admin or Country Centroid
            return await fallback_centroid(clean_country, admin1)

        scored_candidates = []
        for cand in candidates:
            addr = cand.raw.get('address', {})
            cand_country = addr.get('country', '').lower()
            cand_iso3 = addr.get('ISO3166-1:alpha3', 'UNK').upper()
            
            # SCORING MODEL
            score = 0.0
            # Country Match (45%)
            if clean_country in cand_country or cand_iso3 == get_country_iso3(clean_country):
                score += 0.45
            
            # Admin1 Match (20%)
            if admin1 and (admin1.lower() in str(addr).lower()):
                score += 0.20
            
            # PINPOINT LANDMARK BOOST (World Monitor Requirement)
            landmark_kws = ['base', 'airport', 'port', 'checkpoint', 'refinery', 'plant', 'depot', 'harbor', 'dam']
            if any(kw in clean_place for kw in landmark_kws) and any(kw in cand.address.lower() for kw in landmark_kws):
                score += 0.25 # High boost for strategic infrastructure
            
            # Name Similarity (Simple check - 15%)
            if clean_place in cand.address.lower():
                score += 0.15
                
            # Feature Type Preference (10%)
            if addr.get('city') or addr.get('town') or addr.get('village'):
                score += 0.10
            
            scored_candidates.append({
                "cand": cand,
                "score": score,
                "iso3": cand_iso3,
                "country": addr.get('country', 'Unknown'),
                "admin1": addr.get('state') or addr.get('region')
            })

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        top = scored_candidates[0]

        # REVERSE VALIDATION (for EXACT status)
        precision = 3
        confidence = top["score"]
        method = "ranked_nominatim"

        if top["score"] >= 0.80:
            # Mandatory reverse check for Precision 1
            await asyncio.sleep(1.1)
            rev = geolocator.reverse((top["cand"].latitude, top["cand"].longitude), addressdetails=True)
            if rev:
                rev_addr = rev.raw.get('address', {})
                rev_iso3 = rev_addr.get('ISO3166-1:alpha3', '').upper()
                if rev_iso3 == top["iso3"]:
                    precision = 1
                    confidence = min(0.99, confidence + 0.1)
                else:
                    precision = 2 # Mismatch, downgrade
        elif top["score"] >= 0.55:
            precision = 2
            
        result = {
            "lat": top["cand"].latitude, "lon": top["cand"].longitude,
            "country": top["country"], "iso3": top["iso3"], "admin1": top["admin1"],
            "precision": precision, "confidence": round(confidence, 3), 
            "method": method, "provider": "nominatim"
        }
        await set_cached_geo(cache_key, result)
        return result

    except Exception as e:
        log.warning(f"Geocoding error: {e}")
        return await fallback_centroid(clean_country, admin1)

async def fallback_centroid(country: str, admin1: str = None) -> Dict:
    centroid = COUNTRY_CENTROIDS.get(country.lower())
    if centroid:
        return {
            "lat": centroid[0], "lon": centroid[1], "country": centroid[2], "iso3": centroid[3],
            "precision": 3, "confidence": 0.4, "method": "country_centroid", "provider": "static"
        }
    return {
        "lat": 0.0, "lon": 0.0, "country": "International Waters", "iso3": "INT",
        "precision": 3, "confidence": 0.0, "method": "failed", "provider": "none"
    }

def get_country_iso3(name: str) -> Optional[str]:
    if not name: return None
    try:
        c = pycountry.countries.search_fuzzy(name)
        if c: return c[0].alpha_3
    except: pass
    return None
