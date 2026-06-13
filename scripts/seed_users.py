"""Load ansar_users from ansar_users.json into Postgres."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
USERS_FILE = ROOT / "ansar_users.json"

INSERT_SQL = """
INSERT INTO ansar_users (
    id, name, skills, lat, lng, languages, trust_tier, capacity, telegram_chat_id
) VALUES (
    %(id)s, %(name)s, %(skills)s, %(lat)s, %(lng)s,
    %(languages)s, %(trust_tier)s, %(capacity)s, %(telegram_chat_id)s
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    skills = EXCLUDED.skills,
    lat = EXCLUDED.lat,
    lng = EXCLUDED.lng,
    languages = EXCLUDED.languages,
    trust_tier = EXCLUDED.trust_tier,
    capacity = EXCLUDED.capacity,
    telegram_chat_id = EXCLUDED.telegram_chat_id
"""


def main() -> None:
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql://alansar:alansar@localhost:5432/alansar"
    )
    if not USERS_FILE.is_file():
        print(f"Users file not found: {USERS_FILE}", file=sys.stderr)
        sys.exit(1)

    users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    if not isinstance(users, list):
        print("ansar_users.json must contain a JSON array", file=sys.stderr)
        sys.exit(1)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for user in users:
                cur.execute(INSERT_SQL, user)
        conn.commit()

    print(f"Seeded {len(users)} ansar users from {USERS_FILE.name}.")


if __name__ == "__main__":
    main()
