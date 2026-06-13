"""Optional pgvector pre-filter when catalog exceeds context budget."""

from __future__ import annotations

from db import get_connection
from grounding.jurisdiction import jurisdictions_for_country

TOP_K = 40


def prefilter_by_embedding(
    country_iso: str | None,
    query_embedding: list[float],
    limit: int = TOP_K,
) -> list[str]:
    """Return chunk IDs ranked by cosine similarity. Requires populated embeddings."""
    jurisdictions = jurisdictions_for_country(country_iso)
    vector_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id::text
                FROM legal_chunks c
                JOIN legal_sources s ON s.id = c.source_id
                WHERE s.jurisdiction = ANY(%s)
                  AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                (jurisdictions, vector_literal, limit),
            )
            return [row["id"] for row in cur.fetchall()]
