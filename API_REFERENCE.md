# ConflictIQ API Reference

This document describes the API routes currently implemented in the backend (`/api/v1`), including request parameters and response body shapes.

## Base URLs

- API base: `/api/v1`
- Health (also exposed outside API prefix): `/health`

## Authentication

- No authentication/authorization is currently enforced in these routes.

## Common Notes

- All dates use `YYYY-MM-DD`.
- Most timestamps are ISO-like strings and often end with `Z`.
- Error responses from FastAPI typically look like:
  ```json
  { "detail": "Error message" }
  ```

## Core Event Object (`conflict_events` row)

Many endpoints return raw or near-raw `conflict_events` rows. Typical fields:

- `id` (integer)
- `event_id` (string)
- `source` (string)
- `source_reliability` (string)
- `event_time` (string datetime)
- `event_date` (string date)
- `year` (integer)
- `week` (integer)
- `country` (string)
- `country_iso3` (string)
- `region`, `admin1`, `admin2`, `city` (string/null)
- `lat`, `lon` (number/null)
- `geo_precision` (integer)
- `event_type`, `event_subtype`, `interaction_code` (string/null)
- `actor1`, `actor1_type`, `actor2`, `actor2_type` (string/null)
- `fatalities`, `fatalities_civilians` (integer)
- `fatalities_confidence` (string)
- `severity` (string/null)
- `severity_score` (number/null)
- `title`, `notes` (string/null)
- `tags` (string array/null)
- `source_url` (string/null)
- `conflict_name` (string/null)
- `conflict_id` (integer/null)
- `category` (string)
- `ingested_at` (string datetime)
- `geom` (internal PostGIS object, excluded in some endpoints)

---

## Health Endpoints

### `GET /health`
### `GET /api/v1/health`

Request parameters: none

Response body:
```json
{
  "status": "OK",
  "events_total": 1234,
  "database_connected": true,
  "redis_connected": true
}
```

---

## Conflicts API (`/api/v1/conflicts`)

### `GET /api/v1/conflicts`

Query parameters:

- `country` (string, optional)
- `category` (string, optional)
- `from_date` (date, optional, default = today - 7 days)
- `to_date` (date, optional, default = today)
- `event_type` (string, optional)
- `severity` (string, optional)
- `min_fatalities` (integer, optional, default `0`)
- `tags` (string, optional, comma-separated, example: `urban-combat,artillery`)
- `limit` (integer, optional, default `100`, max `500`)
- `offset` (integer, optional, default `0`)

Response body:
```json
{
  "status": 200,
  "success": true,
  "count": 2,
  "data": [{ "...event fields..." : "..." }],
  "meta": {
    "from_cache": false,
    "page": 1,
    "per_page": 100
  }
}
```

### `GET /api/v1/conflicts/recent`

Query parameters:

- `days` (integer, optional, default `7`)
- `limit` (integer, optional, default `100`)

Response body:
```json
{
  "status": 200,
  "success": true,
  "count": 2,
  "data": [{ "...event fields..." : "..." }],
  "meta": { "from_cache": false }
}
```

### `GET /api/v1/conflicts/ongoing`

Query parameters:

- `limit` (integer, optional, default `50`)

Response body:
```json
{
  "status": 200,
  "success": true,
  "count": 2,
  "data": [{ "...event fields without geom..." : "..." }]
}
```

### `GET /api/v1/conflicts/historical`

Query parameters:

- `days_ago` (integer, optional, default `2`)
- `limit` (integer, optional, default `100`)

Response body:
```json
{
  "status": 200,
  "success": true,
  "count": 2,
  "data": [{ "...event fields without geom..." : "..." }]
}
```

### `GET /api/v1/conflicts/near`

Query parameters:

- `lat` (number, required)
- `lon` (number, required)
- `radius_km` (integer, optional, default `50`)
- `days` (integer, optional, default `7`)
- `limit` (integer, optional, default `100`)

Response body:
```json
{
  "status": 200,
  "success": true,
  "count": 2,
  "data": [{ "...event fields without geom..." : "..." }],
  "meta": { "from_cache": false }
}
```

### `GET /api/v1/conflicts/country/{iso3}`

Path parameters:

- `iso3` (string, required)

Query parameters:

- `days` (integer, optional, default `30`)
- `limit` (integer, optional, default `100`)

Response body:
```json
{
  "status": 200,
  "success": true,
  "count": 2,
  "data": [{ "...event fields without geom..." : "..." }],
  "meta": { "from_cache": false }
}
```

### `GET /api/v1/conflicts/{event_id}`

Path parameters:

- `event_id` (string, required)

Response body:
```json
{
  "status": 200,
  "success": true,
  "data": { "...single event fields without geom..." : "..." },
  "meta": { "from_cache": false }
}
```

404 response:
```json
{ "detail": "Event not found" }
```

### `GET /api/v1/conflicts/clusters`

Query parameters:

- `precision` (number, optional, default `1.0`, min `0.1`, max `5.0`)
- `days` (integer, optional, default `7`)

Response body:
```json
{
  "status": 200,
  "count": 2,
  "data": [
    {
      "lon": 36.8219,
      "lat": -1.2921,
      "count": 7,
      "main_category": "MILITARY",
      "main_severity": "HIGH"
    }
  ]
}
```

---

## Stats API

### `GET /api/v1/stats`
### `GET /api/v1/stats/stats`

Query parameters:

- `country` (string, optional)
- `days` (integer, optional, default `30`)

Response body:
```json
{
  "country": "Global",
  "period_days": 30,
  "total_events": 120,
  "by_type": { "Airstrike / Artillery": 20, "Unknown": 5 },
  "by_severity": { "HIGH": 10, "UNKNOWN": 3 },
  "total_fatalities": 450,
  "civilian_fatalities": 120,
  "events_last_24h": 14,
  "trend": "STABLE"
}
```

### `GET /api/v1/active-conflicts`

Request parameters: none

Response body:
```json
[
  {
    "conflict_id": 1,
    "name": "Russo-Ukrainian War",
    "countries": ["UKR", "RUS"],
    "region": "Europe",
    "start_date": "2022-02-24",
    "status": "ACTIVE",
    "intensity": "WAR",
    "total_events": 2000,
    "last_event_at": "2026-04-20T09:25:00Z"
  }
]
```

---

## Intelligence API (`/api/v1/intel`)

### `GET /api/v1/intel/theaters`

Request parameters: none

Response body:
```json
[
  {
    "conflict_id": 1,
    "name": "Example Theater",
    "intensity": "WAR",
    "center_lat": 48.5,
    "center_lon": 37.9,
    "max_severity": 9.2,
    "total_fatalities": 300,
    "dominant_actor": "Actor Name",
    "primary_weapon": "unknown",
    "spread_km": 220.5,
    "total_events": 124,
    "stability_rating": 35.4
  }
]
```

### `GET /api/v1/intel/sitrep`

Request parameters: none

Response body:
```json
{
  "summary": "Global Intelligence Alert: ...",
  "intensity": "HIGH",
  "stats": {
    "total_events": 50,
    "total_fatalities": 210,
    "top_country": "UKR",
    "top_category": "MILITARY",
    "most_active_actor": "Actor Name"
  }
}
```

If no recent events:
```json
{
  "summary": "Stable. No major conflict events reported in the last 24h.",
  "intensity": "LOW"
}
```

### `GET /api/v1/intel/forecast`

Request parameters: none

Response body:
```json
{
  "forecast": "AI-generated strategic forecast text...",
  "risk_level": "CRITICAL",
  "timestamp": "2026-04-20"
}
```

### `GET /api/v1/intel/actors`

Request parameters: none

Response body:
```json
[
  {
    "actor1": "Actor Name",
    "involvement_count": 17,
    "fatal_impact": 93
  }
]
```

### `GET /api/v1/intel/trends`

Request parameters: none

Response body:
```json
[
  {
    "country_iso3": "UKR",
    "current_count": 21,
    "previous_count": 8,
    "surge_percentage": 162.5
  }
]
```

### `GET /api/v1/intel/hotspots`

Request parameters: none

Response body:
```json
[
  {
    "lon": 37.61,
    "lat": 48.01,
    "event_count": 12,
    "country_iso3": "UKR"
  }
]
```

### `GET /api/v1/intel/monitor`

Request parameters: none

Response body:

- Array of conflict event objects (`SELECT * FROM conflict_events ... LIMIT 15`).

### `GET /api/v1/intel/frontlines`

Request parameters: none

Response body:
```json
[
  {
    "lon": 37.6,
    "lat": 47.9,
    "event_count": 5,
    "country": "Ukraine",
    "country_iso3": "UKR",
    "highest_severity": 9.1,
    "primary_engagement": "Armed clash"
  }
]
```

500 response for intel endpoints:
```json
{ "detail": "Exception message" }
```

---

## Intelligence Hub API (`/api/v1/intel/articles`)

### `GET /api/v1/intel/articles`

Query parameters:

- `limit` (integer, optional, default `20`)
- `offset` (integer, optional, default `0`)

Response body:
```json
[
  {
    "id": 42,
    "title": "Daily Theater Summary",
    "author": "Ops Desk",
    "tags": ["ukraine", "airstrike"],
    "created_at": "2026-04-20T06:10:00"
  }
]
```

### `GET /api/v1/intel/articles/search`

Query parameters:

- `q` (string, required, min length `2`)

Response body:
```json
[
  {
    "id": 42,
    "title": "Daily Theater Summary",
    "author": "Ops Desk",
    "tags": ["ukraine"],
    "created_at": "2026-04-20T06:10:00",
    "rank": 0.425
  }
]
```

### `GET /api/v1/intel/articles/{article_id}`

Path parameters:

- `article_id` (integer, required)

Response body:

- Full `intel_articles` row as JSON object:
  - `id`, `title`, `content`, `author`, `tags`, `created_at`, `updated_at`, `search_vector`

404 response:
```json
{ "detail": "Article not found" }
```

### `POST /api/v1/intel/articles`

Request parameters (implemented as function params; currently handled as query/form-style fields):

- `title` (string, required)
- `content` (string, required)
- `author` (string, required)
- `tags` (string array, optional, default `[]`)

Response body:
```json
{
  "status": "published",
  "id": 43,
  "created_at": "2026-04-20T08:30:00"
}
```

---

## Data API (`/api/v1/data`)

### `GET /api/v1/data/events`

Query parameters:

- `country` (string, optional, ISO3)
- `actor` (string, optional, matches `actor1` or `actor2` using `ILIKE`)
- `start_date` (date, optional)
- `end_date` (date, optional)
- `limit` (integer, optional, default `100`)
- `offset` (integer, optional, default `0`)

Response body:

- Array of conflict event objects (raw DB rows).

### `GET /api/v1/data/acled`

Query parameters:

- `country` (string, optional)
- `limit` (integer, optional, default `100`)

Response body:
```json
[
  {
    "event_id_cnty": "CIQ-20260420-UKR-00001",
    "event_date": "2026-04-20",
    "year": 2026,
    "event_type": "Airstrike / Artillery",
    "actor1": "Actor A",
    "actor2": "Actor B",
    "country": "Ukraine",
    "location": "Dnipro",
    "latitude": 48.4647,
    "longitude": 35.0462,
    "source": "GDELT",
    "notes": "Text...",
    "fatalities": 8,
    "severity": 8.7
  }
]
```

### `GET /api/v1/data/export/csv`

Query parameters:

- `country` (string, optional)

Response:

- `text/csv` streamed file download.
- Header includes:
  - `Content-Disposition: attachment; filename=conflictiq_data_<YYYY-MM-DD>.csv`

### `GET /api/v1/data/geojson`

Query parameters:

- `limit` (integer, optional, default `500`)

Response body:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [36.82, -1.29] },
      "properties": {
        "event_id": "CIQ-...",
        "title": "Event title",
        "event_type": "Armed clash",
        "fatalities": 3
      }
    }
  ]
}
```

---

## AI Analyst API (`/api/v1/ai`)

### `GET /api/v1/ai/analyze`

Query parameters:

- `context` (string, optional)

Response:

- Content type: Server-Sent Events (SSE) stream
- Stream emits token chunks as:
  ```text
  data: <partial text token>
  ```

Error behavior:

- On failure, still returns an SSE stream with an error message token:
  ```text
  data: [COMMUNICATION LINK ERROR: ...]
  ```

---

## WebSocket API

### `WS /api/v1/ws`

Client behavior:

- Connect with WebSocket to `/api/v1/ws`.
- Server accepts the socket and keeps it open.
- Any text the client sends is received (currently not processed into replies).

Server push behavior:

- On every new `conflict_events` insert (via PostgreSQL `NOTIFY`), server broadcasts an event payload to all connected clients.
- Payload is JSON text of the inserted row plus:
  - `priority: true` if `category` is `MILITARY` or `TERRORIST`
  - `priority: false` otherwise

Example pushed message:
```json
{
  "id": 1001,
  "event_id": "CIQ-20260420-UKR-00001",
  "category": "MILITARY",
  "title": "Artillery strike near frontline",
  "event_time": "2026-04-20T09:45:00",
  "priority": true
}
```

---

## Implementation Caveats (Current Code)

- Route order issue: `/api/v1/conflicts/{event_id}` is declared before `/api/v1/conflicts/clusters`, so requests to `/conflicts/clusters` may be captured as `event_id="clusters"` depending on router matching behavior.
- `GET /api/v1/intel/theaters` uses `mode() ... ORDER BY weapon`, but `weapon` is not present in `conflict_events` schema in `db/init.sql`, which can cause runtime SQL errors unless schema differs in production.
- `POST /api/v1/intel/articles` currently uses plain function parameters (not an explicit JSON body model), so clients should send these fields as query/form parameters unless route code is updated.

