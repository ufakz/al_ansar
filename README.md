# Al-Ansar

When a crisis affecting Muslims is detected, Al-Ansar grounds it in real public law, identifies legitimate response routes (legal aid, ombudsman, FOI), breaks work into tasks, and matches skilled **Ansar** helpers.

**Stack:** Postgres + pgvector, FastAPI, Next.js, Gemini API, Telegram notifications.

## Quick start

```bash
cp .env.example .env
# Add GEMINI_API_KEY and Telegram credentials to backend/.env

docker compose up --build
```

| Service  | URL                   |
|----------|-----------------------|
| Frontend | http://localhost:3000 |
| Backend  | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

## Seed data

```bash
./scripts/seed_legal.sh   # legal corpus from regulations/
./scripts/seed_users.sh   # 50 synthetic Ansar helpers
```

## Project layout

```
backend/     FastAPI — ingest, legal grounding, task decomposition, matching
frontend/    Next.js dashboard — crises, citations, tasks, Ansar matches
data/        Legal corpus manifest
scripts/     Seed and test helpers
```
