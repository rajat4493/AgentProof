# Running AgentProof Locally (for demos)

This is the quick-start for getting the app up before a demo — not a deployment guide. See
`backend/requirements.txt` / `frontend/package.json` for exact dependency versions.

## 1. Database

```bash
# Postgres must be running and reachable at the URL in backend/.env
createuser agentproof --pwprompt   # first time only
createdb agentproof -O agentproof  # first time only
```

## 2. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY before demoing — the agent is real, not mocked
python -m app.seed     # seeds the demo customer (C-891) and order (ORD-1047)
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Confirm it's up: `curl http://127.0.0.1:8000/api/health` → `{"status":"ok"}`.

## 3. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev -- -p 3000
```

Open `http://localhost:3000`.

## Before every demo

- Confirm `ANTHROPIC_API_KEY` is set in `backend/.env` — every scenario makes real Claude API
  calls. There is no offline/mock demo mode by design (a faked demo would undercut the entire
  pitch, which is that AgentProof checks *real* systems).
- Run one scenario yourself first (any of the four buttons) to confirm the API key and both
  servers are healthy before a buyer is watching.
- See `docs/DEMO_SCRIPT.md` for the actual demo path once the app is up.
