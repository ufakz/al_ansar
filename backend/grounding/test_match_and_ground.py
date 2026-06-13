"""Integration test for match_and_ground with mocked Gemini."""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from grounding.match_and_ground import match_and_ground
from schemas.grounding import BatchResult, ChunkMatch

CRISIS_ID = UUID("31111111-1111-4111-8111-111111111101")


@pytest.fixture
def sample_chunk_from_db():
    from db import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id::text AS chunk_id, c.chunk_text, c.article_ref,
                       s.id::text AS source_id, s.title, s.url
                FROM legal_chunks c
                JOIN legal_sources s ON s.id = c.source_id
                WHERE s.slug = 'fin-non-discrimination-act-1325-2014'
                  AND c.article_ref = 'Section 7'
                LIMIT 1
                """
            )
            row = cur.fetchone()
    if not row:
        pytest.skip("Legal corpus not seeded")
    return row


def test_match_and_ground_with_mock_gemini(sample_chunk_from_db):
    chunk = sample_chunk_from_db
    excerpt = chunk["chunk_text"][:80].strip()

    mock_batch_result = BatchResult(
        matches=[
            ChunkMatch(
                chunk_id=chunk["chunk_id"],
                source_id=chunk["source_id"],
                title=chunk["title"],
                article_ref=chunk["article_ref"],
                url=chunk["url"],
                relevance_score=9,
                covers_crisis=True,
                reason="Directly addresses discrimination in employment",
                excerpt=excerpt,
            )
        ]
    )

    with patch(
        "grounding.match_and_ground._evaluate_batch",
        new=AsyncMock(return_value=mock_batch_result),
    ):
        result = asyncio.run(match_and_ground(CRISIS_ID))

    assert result["has_legal_support"] is True
    assert len(result["matched_chunks"]) >= 1
    assert result["matched_chunks"][0]["excerpt"] in chunk["chunk_text"]
