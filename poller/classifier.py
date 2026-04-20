import logging
import re
import os
import json
from typing import Dict, Any, Tuple, List, Optional
from groq import AsyncGroq, RateLimitError

log = logging.getLogger(__name__)

# Category definitions and their priority keywords (Fallback Logic)
CATEGORIES = {
    "TERRORIST": {
        "keywords": [
            r"\bterror(ist|ism|s)?\b", r"\bbomb(ing|ed)?\b", r"\bblast\b", 
            r"\bsuicide\b", r"\bmassacre\b", r"\bied\b", r"\bjihad(ist)?\b",
            r"\bisis\b", r"\bhamas\b", r"\bhezbollah\b", r"\bshabaab\b",
            r"\bextremists?\b", r"\bhostage\b"
        ],
        "base_severity": 8.5
    },
    "MILITARY": {
        "keywords": [
            r"\bar(my|mies)\b", r"\btroops?\b", r"\bmilitary\b", r"\bair\s?strike\b",
            r"\bmissile\b", r"\bshelling\b", r"\boffensive\b", r"\bcmdrs?\b",
            r"\bcommander\b", r"\bforces?\b", r"\battalion\b", r"\binvasion\b",
            r"\bartiller(y|ies)\b", r"\btanks?\b", r"\bconvoy\b"
        ],
        "base_severity": 7.0
    },
    "MILITANT": {
        "keywords": [
            r"\bmilitants?\b", r"\brebels?\b", r"\binsurgent(s)?\b", r"\bguerrilla\b",
            r"\bparamilitary\b", r"\barmed\s?group\b", r"\bseparatists?\b",
            r"\bfighters?\b", r"\bclash(es)?\b", r"\busher\b"
        ],
        "base_severity": 6.0
    }
}

EVENT_TYPES_MAP = {
    "Airstrike / Artillery": [r"\bair\s?strike\b", r"\bshelling\b", r"\bmissile\b", r"\bbombing\b", r"\bartiller(y|ies)\b"],
    "Terrorist Attack": [r"\bsuicide\b", r"\bterror(ist|ism)\b", r"\bblast\b", r"\bied\b", r"\bmassacre\b"],
    "Armed Clash": [r"\bclash(es)?\b", r"\battle\b", r"\bfights?\b", r"\bclash\b", r"\boffensive\b", r"\binvasion\b"],
    "Arrests / Detainment": [r"\barrests?\b", r"\bdetain(ed|s)?\b", r"\bcustody\b"],
    "Strategic Report": [r"\breport\b", r"\banalysis\b", r"\bupdate\b", r"\bsitrep\b"]
}

# AI Classifier Setup
_groq_client = None
def get_groq_client():
    global _groq_client
    if not _groq_client:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            _groq_client = AsyncGroq(api_key=api_key)
    return _groq_client

async def classify_event_llm(title: str, summary: str = "") -> Dict[str, Any]:
    """
    Advanced LLM-based classification for high-precision intelligence.
    Returns a dictionary with structured event data.
    """
    client = get_groq_client()
    if not client:
        # Fallback to regex if no AI key
        cat, sev, tags, etype = classify_event(title, summary)
        return {
            "category": cat,
            "severity_score": sev,
            "tags": tags,
            "event_type": etype,
            "actor1": None,
            "actor2": None,
            "fatalities": 0,
            "notes": "Classification: Regex (Fallback)"
        }

    prompt = f"""
    Analyze this news event for a conflict intelligence database:
    Title: {title}
    Summary: {summary}

    Return a JSON object with:
    - category: (MILITARY, TERRORIST, MILITANT, CIVIL_UNREST, or GENERAL)
    - event_type: (Armed Clash, Airstrike / Artillery, Terrorist Attack, Arrests / Detainment, Strategic Report, or Other)
    - actor1: The primary group or entity (e.g. 'IDF', 'Wagner Group', 'Protestors')
    - actor2: The secondary entity or target
    - weapon: Keywords for weapons used (e.g. 'F-16', 'Drone', 'Rocket')
    - fatalities: Estimated count if mentioned, else 0
    - severity_score: 0 to 10 based on tactical impact
    - summary_short: 1 sentence tactical summary
    """

    try:
        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional conflict intelligence analyst. Output ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        res = json.loads(completion.choices[0].message.content)
        return {
            "category": res.get("category", "GENERAL").upper(),
            "severity_score": float(res.get("severity_score", 3.0)),
            "tags": list(set([res.get("actor1"), res.get("weapon")] + (res.get("weapon_list", []) if isinstance(res.get("weapon_list"), list) else []))),
            "event_type": res.get("event_type", "Other"),
            "actor1": res.get("actor1"),
            "actor2": res.get("actor2"),
            "fatalities": int(res.get("fatalities", 0)),
            "notes": res.get("summary_short", ""),
            "ai_classified": True
        }
    except Exception as e:
        log.error(f"LLM Classification failed: {e}")
        cat, sev, tags, etype = classify_event(title, summary)
        return {
            "category": cat,
            "severity_score": sev,
            "tags": tags,
            "event_type": etype,
            "actor1": None,
            "actor2": None,
            "fatalities": 0,
            "notes": f"Fallback: {str(e)}",
            "ai_classified": False
        }

def classify_event(title: str, summary: str = "") -> tuple:
    """
    Regex fallback classification.
    """
    combined_text = (title + " " + summary).lower()
    
    found_category = "GENERAL"
    max_severity = 3.0
    tags = []
    found_event_type = "Violence"

    for etype, patterns in EVENT_TYPES_MAP.items():
        if any(re.search(p, combined_text) for p in patterns):
            found_event_type = etype
            break

    for cat_name, config in CATEGORIES.items():
        matched_keywords = []
        for pattern in config["keywords"]:
            if re.search(pattern, combined_text):
                matched_keywords.append(pattern.replace(r"\b", "").replace("?", ""))
        
        if matched_keywords:
            found_category = cat_name
            max_severity = config["base_severity"]
            tags.extend(matched_keywords[:3])
            break 

    return found_category, max_severity, list(set(tags)), found_event_type
