-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- 4.2 active_conflicts (War-level rollup)
CREATE TABLE active_conflicts (
  conflict_id   SERIAL PRIMARY KEY,
  name          VARCHAR(200),            -- 'Russo-Ukrainian War'
  countries     TEXT[],                  -- ['UKR', 'RUS']
  region        VARCHAR(100),
  start_date    DATE,
  status        VARCHAR(20),             -- ACTIVE | CEASEFIRE | RESOLVED
  intensity     VARCHAR(20),             -- WAR | CRISIS | DISPUTE | TENSION
  total_events  INTEGER DEFAULT 0,
  last_event_at TIMESTAMP
);

-- 4.1 conflict_events
CREATE TABLE conflict_events (
  id              BIGSERIAL PRIMARY KEY,
  event_id        VARCHAR(100) UNIQUE NOT NULL,   -- CIQ-YYYYMMDD-ISO3-NNNNN
  source          VARCHAR(20)  NOT NULL,           -- GDELT | RSS | RELIEFWEB | UCDP
  source_reliability VARCHAR(10) DEFAULT 'MEDIUM', -- HIGH | MEDIUM | LOW

  event_time      TIMESTAMP NOT NULL,
  event_date      DATE      NOT NULL,
  year            SMALLINT  GENERATED ALWAYS AS (EXTRACT(YEAR FROM event_date)) STORED,
  week            SMALLINT  GENERATED ALWAYS AS (EXTRACT(WEEK FROM event_date)) STORED,

  country         VARCHAR(100) NOT NULL,
  country_iso3    CHAR(3)      NOT NULL,
  region          VARCHAR(100),
  admin1          VARCHAR(100),   -- Province / Oblast
  admin2          VARCHAR(100),   -- District / Rayon
  city            VARCHAR(100),
  lat             DECIMAL(9,6),
  lon             DECIMAL(10,6),
  geom            GEOGRAPHY(POINT,4326),
  geo_precision   SMALLINT DEFAULT 3,  -- 1=city 2=district 3=country

  event_type      VARCHAR(50),    -- Battles | Explosions | Violence vs Civilians | Protests
  event_subtype   VARCHAR(80),    -- Armed clash | Air/drone strike | Shelling…
  interaction_code VARCHAR(60),   -- Military vs Military | Military vs Civilians…
  actor1          VARCHAR(200),
  actor1_type     VARCHAR(50),    -- Military Forces | Rebel Group | Civilians…
  actor2          VARCHAR(200),
  actor2_type     VARCHAR(50),

  fatalities          INTEGER DEFAULT 0,
  fatalities_civilians INTEGER DEFAULT 0,
  fatalities_confidence VARCHAR(10) DEFAULT 'LOW',  -- HIGH | MEDIUM | LOW
  severity            VARCHAR(20),     -- HIGH | MEDIUM | LOW
  severity_score      DECIMAL(4,2),    -- 0.00 – 10.00

  title           VARCHAR(500),
  notes           TEXT,
  tags            TEXT[],          -- ['artillery','urban-combat','civilian-area']
  source_url      TEXT,
  conflict_name   VARCHAR(200),    -- 'Russo-Ukrainian War'
  conflict_id     INTEGER REFERENCES active_conflicts(conflict_id),
  category        VARCHAR(20) DEFAULT 'GENERAL',

  ingested_at     TIMESTAMP DEFAULT NOW()
);

-- INDEXES (sub-10ms guaranteed)
CREATE INDEX idx_event_time   ON conflict_events(event_time DESC);
CREATE INDEX idx_country_time ON conflict_events(country_iso3, event_time DESC);
CREATE INDEX idx_geom         ON conflict_events USING GIST(geom);
CREATE INDEX idx_severity     ON conflict_events(severity_score DESC);
CREATE INDEX idx_category     ON conflict_events(category);
CREATE INDEX idx_type         ON conflict_events(event_type, event_time DESC);
CREATE INDEX idx_tags         ON conflict_events USING GIN(tags);

-- We trigger a NOTIFY when a new conflict event is inserted
-- This pushes data to the websocket
CREATE OR REPLACE FUNCTION notify_new_conflict_event()
RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify(
    'new_conflict_event',
    row_to_json(NEW)::text
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_new_conflict_event
AFTER INSERT ON conflict_events
FOR EACH ROW EXECUTE FUNCTION notify_new_conflict_event();

-- 5. Intelligence Articles Hub
CREATE TABLE intel_articles (
  id              SERIAL PRIMARY KEY,
  title           VARCHAR(255) NOT NULL,
  content         TEXT NOT NULL,            -- Supports Markdown
  author          VARCHAR(100),
  tags            TEXT[],
  created_at      TIMESTAMP DEFAULT NOW(),
  updated_at      TIMESTAMP DEFAULT NOW(),
  search_vector   TSVECTOR GENERATED ALWAYS AS (
    to_tsvector('english', title || ' ' || content)
  ) STORED
);

CREATE INDEX idx_articles_search ON intel_articles USING GIN(search_vector);
CREATE INDEX idx_articles_created ON intel_articles(created_at DESC);
