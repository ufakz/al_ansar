"""Per-task Ansar matcher: skills + geo filter, scored ranking, top-3 per task."""

from __future__ import annotations

import logging
import math
import time
from typing import Any
from uuid import UUID

from db import get_connection
from grounding.retrieve import fetch_crisis, fetch_users_for_crisis

log = logging.getLogger("matcher")

REMOTE_SKILLS = frozenset({"remote_research", "foi_request"})
MAX_DISTANCE_KM = 500
TOP_N = 3
TRUST_WEIGHT = {"trusted": 1.0, "org_verified": 0.7, "unverified": 0.4}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _skill_overlap(required: list[str], user_skills: list[str]) -> float:
    if not required:
        return 0.0
    overlap = set(required) & set(user_skills)
    return len(overlap) / len(required)


def _is_remote_task(required_skills: list[str]) -> bool:
    if not required_skills:
        return False
    return set(required_skills) <= REMOTE_SKILLS


def _passes_geo(crisis: dict, user: dict, required_skills: list[str]) -> bool:
    if _is_remote_task(required_skills):
        return True

    crisis_lat, crisis_lng = crisis.get("lat"), crisis.get("lng")
    user_lat, user_lng = user.get("lat"), user.get("lng")

    if crisis_lat is not None and crisis_lng is not None and user_lat is not None and user_lng is not None:
        return _haversine_km(crisis_lat, crisis_lng, user_lat, user_lng) <= MAX_DISTANCE_KM

    return True


def _score_candidate(required_skills: list[str], user: dict) -> float:
    overlap = _skill_overlap(required_skills, user.get("skills") or [])
    if overlap == 0:
        return 0.0
    trust = TRUST_WEIGHT.get(user.get("trust_tier", "unverified"), 0.4)
    return 0.7 * overlap + 0.3 * trust


def _get_tasks_for_crisis(crisis_id: UUID) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, crisis_id, title, description, required_skills,
                       task_type, status, legal_review_needed, created_at
                FROM tasks
                WHERE crisis_id = %s
                ORDER BY created_at ASC
                """,
                (str(crisis_id),),
            )
            return cur.fetchall()


def _get_existing_matches(crisis_id: UUID) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    m.id, m.task_id, m.ansar_id, m.score, m.rank,
                    m.notified_at, m.created_at,
                    t.title AS task_title, t.crisis_id, t.status AS task_status,
                    u.name, u.skills, u.trust_tier, u.languages
                FROM matches m
                JOIN tasks t ON t.id = m.task_id
                JOIN ansar_users u ON u.id = m.ansar_id
                WHERE t.crisis_id = %s
                ORDER BY t.created_at ASC, m.rank ASC
                """,
                (str(crisis_id),),
            )
            return cur.fetchall()


def _serialize_match(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "task_id": str(row["task_id"]),
        "ansar_id": str(row["ansar_id"]),
        "score": round(float(row["score"]), 3) if row["score"] is not None else 0,
        "rank": row["rank"],
        "notified_at": row["notified_at"].isoformat() if row.get("notified_at") else None,
        "created_at": row["created_at"].isoformat(),
        "task_title": row.get("task_title"),
        "task_status": row.get("task_status"),
        "name": row.get("name"),
        "skills": row.get("skills") or [],
        "trust_tier": row.get("trust_tier"),
        "languages": row.get("languages") or [],
    }


def _group_matches_by_task(matches: list[dict]) -> list[dict]:
    by_task: dict[str, dict] = {}
    for m in matches:
        tid = m["task_id"]
        if tid not in by_task:
            by_task[tid] = {
                "task_id": tid,
                "task_title": m.get("task_title"),
                "task_status": m.get("task_status"),
                "matches": [],
            }
        by_task[tid]["matches"].append(m)
    return list(by_task.values())


def list_task_matches(crisis_id: UUID | None = None) -> list[dict]:
    if crisis_id:
        rows = _get_existing_matches(crisis_id)
    else:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        m.id, m.task_id, m.ansar_id, m.score, m.rank,
                        m.notified_at, m.created_at,
                        t.title AS task_title, t.crisis_id, t.status AS task_status,
                        u.name, u.skills, u.trust_tier, u.languages
                    FROM matches m
                    JOIN tasks t ON t.id = m.task_id
                    JOIN ansar_users u ON u.id = m.ansar_id
                    ORDER BY m.created_at DESC
                    """
                )
                rows = cur.fetchall()
    return [_serialize_match(r) for r in rows]


def match_tasks_for_crisis(crisis_id: UUID, force: bool = False) -> dict[str, Any]:
    t_start = time.perf_counter()

    tasks = _get_tasks_for_crisis(crisis_id)
    if not tasks:
        raise ValueError(
            f"No tasks for crisis {crisis_id}. Run POST /decompose/{crisis_id} first."
        )

    existing = _get_existing_matches(crisis_id)
    if existing and not force:
        serialized = [_serialize_match(r) for r in existing]
        log.info("[task-match] cache hit for %s — %d matches", crisis_id, len(serialized))
        return {
            "crisis_id": str(crisis_id),
            "task_count": len(tasks),
            "match_count": len(serialized),
            "tasks": _group_matches_by_task(serialized),
            "summary": f"Found {len(serialized)} task matches across {len(tasks)} tasks.",
            "cached": True,
            "elapsed_seconds": 0,
        }

    crisis = fetch_crisis(crisis_id)
    if not crisis:
        raise ValueError(f"Crisis not found: {crisis_id}")

    candidates = fetch_users_for_crisis(crisis.get("country_iso"))
    if not candidates:
        raise RuntimeError("Ansar user catalog is empty — run seed_users.py first")

    task_ids = [str(t["id"]) for t in tasks]

    with get_connection() as conn:
        with conn.cursor() as cur:
            if force:
                cur.execute(
                    """
                    DELETE FROM matches
                    WHERE task_id = ANY(%s::uuid[])
                    """,
                    (task_ids,),
                )
                cur.execute(
                    """
                    UPDATE tasks SET status = 'open'
                    WHERE crisis_id = %s
                    """,
                    (str(crisis_id),),
                )

            all_inserted: list[dict] = []

            for task in tasks:
                required = task.get("required_skills") or []
                ranked: list[tuple[dict, float]] = []

                for user in candidates:
                    if not set(required) & set(user.get("skills") or []):
                        continue
                    if not _passes_geo(crisis, user, required):
                        continue
                    score = _score_candidate(required, user)
                    if score > 0:
                        ranked.append((user, score))

                ranked.sort(key=lambda x: x[1], reverse=True)
                top = ranked[:TOP_N]

                for rank, (user, score) in enumerate(top, start=1):
                    cur.execute(
                        """
                        INSERT INTO matches (task_id, ansar_id, score, rank)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id, created_at
                        """,
                        (str(task["id"]), user["ansar_id"], score, rank),
                    )
                    row = cur.fetchone()
                    all_inserted.append({
                        "id": str(row["id"]),
                        "task_id": str(task["id"]),
                        "task_title": task["title"],
                        "task_status": "matched",
                        "ansar_id": user["ansar_id"],
                        "name": user.get("name"),
                        "skills": user.get("skills") or [],
                        "trust_tier": user.get("trust_tier"),
                        "languages": user.get("languages") or [],
                        "score": round(score, 3),
                        "rank": rank,
                        "notified_at": None,
                        "created_at": row["created_at"].isoformat(),
                    })

                if top:
                    cur.execute(
                        "UPDATE tasks SET status = 'matched' WHERE id = %s",
                        (str(task["id"]),),
                    )

        conn.commit()

    elapsed = time.perf_counter() - t_start
    log.info(
        "[task-match] done in %.1fs — %d matches for %d tasks",
        elapsed, len(all_inserted), len(tasks),
    )

    return {
        "crisis_id": str(crisis_id),
        "task_count": len(tasks),
        "match_count": len(all_inserted),
        "tasks": _group_matches_by_task(all_inserted),
        "summary": (
            f"Matched {len(all_inserted)} helpers across {len(tasks)} tasks "
            f"(top {TOP_N} per task)."
        ),
        "elapsed_seconds": round(elapsed, 2),
    }
