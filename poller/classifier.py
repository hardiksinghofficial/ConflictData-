import logging
import re

log = logging.getLogger(__name__)

# Category definitions and their priority keywords
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

# Event Type definitions
EVENT_TYPES_MAP = {
    "Airstrike / Artillery": [r"\bair\s?strike\b", r"\bshelling\b", r"\bmissile\b", r"\bbombing\b", r"\bartiller(y|ies)\b"],
    "Terrorist Attack": [r"\bsuicide\b", r"\bterror(ist|ism)\b", r"\bblast\b", r"\bied\b", r"\bmassacre\b"],
    "Armed Clash": [r"\bclash(es)?\b", r"\battle\b", r"\bfights?\b", r"\bclash\b", r"\boffensive\b", r"\binvasion\b"],
    "Arrests / Detainment": [r"\barrests?\b", r"\bdetain(ed|s)?\b", r"\bcustody\b"],
    "Strategic Report": [r"\breport\b", r"\banalysis\b", r"\bupdate\b", r"\bsitrep\b"]
}

def classify_event(title: str, summary: str = "") -> tuple:
    """
    Classifies an event based on title and summary.
    Returns (category, severity_score, tags, event_type)
    """
    combined_text = (title + " " + summary).lower()
    
    found_category = "GENERAL"
    max_severity = 3.0
    tags = []
    found_event_type = "Violence" # Default

    # 1. Determine Event Type (New Logic)
    for etype, patterns in EVENT_TYPES_MAP.items():
        if any(re.search(p, combined_text) for p in patterns):
            found_event_type = etype
            break

    # 2. Determine Category (Existing Logic)
    # Priority order: Terrorist > Military > Militant
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
