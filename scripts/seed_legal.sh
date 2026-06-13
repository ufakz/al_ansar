#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Applying legal corpus migration..."
docker exec -i alansar-postgres psql -U alansar -d alansar < backend/db/migrations/003_legal_corpus.sql

echo "Building legal corpus from PDFs..."
docker compose run --rm \
  -e AL_ANSAR_ROOT=/workspace \
  -e DATABASE_URL=postgresql://alansar:alansar@postgres:5432/alansar \
  backend python -m grounding.build_corpus

echo "Legal corpus ready."
