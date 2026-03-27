Run the full test suite for ClawScout (backend + frontend).

Execute both in sequence:

```bash
# 1. Backend tests (pytest with SQLite)
wsl.exe -d Ubuntu -- bash -c "cd /home/briar/src/ClawScout && source .venv/bin/activate && pytest -v"

# 2. Frontend type check
wsl.exe -d Ubuntu -- bash -c "cd /home/briar/src/ClawScout/dashboard && npx tsc --noEmit"
```

Report:
- Total tests passed/failed
- Any type errors in frontend
- If all green, say so clearly with evidence
- If failures, show the failing test names and errors
