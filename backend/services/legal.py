from uuid import UUID

from db import get_connection


def list_legal_sources(jurisdiction: str | None = None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if jurisdiction:
                cur.execute(
                    """
                    SELECT
                        s.id, s.title, s.jurisdiction, s.source_type, s.url,
                        s.celex_or_ref, s.slug, s.topic_tags, s.leverage_routes,
                        s.created_at,
                        COUNT(c.id) AS chunk_count
                    FROM legal_sources s
                    LEFT JOIN legal_chunks c ON c.source_id = s.id
                    WHERE s.jurisdiction = %s
                    GROUP BY s.id
                    ORDER BY s.jurisdiction, s.title
                    """,
                    (jurisdiction.upper(),),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        s.id, s.title, s.jurisdiction, s.source_type, s.url,
                        s.celex_or_ref, s.slug, s.topic_tags, s.leverage_routes,
                        s.created_at,
                        COUNT(c.id) AS chunk_count
                    FROM legal_sources s
                    LEFT JOIN legal_chunks c ON c.source_id = s.id
                    GROUP BY s.id
                    ORDER BY s.jurisdiction, s.title
                    """
                )
            return cur.fetchall()


def get_legal_source(source_id: UUID) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.id, s.title, s.jurisdiction, s.source_type, s.url,
                    s.celex_or_ref, s.slug, s.file_path, s.topic_tags,
                    s.leverage_routes, s.created_at,
                    COUNT(c.id) AS chunk_count
                FROM legal_sources s
                LEFT JOIN legal_chunks c ON c.source_id = s.id
                WHERE s.id = %s
                GROUP BY s.id
                """,
                (str(source_id),),
            )
            return cur.fetchone()


def list_legal_chunks(
    *,
    jurisdiction: str | None = None,
    source_id: UUID | None = None,
    include_text: bool = True,
) -> list[dict]:
    text_col = "c.chunk_text" if include_text else "NULL AS chunk_text"
    conditions: list[str] = []
    params: list[object] = []

    if jurisdiction:
        conditions.append("s.jurisdiction = %s")
        params.append(jurisdiction.upper())
    if source_id:
        conditions.append("c.source_id = %s")
        params.append(str(source_id))

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    c.id,
                    c.source_id,
                    {text_col},
                    c.article_ref,
                    c.topic_tags,
                    c.chunk_index,
                    c.token_count,
                    c.created_at,
                    s.title AS source_title,
                    s.jurisdiction,
                    s.url AS source_url,
                    s.slug AS source_slug
                FROM legal_chunks c
                JOIN legal_sources s ON s.id = c.source_id
                {where_clause}
                ORDER BY s.jurisdiction, s.title, c.chunk_index
                """,
                params,
            )
            return cur.fetchall()
