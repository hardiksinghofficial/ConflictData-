import logging
from api.database import db
import asyncio

log = logging.getLogger("api.bootstrap")

TABLE_ACTIVE_CONFLICTS = """
CREATE TABLE IF NOT EXISTS active_conflicts (
  conflict_id   SERIAL PRIMARY KEY,
  name          VARCHAR(200),
  countries     TEXT[],
  region        VARCHAR(100),
  start_date    DATE,
  status        VARCHAR(20) DEFAULT 'ACTIVE',
  intensity     VARCHAR(20) DEFAULT 'CRISIS',
  total_events  INTEGER DEFAULT 0,
  last_event_at TIMESTAMP DEFAULT NOW()
);
"""

TABLE_CONFLICT_EVENTS = """
CREATE TABLE IF NOT EXISTS conflict_events (
  id              BIGSERIAL PRIMARY KEY,
  event_id        VARCHAR(100) UNIQUE NOT NULL,
  source          VARCHAR(20)  NOT NULL,
  source_reliability VARCHAR(10) DEFAULT 'MEDIUM',
  event_time      TIMESTAMP NOT NULL,
  event_date      DATE      NOT NULL,
  country         VARCHAR(100) NOT NULL,
  country_iso3    CHAR(3)      NOT NULL,
  region          VARCHAR(100),
  admin1          VARCHAR(100),
  admin2          VARCHAR(100),
  city            VARCHAR(100),
  lat             DECIMAL(9,6),
  lon             DECIMAL(10,6),
  geom            GEOGRAPHY(POINT,4326),
  geo_precision   SMALLINT DEFAULT 3,
  event_type      VARCHAR(50),
  event_subtype   VARCHAR(80),
  interaction_code VARCHAR(60),
  actor1          VARCHAR(200),
  actor1_type     VARCHAR(50),
  actor2          VARCHAR(200),
  actor2_type     VARCHAR(50),
  fatalities      INTEGER DEFAULT 0,
  fatalities_civilians INTEGER DEFAULT 0,
  fatalities_confidence VARCHAR(10) DEFAULT 'LOW',
  severity        VARCHAR(20),
  severity_score  DECIMAL(4,2),
  title           VARCHAR(500),
  notes           TEXT,
  tags            TEXT[],
  source_url      TEXT,
  conflict_name   VARCHAR(200),
  conflict_id     INTEGER REFERENCES active_conflicts(conflict_id),
  category        VARCHAR(20) DEFAULT 'GENERAL',
  ingested_at     TIMESTAMP DEFAULT NOW()
);
"""

TABLE_INTEL_ARTICLES = """
CREATE TABLE IF NOT EXISTS intel_articles (
  id              SERIAL PRIMARY KEY,
  title           VARCHAR(255) NOT NULL,
  content         TEXT NOT NULL,
  author          VARCHAR(100),
  tags            TEXT[],
  created_at      TIMESTAMP DEFAULT NOW(),
  updated_at      TIMESTAMP DEFAULT NOW()
);
"""

SEARCH_VECTOR_ADD = """
DO $$ 
BEGIN 
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='intel_articles' AND column_name='search_vector') THEN
    ALTER TABLE intel_articles ADD COLUMN search_vector TSVECTOR 
    GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || content)) STORED;
  END IF;
END $$;
"""

async def bootstrap_db():
    log.info("Starting database bootstrap process...")
    try:
        async with db.pool.acquire() as conn:
            # 1. Extensions
            await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            
            # 2. Tables
            await conn.execute(TABLE_ACTIVE_CONFLICTS)
            await conn.execute(TABLE_CONFLICT_EVENTS)
            await conn.execute(TABLE_INTEL_ARTICLES)
            
            # 3. Features
            await conn.execute(SEARCH_VECTOR_ADD)
            
            # 4. Indexes (Safe Creation)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_event_time ON conflict_events(event_time DESC);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_country_time ON conflict_events(country_iso3, event_time DESC);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_geom ON conflict_events USING GIST(geom);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_search ON intel_articles USING GIN(search_vector);")
            
            log.info("[Bootstrap] Database schema validation and initialization complete.")
    except Exception as e:
        log.error(f"[Bootstrap] Critical Failure: {e}")
        # We don't raise here to allow the API to heartbeat even if DB is partially broken
