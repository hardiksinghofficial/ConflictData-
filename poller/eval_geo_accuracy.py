import asyncio
import logging
import json
import math
from typing import List, Dict
from poller.classifier import classify_event_llm
from poller.geo_utils import geocode_ranked

# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("GeoEval")

# --- TRUTH SET (Reference Data) ---
# Format: {"article_title": str, "article_summary": str, "gold_lat": float, "gold_lon": float, "gold_country": str}
TRUTH_SET = [
    {
        "title": "IDF strikes Hamas headquarters in Khan Yunis, Gaza Strip",
        "summary": "Military operation targeting command centers in southern Gaza.",
        "gold_lat": 31.3462, "gold_lon": 34.3022, "gold_country": "Palestine"
    },
    {
        "title": "Heavy shelling reported in Avdiivka as Russian forces advance",
        "summary": "Strategic town in Donetsk region under intense fire.",
        "gold_lat": 48.1366, "gold_lon": 37.7347, "gold_country": "Ukraine"
    },
    {
        "title": "Explosion at a market in Mogadishu kills 5",
        "summary": "Suspected Al-Shabaab attack in the Somali capital.",
        "gold_lat": 2.0469, "gold_lon": 45.3182, "gold_country": "Somalia"
    },
    {
        "title": "Sudanese Army clash with RSF in Omdurman",
        "summary": "Street fighting intensifies in the sister city of Khartoum.",
        "gold_lat": 15.6476, "gold_lon": 32.4807, "gold_country": "Sudan"
    }
]

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in KM between two points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

async def run_evaluation():
    log.info(f"Starting Geospatial Evaluation with {len(TRUTH_SET)} entries...")
    results = []
    
    for entry in TRUTH_SET:
        log.info(f"Evaluating: {entry['title']}")
        try:
            # 1. Pipeline: Extraction
            ai_res = await classify_event_llm(entry["title"], entry["summary"])
            
            # 2. Pipeline: Geocoding
            geo_res = await geocode_ranked(
                ai_res.get("location"),
                ai_res.get("country"),
                ai_res.get("location_admin1")
            )
            
            # 3. Metrics Calculation
            dist_err = haversine(entry["gold_lat"], entry["gold_lon"], geo_res["lat"], geo_res["lon"])
            country_match = entry["gold_country"].lower() == geo_res["country"].lower()
            
            results.append({
                "title": entry["title"],
                "dist_err_km": dist_err,
                "country_match": country_match,
                "precision": geo_res["precision"],
                "confidence": geo_res["confidence"]
            })
            
            # Rate limiting compliance
            await asyncio.sleep(2)
            
        except Exception as e:
            log.error(f"Failed entry {entry['title']}: {e}")

    # --- REPORTING ---
    if not results:
        log.error("No results to report.")
        return

    total = len(results)
    avg_dist = sum(r["dist_err_km"] for r in results) / total
    country_acc = sum(1 for r in results if r["country_match"]) / total
    exact_rate = sum(1 for r in results if r["dist_err_km"] <= 10) / total
    near_exact_rate = sum(1 for r in results if r["dist_err_km"] <= 25) / total

    print("\n" + "="*40)
    print(" CONFLICTIQ GEO-ACCURACY REPORT")
    print("="*40)
    print(f"Total Evaluated:   {total}")
    print(f"Avg Distance Err:  {avg_dist:.2f} km")
    print(f"Country Accuracy:  {country_acc*100:.1f}%")
    print(f"Exact Rate (10km): {exact_rate*100:.1f}%")
    print(f"Near-Exact (25km): {near_exact_rate*100:.1f}%")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_evaluation())
