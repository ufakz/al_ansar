"""Load jurisdiction-filtered legal chunks and Ansar users from Postgres."""

from __future__ import annotations

from uuid import UUID

from db import get_connection
from grounding.jurisdiction import jurisdictions_for_country
from grounding.regions import MIN_POOL_SIZE, user_ids_for_country

# Rough token budget before optional vector pre-filter (~80k tokens ≈ 320k chars)
MAX_CATALOG_CHARS = 320_000


def fetch_chunks_for_crisis(country_iso: str | None) -> list[dict]:
    jurisdictions = jurisdictions_for_country(country_iso)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.id AS chunk_id,
                    c.chunk_text,
                    c.article_ref,
                    c.topic_tags,
                    c.chunk_index,
                    s.id AS source_id,
                    s.title,
                    s.url,
                    s.jurisdiction,
                    s.leverage_routes
                FROM legal_chunks c
                JOIN legal_sources s ON s.id = c.source_id
                WHERE s.jurisdiction = ANY(%s)
                ORDER BY s.jurisdiction, s.title, c.chunk_index
                """,
                (jurisdictions,),
            )
            rows = cur.fetchall()

    catalog = []
    total_chars = 0
    for row in rows:
        text = row["chunk_text"]
        if total_chars + len(text) > MAX_CATALOG_CHARS:
            break
        catalog.append(
            {
                "chunk_id": str(row["chunk_id"]),
                "source_id": str(row["source_id"]),
                "title": row["title"],
                "jurisdiction": row["jurisdiction"],
                "article_ref": row["article_ref"],
                "url": row["url"],
                "text": text,
                "leverage_routes": row["leverage_routes"] or [],
            }
        )
        total_chars += len(text)
    return catalog


def fetch_crisis(crisis_id: UUID) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, summary, country_iso, lat, lng,
                       tags, type, severity
                FROM crisis_objects
                WHERE id = %s
                """,
                (str(crisis_id),),
            )
            return cur.fetchone()


def fetch_grounding(crisis_id: UUID) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, crisis_id, has_legal_support, summary,
                       citations, leverage_routes, matched_users, created_at
                FROM grounding_results
                WHERE crisis_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (str(crisis_id),),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "grounding_id": str(row["id"]),
        "crisis_id": str(row["crisis_id"]),
        "has_legal_support": row["has_legal_support"],
        "summary": row["summary"],
        "matched_chunks": row["citations"] or [],
        "matched_users": row["matched_users"] or [],
        "created_at": row["created_at"],
    }


def _fetch_users_by_ids(user_ids: list[str]) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, skills, lat, lng, languages,
                       trust_tier, capacity
                FROM ansar_users
                WHERE id = ANY(%s::uuid[])
                ORDER BY name
                """,
                (user_ids,),
            )
            rows = cur.fetchall()
    return [
        {
            "ansar_id": str(row["id"]),
            "name": row["name"],
            "skills": row["skills"] or [],
            "lat": row["lat"],
            "lng": row["lng"],
            "languages": row["languages"] or [],
            "trust_tier": row["trust_tier"],
            "capacity": row["capacity"],
        }
        for row in rows
    ]


def _fetch_all_users() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, skills, lat, lng, languages,
                       trust_tier, capacity
                FROM ansar_users
                ORDER BY name
                """
            )
            rows = cur.fetchall()
    return [
        {
            "ansar_id": str(row["id"]),
            "name": row["name"],
            "skills": row["skills"] or [],
            "lat": row["lat"],
            "lng": row["lng"],
            "languages": row["languages"] or [],
            "trust_tier": row["trust_tier"],
            "capacity": row["capacity"],
        }
        for row in rows
    ]


def fetch_users_for_crisis(country_iso: str | None) -> list[dict]:
    candidate_ids = user_ids_for_country(country_iso)
    if candidate_ids:
        users = _fetch_users_by_ids(candidate_ids)
        if len(users) >= MIN_POOL_SIZE:
            return users
    return _fetch_all_users()
