---
title: ConflictIQ API
emoji: 🌍
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# ConflictIQ API 🌍

Real-time global conflict intelligence API — powered by FastAPI, spaCy NER, and live RSS/GDELT ingestion.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check + DB status |
| GET | `/api/v1/conflicts` | List conflict events (filterable) |
| GET | `/api/v1/conflicts/recent` | Last N days of events |
| GET | `/api/v1/conflicts/country/{iso3}` | By country ISO3 code |
| GET | `/api/v1/conflicts/near` | Near a lat/lon radius |
| GET | `/api/v1/conflicts/{event_id}` | Single event detail |
| GET | `/api/v1/stats` | Aggregated statistics |
| GET | `/api/v1/active-conflicts` | Active conflict zones |
| WS  | `/api/v1/ws` | Live WebSocket stream |

## Tech Stack

- **FastAPI** — async REST API
- **spaCy** — NER-based geolocation extraction from news
- **APScheduler** — automated background polling (RSS every 2min, GDELT every 5min)
- **Neon (PostgreSQL + PostGIS)** — cloud-native geospatial database
- **Upstash (Redis)** — serverless caching layer
