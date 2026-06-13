from uuid import UUID

from db import get_connection


def list_crises(limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, summary, type, country_iso, lat, lng,
                       severity, urgency, tags, source, source_report_id, created_at
                FROM crisis_objects
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


def list_tasks(crisis_id: UUID | None = None, limit: int = 100) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if crisis_id:
                cur.execute(
                    """
                    SELECT id, crisis_id, title, description, required_skills,
                           task_type, status, legal_review_needed, created_at
                    FROM tasks
                    WHERE crisis_id = %s
                    ORDER BY created_at ASC
                    LIMIT %s
                    """,
                    (str(crisis_id), limit),
                )
            else:
                cur.execute(
                    """
                    SELECT id, crisis_id, title, description, required_skills,
                           task_type, status, legal_review_needed, created_at
                    FROM tasks
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            return cur.fetchall()


def get_crisis_summary(crisis_id: UUID) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.id, c.title, c.summary, c.type, c.country_iso, c.lat, c.lng,
                    c.severity, c.urgency, c.tags, c.source, c.source_report_id,
                    c.created_at,
                    g.id AS grounding_id,
                    g.has_legal_support,
                    jsonb_array_length(COALESCE(g.citations, '[]'::jsonb)) AS legal_match_count,
                    jsonb_array_length(COALESCE(g.matched_users, '[]'::jsonb)) AS user_match_count,
                    (SELECT COUNT(*) FROM tasks t WHERE t.crisis_id = c.id) AS task_count
                FROM crisis_objects c
                LEFT JOIN LATERAL (
                    SELECT id, has_legal_support, citations, matched_users
                    FROM grounding_results gr
                    WHERE gr.crisis_id = c.id
                    ORDER BY created_at DESC
                    LIMIT 1
                ) g ON true
                WHERE c.id = %s
                """,
                (str(crisis_id),),
            )
            return cur.fetchone()


def list_ansar(limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, skills, lat, lng, languages,
                       trust_tier, capacity, created_at
                FROM ansar_users
                ORDER BY name
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()
