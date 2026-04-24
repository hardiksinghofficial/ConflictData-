import logging
import re
import os
import json
import asyncio
from typing import Dict, Any, Tuple, List, Optional
from groq import AsyncGroq
import google.generativeai as genai
from huggingface_hub import AsyncInferenceClient

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
            r"\bartiller(y|ies)\b", r"\btanks?\b", r"\bconvoy\b", r"\bstrikes?\b",
            r"\battacks?\b", r"\bkill(ed|s)?\b"
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

# --- MULTI-ENGINE CLIENT SETUP ---
_groq_keys = [k.strip() for k in os.getenv("GROQ_API_KEYS", os.getenv("GROQ_API_KEY", "")).split(",") if k.strip()]
_groq_clients = [AsyncGroq(api_key=k) for k in _groq_keys]
_current_groq_index = 0

_hf_client = None
_gemini_configured = False

def get_groq_client():
    global _current_groq_index
    if not _groq_clients:
        return None
    client = _groq_clients[_current_groq_index]
    # Rotate for next call
    _current_groq_index = (_current_groq_index + 1) % len(_groq_clients)
    return client

def get_hf_client():
    global _hf_client
    if not _hf_client:
        token = os.getenv("HF_TOKEN")
        if token: _hf_client = AsyncInferenceClient(token=token)
    return _hf_client

def configure_gemini():
    global _gemini_configured
    if not _gemini_configured:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            _gemini_configured = True
    return _gemini_configured

# --- CLASSIFICATION ENGINES ---

async def classify_with_groq(prompt: str) -> Optional[Dict]:
    if not _groq_clients: return None
    
    # Try all available keys in round-robin fashion
    for _ in range(len(_groq_clients)):
        client = get_groq_client()
        try:
            completion = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a professional conflict intelligence analyst. Output ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            if "429" in str(e):
                log.warning(f"Groq Key limited. Rotating to next...")
                continue # Try next key
            else:
                log.error(f"Groq Engine Error: {e}")
                return None
    return None

async def classify_with_gemini(prompt: str) -> Optional[Dict]:
    if not configure_gemini(): return None
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Gemini expects structured feedback, we wrap it
        response = await asyncio.to_thread(model.generate_content, f"{prompt}\nReturn ONLY JSON.")
        text = response.text
        # Clean potential markdown wrapping
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        log.error(f"Gemini Engine Error: {e}")
        return None

async def classify_with_hf(prompt: str) -> Optional[Dict]:
    client = get_hf_client()
    if not client: return None
    try:
        # Using Llama 3.3 70B via Serverless Inference API
        model_id = "meta-llama/Llama-3.3-70B-Instruct"
        messages = [
            {"role": "system", "content": "You are a professional conflict intelligence analyst. Output ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ]
        response = await client.chat_completion(
            model=model_id,
            messages=messages,
            max_tokens=1000,
            temperature=0.1
        )
        text = response.choices[0].message.content
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        log.error(f"HF Inference Error: {e}")
        return None

# --- MAIN GATEWAY ---

async def classify_event_llm(title: str, summary: str = "") -> Dict[str, Any]:
    """
    Resilient Multi-Engine Classification Gateway.
    Tries Groq -> Gemini -> HF -> Regex Fallback.
    """
    prompt = f"""Analyze this news headline for an ELITE conflict intelligence database.
Your goal is absolute accuracy. Only classify REAL kinetic/military/violent incidents.
Reject diplomacy, politics, economics, sports, or opinion articles.

Title: {title}
Summary: {summary}

Return a JSON object with these fields:
- is_conflict_tactical: Boolean. True ONLY if this is a real kinetic event (explosions, airstrikes, armed clashes, shootings, bombings, military operations). False for diplomacy, sanctions, protests, elections, humanitarian aid, opinion pieces, or general politics.
- validation_logic: 1 sentence explaining your reasoning.
- category: MILITARY, TERRORIST, MILITANT, CIVIL_UNREST, or GENERAL
- strategic_significance: CRITICAL, HIGH, MEDIUM, or LOW
- event_type: Armed Clash, Airstrike / Artillery, Terrorist Attack, Drone Strike, Naval Engagement, Arrests / Detainment, or Other
- location_landmark: Specific facility name if mentioned (base, airport, port, checkpoint). null if none.
- location_city: Specific city or town. null if unclear.
- location_admin1: Province, state, or oblast name. null if unclear.
- location_country: Country name. Required.
- location_text_span: The exact phrase from the title referring to the location.
- confidence_score: Float 0.0-1.0 indicating overall data reliability.
- actor1: Primary armed group or military force. Be specific (e.g. "72nd Mechanized Brigade" not just "Ukraine").
- actor2: Secondary entity or target. null if unknown.
- weapon: Specific weapon system if mentioned (e.g. "Shahed-136", "HIMARS", "RPG-7"). null if not mentioned.
- fatalities: Integer count. 0 if not mentioned or unknown.
- severity_score: Float 0-10 based on tactical impact and scale.
"""

    # ENGINE TIER 1: GROQ
    res = await classify_with_groq(prompt)
    if res: return parse_llm_res(res, "GROQ")

    # ENGINE TIER 2: GEMINI
    res = await classify_with_gemini(prompt)
    if res: return parse_llm_res(res, "GEMINI")

    # ENGINE TIER 3: HF INFERENCE
    res = await classify_with_hf(prompt)
    if res: return parse_llm_res(res, "HF-API")

    # FINAL FALLBACK: REGEX
    cat, sev, tags, etype = classify_event(title, summary)
    return {
        "category": cat,
        "severity_score": sev,
        "tags": tags,
        "event_type": etype,
        "actor1": None,
        "actor2": None,
        "fatalities": 0,
        "notes": f"Classification: Regex Fallback (All AI Engines Failed)",
        "ai_classified": False,
        "provider": "REGEX"
    }

def parse_llm_res(res: Dict, provider: str) -> Dict[str, Any]:
    # World Monitor Noise Gate: Reject non-conflict or low-confidence events
    is_tactical = res.get("is_conflict_tactical")
    confidence = 0.0
    try:
        confidence = float(res.get("confidence_score", 0))
    except (ValueError, TypeError):
        confidence = 0.0

    if not is_tactical or confidence < 0.7:
        return {"is_noise": True, "logic": res.get("validation_logic", "Rejected by noise gate")}

    significance = res.get("strategic_significance", "LOW")

    return {
        "is_noise": False,
        "category": res.get("category", "GENERAL").upper(),
        "severity_score": float(res.get("severity_score", 3.0)),
        "strategic_relevance": significance,
        "location": res.get("location_landmark") or res.get("location_city"),
        "location_admin1": res.get("location_admin1"),
        "country": res.get("location_country"),
        "location_raw": res.get("location_text_span"),
        "extraction_confidence": confidence,
        "tags": [t for t in [res.get("actor1"), res.get("weapon")] if t],
        "event_type": res.get("event_type", "Other"),
        "actor1": res.get("actor1"),
        "actor2": res.get("actor2"),
        "weapon": res.get("weapon"),
        "fatalities": int(res.get("fatalities", 0)),
        "notes": f"[{significance}] {res.get('validation_logic', '')}",
        "ai_classified": True,
        "provider": provider
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
