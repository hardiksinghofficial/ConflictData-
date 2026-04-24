import hashlib
import logging
from api.database import db

log = logging.getLogger(__name__)

async def is_duplicate_event(title: str, window_days: int = 1) -> bool:
    """
    Checks if a similar headline has been processed recently.
    Uses semantic hashing (normalized title) and Redis/Mem storage.
    """
    if not title: return False
    
    # Simple normalization for semantic hashing
    normalized = "".join(filter(str.isalnum, title.lower()))
    hash_key = hashlib.md5(normalized.encode()).hexdigest()
    
    redis_key = f"seen_event:{hash_key}"
    
    if db.redis:
        exists = await db.redis.get(redis_key)
        if exists:
            log.debug(f"Token Saved: Skipping duplicate event: {title[:50]}...")
            return True
        
        # Mark as seen for X days
        await db.redis.setex(redis_key, 86400 * window_days, "1")
    
    return False
