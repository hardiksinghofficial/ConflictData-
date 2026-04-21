# Frontend API Integration Guide

This document explains, in implementation detail, how the frontend consumes backend APIs and real-time streams, and how each payload is transformed into UI behavior.

## 1) Frontend Architecture Overview

The frontend is a React SPA with two routes:

- `/` -> Tactical dashboard (`Dashboard.jsx`)
- `/sitrep` -> Strategic analytics page (`AnalyticsPage.jsx`)

Key orchestration files:

- `frontend/src/config.js`: selects API base URL.
- `frontend/src/Dashboard.jsx`: loads tactical data + subscribes to WebSocket.
- `frontend/src/components/AnalyticsPage.jsx`: loads strategic data + reads SSE AI stream.
- `frontend/src/hooks/useTacticalWS.js`: resilient WebSocket connection and reconnect.

## 2) API Base URL Resolution

File: `frontend/src/config.js`

Behavior:

- If hostname is `localhost` or `127.0.0.1`, API base is hardcoded to:
  - `https://hardik1231312-conflictdata.hf.space`
- Otherwise, base is empty string `''` (same-origin relative requests).

Implementation impact:

- Local development still targets deployed backend unless this config is changed.
- Production uses relative paths like `/api/v1/...`.

## 3) Route-Level Data Responsibilities

### `/` Dashboard (`frontend/src/Dashboard.jsx`)

Owns:

- Tactical event timeline
- Threat counters
- Map intelligence layers
- Flash alerts
- Live connectivity status

Data sources:

- One-time bootstrapping REST calls on mount.
- Continuous WebSocket stream (`/api/v1/ws`) for live event inserts.

### `/sitrep` Strategic Analytics (`frontend/src/components/AnalyticsPage.jsx`)

Owns:

- Situation briefing summary
- Strategic forecast
- Theater cards
- AI streaming report terminal

Data sources:

- Polling REST calls every 60s for strategic snapshots.
- On-demand SSE stream for AI analyst output (`/api/v1/ai/analyze`).

## 4) Dashboard API Integration (Detailed)

File: `frontend/src/Dashboard.jsx`

### 4.1 Initial REST bootstrap (`useEffect` on mount)

The dashboard executes all requests concurrently using `Promise.all` with a `safeFetch` wrapper.

Endpoints called:

1. `GET /api/v1/stats/stats`
2. `GET /api/v1/conflicts/ongoing?limit=100`
3. `GET /api/v1/intel/monitor`
4. `GET /api/v1/intel/frontlines`
5. `GET /api/v1/intel/hotspots`
6. `GET /api/v1/intel/trends`
7. `GET /api/v1/intel/sitrep`
8. `GET /api/v1/intel/theaters`

`safeFetch` behavior:

- Returns parsed JSON when `res.ok`.
- Returns `null` for non-2xx or network errors.
- Prevents one failing endpoint from crashing the whole init sequence.

### 4.2 State mapping from responses

State variables:

- `events`: set from `eventsRes.data` (ongoing conflicts endpoint).
- `stats`:
  - `total_events` <- `statsRes.total_events`
  - `high_severity` <- `statsRes.by_severity.HIGH`
  - `sitrep` <- full `sitrepRes` object
  - `active_wars` currently fixed `0` (not dynamically sourced)
- `layerData`:
  - `monitor` <- `monitorRes`
  - `frontlines` <- `frontRes`
  - `hotspots` <- `hotRes`
  - `trends` <- `trendRes`
  - `theaters` <- `theaterRes`

All layer arrays are normalized with:

- `safeArr = arr => Array.isArray(arr) ? arr : []`

This guards against null/error shapes.

### 4.3 Layer counts derived from API payloads

Layer metadata in `layers` state is updated after bootstrap:

- `kinetic.count` <- ongoing events length
- `theaters.count` <- theaters length
- `priority.count` <- monitor length
- `frontlines.count` <- frontlines length
- `hotspots.count` <- hotspots length
- `surges.count` <- trends length
- `civilians.count` <- events with `fatalities_civilians > 0`

These counts drive `LayerManager` telemetry badges.

### 4.4 Real-time updates from WebSocket

Hook: `useTacticalWS` with callback:

- Prepends new event into `events` (keeps max ~100 items):
  - `[newEvent, ...prev.slice(0, 99)]`
- Triggers flash alert for high-priority events when:
  - `newEvent.severity_score >= 7.5` OR `newEvent.priority === true`
- Increments:
  - `stats.total_events` by 1
  - `stats.high_severity` by 1 when `severity_score >= 8.5`
- Updates `kinetic` layer count.

Flash alert UI:

- Shows `title`, `city`, `country`.
- Auto-dismisses after 8 seconds.

## 5) WebSocket Transport Implementation

File: `frontend/src/hooks/useTacticalWS.js`

### 5.1 URL selection

- If `API_BASE` starts with `http`, converts to WS:
  - `http` -> `ws`
  - `https` -> `wss`
  - appends `/api/v1/ws`
- Otherwise builds same-origin URL:
  - `${protocol}//${window.location.host}/api/v1/ws`

### 5.2 Lifecycle and resiliency

- On mount: call `connect()`.
- On open:
  - set status `ONLINE`
  - clear reconnect timer if active
- On message:
  - parse JSON and forward to callback
- On close:
  - set status `OFFLINE`
  - schedule reconnect after 5 seconds
- On error:
  - close socket (which triggers reconnect flow)
- On unmount:
  - close socket cleanly

Status is surfaced to dashboard header as `COMMS`.

## 6) How API Data Is Rendered in UI Components

### 6.1 TacticalMap (`frontend/src/components/TacticalMap.jsx`)

Consumes:

- `events` (ongoing + websocket inserts)
- `layerData` (monitor/frontlines/hotspots/trends/theaters)
- `layers` toggles/opacities

Render rules by API source:

- `/conflicts/ongoing` + WS events:
  - Kinetic `Marker`s at `[lat, lon]`
  - popup fields: `title`, `severity_score`, `country_iso3`, `actor1`, `weapon`, `fatalities`, `notes`
- `/intel/frontlines`:
  - large `Circle` overlays with `primary_engagement`, `country`
- `/intel/hotspots`:
  - heat-style `Circle` overlays
- `/intel/trends`:
  - surge circles built from derived centroids:
    - For each trend country, average `lat/lon` of matching current `events`
    - display `surge_percentage`
- `/intel/monitor`:
  - priority markers
- `/intel/theaters`:
  - strategic theater circles using:
    - `center_lat`, `center_lon`, `spread_km`, `stability_rating`, `intensity`, `dominant_actor`, `total_events`
  - visual severity color based on stability and intensity.

Interaction using frontend routing + API context:

- `DEEP ANALYZE SECTOR` button builds a context string from selected event fields and navigates:
  - `navigate('/sitrep', { state: { context } })`
- This context is later sent to `/api/v1/ai/analyze?context=...`.

### 6.2 TacticalFeed (`frontend/src/components/TacticalFeed.jsx`)

Consumes `events`.

Uses API fields:

- Event categorization: `event_type`
- Time display: `event_time`
- Card title: `title`
- Telemetry chips: `actor1`, `weapon`, `fatalities`
- Location: `city`, `country`
- Severity styling: `severity_score`

Selection behavior:

- Clicking a feed card sends selected event to parent.
- Parent recenters map and highlights selected card.

### 6.3 CombatTicker (`frontend/src/components/CombatTicker.jsx`)

Consumes `events`.

Uses:

- `event_type`, `title`, `city`, `country_iso3`

Output:

- Scrolling duplicated ticker text loop.

### 6.4 LayerManager (`frontend/src/components/LayerManager.jsx`)

No direct API calls.

Consumes counts/opacities derived from API data in parent state.

Purpose:

- Toggle map layers.
- Adjust per-layer opacity.
- Show live count badges populated from API-backed state.

## 7) Strategic Analytics Page Integration

File: `frontend/src/components/AnalyticsPage.jsx`

### 7.1 Polling REST data (every 60 seconds)

Endpoints:

- `GET /api/v1/intel/sitrep`
- `GET /api/v1/intel/forecast`
- `GET /api/v1/intel/theaters`

State mapping:

- `sitrep` <- sitrep payload
- `forecast` <- forecast payload
- `theaters` <- theaters array

UI bindings:

- Situation Briefing block <- `sitrep.summary`
- Threat intensity badge <- `sitrep.intensity`
- Forecast card <- `forecast.forecast`, `forecast.risk_level`
- Theater cards <- `theaters[*]` fields (`name`, `intensity`, `dominant_actor`, `stability_rating`)
- Right-side stat mini-cards:
  - active ops = `theaters.length`
  - actors = `sitrep.stats.most_active_actor ? 1 : 0`
  - intel feed = `sitrep.stats.total_events`
  - fatalities = `sitrep.stats.total_fatalities`

### 7.2 AI stream ingestion (`/api/v1/ai/analyze`)

Trigger:

- On page load (and when navigation state changes), `startAnalysis(context)` is called.

Context mode:

- If `location.state.context` exists:
  - `GET /api/v1/ai/analyze?context=<encoded>`
- Else:
  - `GET /api/v1/ai/analyze`

Streaming parser:

- Reads response body with `ReadableStream` reader.
- Splits incoming text by newline.
- Extracts lines prefixed with `data: `.
- Appends token text progressively to `report` state.

Error behavior:

- Appends `[CRITICAL ERROR: INTELLIGENCE LINK SEVERED]`.

### 7.3 AIAnalyst terminal rendering

File: `frontend/src/components/AIAnalyst.jsx`

Consumes:

- `report`, `isAnalyzing`, `provider`

Behavior:

- Auto-scroll as report grows.
- Animated status text while streaming.
- Confidence meter:
  - grows during analysis
  - fixed to 96.4 on completion

## 8) Unused API-Capable Component

File: `frontend/src/components/ConflictRollup.jsx`

Contains integration to:

- `GET /api/v1/active-conflicts` (with 60s refresh)

Current status:

- Not imported or rendered by any active route/component.
- API call is implemented but dormant unless this component is mounted.

## 9) End-to-End Data Flow Summary

1. App routes user to Dashboard or Sitrep page.
2. Dashboard:
   - pulls tactical baseline snapshots via REST
   - opens WS connection for delta updates
   - merges WS events into the same `events` list
3. Map/feed/ticker consume shared `events` and `layerData`.
4. User can select a map event and jump to Sitrep with generated context.
5. Sitrep page:
   - polls strategic snapshots every minute
   - streams AI analysis via SSE endpoint
   - progressively renders analyst text in terminal panel.

## 10) API Contract Dependencies by Field

Critical fields expected by frontend rendering:

- Map markers: `lat`, `lon`, `event_id`
- Severity visuals: `severity_score`
- Feed labels: `event_type`, `title`, `event_time`
- Location labels: `city`, `country`, `country_iso3`
- Theaters overlay: `center_lat`, `center_lon`, `spread_km`, `stability_rating`, `intensity`
- Trend overlays: `country_iso3`, `surge_percentage`
- Sitrep cards: `summary`, `intensity`, `stats.total_events`, `stats.total_fatalities`
- Forecast card: `forecast`, `risk_level`
- WS alerting: `priority` boolean (or fallback from severity score)

If these fields are missing/null, affected UI areas degrade (empty markers, broken centering, missing labels, or fallback placeholders).

## 11) Current Frontend Resilience Patterns

Implemented:

- `safeFetch` null-guards in dashboard bootstrap.
- `Array.isArray` guards for layer arrays.
- WebSocket auto-reconnect every 5 seconds.
- Graceful placeholder text on missing strategic data.
- SSE stream appends partial data without blocking full completion.

Not yet implemented:

- Central API client abstraction (calls are inline).
- Runtime schema validation for payloads.
- Abort controllers for in-flight request cancellation on unmount.
- Backoff/jitter strategy for HTTP retries.
- Unified toast/error surface for users (errors are mostly `console.error`).

## 12) Practical Implementation Notes

- The UI references some fields not guaranteed by all endpoints, such as `weapon`; backend payloads should include or frontend should guard further.
- Dashboard currently fetches `sitrep` as part of tactical boot and stores it inside `stats.sitrep` rather than a dedicated state object.
- Analytics polling and analysis streaming are independent; strategic cards can refresh while report stream runs.

