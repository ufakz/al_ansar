"""Validate LLM citations against stored legal chunks."""

from __future__ import annotations

import re
from typing import Any


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _excerpt_in_chunk(excerpt: str, chunk_text: str) -> bool:
    if excerpt in chunk_text:
        return True
    return _normalize(excerpt) in _normalize(chunk_text)


def validate_citations(
    citations: list[dict[str, Any]],
    chunks_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    for citation in citations:
        chunk_id = str(citation.get("chunk_id", ""))
        chunk = chunks_by_id.get(chunk_id)
        if not chunk:
            continue

        excerpt = citation.get("excerpt", "")
        if not excerpt or not _excerpt_in_chunk(excerpt, chunk["chunk_text"]):
            continue

        source_id = str(citation.get("source_id", ""))
        if source_id != str(chunk["source_id"]):
            continue

        url = citation.get("url", "")
        if url and url != chunk.get("url"):
            continue

        validated.append(
            {
                "source_id": str(chunk["source_id"]),
                "chunk_id": chunk_id,
                "title": citation.get("title") or chunk.get("title"),
                "article_ref": citation.get("article_ref") or chunk.get("article_ref"),
                "excerpt": excerpt,
                "url": chunk.get("url") or url,
            }
        )
    return validated


def validate_matched_chunks(
    matched_chunks: list[dict[str, Any]],
    chunks_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    for match in matched_chunks:
        chunk_id = str(match.get("chunk_id", ""))
        chunk = chunks_by_id.get(chunk_id)
        if not chunk:
            continue

        excerpt = match.get("excerpt", "")
        if excerpt and not _excerpt_in_chunk(excerpt, chunk["chunk_text"]):
            continue

        source_id = str(match.get("source_id", ""))
        if source_id != str(chunk["source_id"]):
            continue

        validated.append(
            {
                "chunk_id": chunk_id,
                "source_id": str(chunk["source_id"]),
                "relevance_score": match.get("relevance_score"),
                "match_reason": match.get("match_reason"),
                "excerpt": excerpt,
            }
        )
    return validated


def validate_leverage_routes(
    routes: list[dict[str, Any]],
    allowed_routes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    allowed_urls = {r.get("url") for r in allowed_routes if r.get("url")}
    validated: list[dict[str, Any]] = []
    for route in routes:
        url = route.get("url")
        if url and url in allowed_urls:
            validated.append(route)
    return validated
