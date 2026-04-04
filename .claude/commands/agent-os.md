Common Agent OS operations for Scouter. The user will say what they need — use the matching command.

## Available operations

### Check AI health
```bash
curl -s http://localhost:8000/api/v1/performance/ai-health | python3 -m json.tool
```
Report: approval rate, fallback rate, avg latency, invocations in last 24h.

### View agent status
```bash
curl -s http://localhost:8000/api/v1/ai-office/status | python3 -m json.tool
```
Report: each agent's status (Mote, Scout, Executor, Reviewer), outcomes summary.

### View recent AI decisions
```bash
curl -s "http://localhost:8000/api/v1/ai-office/decisions?limit=10" | python3 -m json.tool
```
Report: function, role, model, status, latency for each decision.

### View Scout investigations
```bash
curl -s "http://localhost:8000/api/v1/ai-office/investigations?limit=5" | python3 -m json.tool
```
Report: lead, pages visited, loops, duration, findings.

### Trigger weekly report
```bash
curl -s -X POST http://localhost:8000/api/v1/ai-office/weekly-reports/generate | python3 -m json.tool
```
Report: whether generation succeeded, report ID.

### Run pipeline on a lead
```bash
cd /home/mateo/Scouter && .venv/bin/python scripts/scouterctl.py run-pipeline --lead-id <LEAD_ID>
```
Replace `<LEAD_ID>` with the actual UUID. Report pipeline status.

### Test WhatsApp
```bash
curl -s -X POST http://localhost:8000/api/v1/ai-office/test-send-whatsapp \
  -H "Content-Type: application/json" \
  -d '{"phone": "<PHONE>", "message": "Test from Scouter"}' | python3 -m json.tool
```
Replace `<PHONE>` with E.164 format (e.g. +5491158399708). Report send status.

### View scoring recommendations
```bash
curl -s http://localhost:8000/api/v1/performance/recommendations | python3 -m json.tool
```
Report: recommended weight changes based on outcome data.

### View correction patterns
```bash
curl -s http://localhost:8000/api/v1/reviews/corrections/summary | python3 -m json.tool
```
Report: top reviewer correction categories and counts.

## Notes
- All endpoints require the API to be running (`make up` or `make dev-up`)
- If API_KEY is set in .env, add `-H "X-API-Key: <key>"` to curl commands
- For detailed docs: [docs/agents/hierarchy.md](../../docs/agents/hierarchy.md)
