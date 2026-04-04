---
name: scouter-briefs
description: "Operational briefs and prioritization via API. Use curl or apiFetch to query /api/v1/briefs, /api/v1/dashboard/stats, /api/v1/performance/ai-health, /api/v1/leads?quality=high. Summarize results in Spanish."
metadata: { "hermes": { "emoji": "📋", "os": ["linux"] } }
---

# Scouter Briefs Skill

Operational briefs using API endpoints. Query real data, then summarize.

## When to use

- "resumime los briefs pendientes"
- "que leads deberia mirar primero"
- "como esta la salud del sistema IA"
- "que cambio hoy"
- Any question asking for prioritization or operational summary

## When NOT to use

- Sending drafts -> use **scouter-mail**
- Mutating actions -> use **scouter-actions**
- Raw data exports -> use **scouter-data**

## Hard rules

1. Always query the API first — do not make up data.
2. Summarize in Spanish (rioplatense).
3. If the backend is not running, say so instead of guessing.

## API Queries

```bash
API="http://localhost:8000/api/v1"

# Commercial briefs list
curl -s "$API/briefs" | python3 -m json.tool

# High-priority leads
curl -s "$API/leads?quality=high&limit=10" | python3 -m json.tool

# Dashboard overview stats
curl -s "$API/dashboard/stats" | python3 -m json.tool

# AI health (approval rate, fallback rate, latency)
curl -s "$API/performance/ai-health" | python3 -m json.tool

# Recent AI decisions
curl -s "$API/ai-office/decisions?limit=10" | python3 -m json.tool

# Outcome analytics
curl -s "$API/performance/outcomes" | python3 -m json.tool

# Scoring recommendations
curl -s "$API/performance/recommendations" | python3 -m json.tool
```

## Brief Types

| Request | API endpoint |
|---|---|
| Commercial briefs | `GET /api/v1/briefs` |
| Priority leads | `GET /api/v1/leads?quality=high&limit=10` |
| System overview | `GET /api/v1/dashboard/stats` |
| AI health | `GET /api/v1/performance/ai-health` |
| Outcome summary | `GET /api/v1/performance/outcomes` |
| Recommendations | `GET /api/v1/performance/recommendations` |
| Weekly reports | `GET /api/v1/ai-office/weekly-reports?limit=1` |
