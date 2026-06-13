"""Tests for per-task matcher."""

from uuid import UUID

import pytest

from services.matcher import (
    _haversine_km,
    _passes_geo,
    _score_candidate,
    _skill_overlap,
    match_tasks_for_crisis,
)

CRISIS_ID = UUID("f6a7b8c9-d0e1-2345-fabc-456789012345")


def test_skill_overlap():
    assert _skill_overlap(["legal_aid", "advocacy"], ["legal_aid", "translation"]) == 0.5
    assert _skill_overlap(["legal_aid"], ["advocacy"]) == 0.0


def test_haversine_helsinki_nearby():
    # Helsinki center vs Espoo — well under 500km
    km = _haversine_km(60.1699, 24.9384, 60.2055, 24.6559)
    assert km < 50


def test_score_candidate_weights_trust():
    user_trusted = {"skills": ["legal_aid", "advocacy"], "trust_tier": "trusted"}
    user_unverified = {"skills": ["legal_aid", "advocacy"], "trust_tier": "unverified"}
    assert _score_candidate(["legal_aid"], user_trusted) > _score_candidate(["legal_aid"], user_unverified)


def test_remote_task_skips_geo():
    crisis = {"lat": 60.1699, "lng": 24.9384}
    far_user = {"lat": 21.4272, "lng": 92.0058, "skills": ["remote_research"]}
    assert _passes_geo(crisis, far_user, ["remote_research"]) is True


@pytest.fixture
def ensure_tasks_exist():
    from db import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM tasks WHERE crisis_id = %s",
                (str(CRISIS_ID),),
            )
            if cur.fetchone()["n"] == 0:
                pytest.skip("No tasks for crisis — run decompose first")


def test_match_tasks_for_crisis(ensure_tasks_exist):
    result = match_tasks_for_crisis(CRISIS_ID, force=True)
    assert result["task_count"] >= 1
    assert result["match_count"] >= 1
    assert len(result["tasks"]) >= 1
    assert result["tasks"][0]["matches"]

    cached = match_tasks_for_crisis(CRISIS_ID, force=False)
    assert cached.get("cached") is True
    assert cached["match_count"] == result["match_count"]
