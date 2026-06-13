"""Integration test for match_users_for_crisis with real Gemini and DB cache."""

import asyncio
from uuid import UUID

import pytest

from config import settings
from grounding.match_users import match_users_for_crisis

CRISIS_ID = UUID("31111111-1111-4111-8111-111111111101")


@pytest.fixture
def ensure_prerequisites():
    if not settings.resolved_gemini_api_key:
        pytest.skip("GEMINI_API_KEY not configured")

    from db import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM ansar_users")
            if cur.fetchone()["n"] == 0:
                pytest.skip("Ansar users not seeded")

            cur.execute(
                """
                SELECT id FROM grounding_results
                WHERE crisis_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (str(CRISIS_ID),),
            )
            if not cur.fetchone():
                pytest.skip("Crisis not grounded — run POST /ground first")


def test_match_users_real_gemini_and_cache(ensure_prerequisites):
    """Run real Gemini matching, persist to DB, then verify cache hit."""
    result = asyncio.run(match_users_for_crisis(CRISIS_ID, force=True))

    assert result["has_matches"] is True
    assert len(result["matched_users"]) >= 1
    assert result["matched_users"][0]["is_relevant"] is True
    assert result.get("cached") is not True
    assert result["elapsed_seconds"] > 0

    cached = asyncio.run(match_users_for_crisis(CRISIS_ID, force=False))
    assert cached.get("cached") is True
    assert cached["elapsed_seconds"] == 0
    assert len(cached["matched_users"]) == len(result["matched_users"])
    assert cached["matched_users"][0]["ansar_id"] == result["matched_users"][0]["ansar_id"]
