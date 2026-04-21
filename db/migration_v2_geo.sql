-- Migration: V2 High-Fidelity Geocoding Metadata
-- Adds precision, confidence, and auditing metadata to conflict_events

ALTER TABLE conflict_events 
    ADD COLUMN IF NOT EXISTS geo_confidence NUMERIC(4,3),
    ADD COLUMN IF NOT EXISTS geo_method VARCHAR(40),
    ADD COLUMN IF NOT EXISTS geocode_provider VARCHAR(40),
    ADD COLUMN IF NOT EXISTS location_raw TEXT,
    ADD COLUMN IF NOT EXISTS location_admin1 VARCHAR(100),
    ADD COLUMN IF NOT EXISTS geo_validation_flags TEXT[];

-- Update comments for clarity
COMMENT ON COLUMN conflict_events.geo_precision IS '1=exact/city, 2=near-exact/admin, 3=country/approximate';
COMMENT ON COLUMN conflict_events.geo_confidence IS 'Score from 0.000 to 1.000 indicating geocoding certainty';
COMMENT ON COLUMN conflict_events.geo_method IS 'Algorithm used: ranked_nominatim, hotspot_override, etc.';

-- Index for confidence filtering
CREATE INDEX IF NOT EXISTS idx_geo_confidence ON conflict_events(geo_confidence);
