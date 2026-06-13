#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Seeding ansar_users from ansar_users.json..."
docker compose run --rm \
  -e AL_ANSAR_ROOT=/workspace \
  -e DATABASE_URL=postgresql://alansar:alansar@postgres:5432/alansar \
  backend python /workspace/scripts/seed_users.py

echo "Ansar users ready."
