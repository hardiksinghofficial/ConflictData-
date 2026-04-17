from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from api.database import db
from datetime import datetime

router = APIRouter(prefix="/intel/articles", tags=["Intelligence Hub"])

@router.get("")
async def list_articles(limit: int = 20, offset: int = 0):
    """List recent intelligence articles."""
    query = "SELECT id, title, author, tags, created_at FROM intel_articles ORDER BY created_at DESC LIMIT $1 OFFSET $2"
    async with db.pool.acquire() as conn:
        records = await conn.fetch(query, limit, offset)
    return [dict(r) for r in records]

@router.get("/search")
async def search_articles(q: str = Query(..., min_length=2)):
    """Ultra-fast Full-Text Search across all intelligence reports."""
    query = """
    SELECT id, title, author, tags, created_at, 
           ts_rank(search_vector, plainto_tsquery('english', $1)) as rank
    FROM intel_articles 
    WHERE search_vector @@ plainto_tsquery('english', $1)
    ORDER BY rank DESC
    LIMIT 20
    """
    async with db.pool.acquire() as conn:
        records = await conn.fetch(query, q)
    return [dict(r) for r in records]

@router.get("/{article_id}")
async def get_article(article_id: int):
    """Retrieve a full intelligence report."""
    query = "SELECT * FROM intel_articles WHERE id = $1"
    async with db.pool.acquire() as conn:
        record = await conn.fetchrow(query, article_id)
    if not record:
        raise HTTPException(status_code=404, detail="Article not found")
    return dict(record)

@router.post("")
async def create_article(title: str, content: str, author: str, tags: List[str] = []):
    """Publish a new intelligence report."""
    query = """
    INSERT INTO intel_articles (title, content, author, tags)
    VALUES ($1, $2, $3, $4)
    RETURNING id, created_at
    """
    async with db.pool.acquire() as conn:
        record = await conn.fetchrow(query, title, content, author, tags)
    return {"status": "published", "id": record["id"], "created_at": record["created_at"]}
