"""LLM-based legal grounding: batch-parallel chunk comparison against a crisis."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from uuid import UUID

from langchain_google_genai import ChatGoogleGenerativeAI

from config import settings
from db import get_connection
from grounding.retrieve import fetch_chunks_for_crisis, fetch_crisis
from schemas.grounding import BatchResult, ChunkMatch

log = logging.getLogger("grounding")

MODEL = "gemini-3.5-flash"
BATCH_SIZE = 5


def _build_batch_prompt(crisis: dict, batch: list[dict]) -> str:
    compact = [
        {
            "chunk_id": c["chunk_id"],
            "source_id": c["source_id"],
            "title": c.get("title"),
            "article_ref": c.get("article_ref"),
            "jurisdiction": c.get("jurisdiction"),
            "text": c.get("text"),
            "url": c.get("url"),
            "leverage_routes": c.get("leverage_routes") or [],
        }
        for c in batch
    ]

    return f"""You are a legal grounding assistant. For each legal chunk below, determine whether it covers or supports the given crisis.

Rules:
1. Use ONLY the provided chunks — no outside legal knowledge.
2. For each chunk, return a relevance score (0-10) and whether it covers the crisis.
3. If a chunk is relevant (score >= 5), provide a verbatim excerpt from its text field.
4. Every chunk_id in your response MUST come from the batch below.

CRISIS:
- title: {crisis.get("title")}
- summary: {crisis.get("summary")}
- country_iso: {crisis.get("country_iso")}
- tags: {crisis.get("tags") or []}
- type: {crisis.get("type")}

LEGAL CHUNKS:
{json.dumps(compact, indent=2)}

Return your assessment for every chunk in this batch."""


def _get_llm() -> ChatGoogleGenerativeAI:
    if not settings.resolved_gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return ChatGoogleGenerativeAI(
        model=MODEL,
        google_api_key=settings.resolved_gemini_api_key,
        temperature=0,
    )


async def _evaluate_batch(
    crisis: dict,
    batch: list[dict],
    batch_idx: int,
    llm: ChatGoogleGenerativeAI,
) -> BatchResult:
    log.info("[batch %d] sending %d chunks to LLM", batch_idx, len(batch))
    t0 = time.perf_counter()

    try:
        structured_llm = llm.with_structured_output(BatchResult)
        prompt = _build_batch_prompt(crisis, batch)
        result = await structured_llm.ainvoke(prompt)

        elapsed = time.perf_counter() - t0
        if not isinstance(result, BatchResult):
            result = BatchResult.model_validate(result)

        relevant = [m for m in result.matches if m.covers_crisis]
        log.info(
            "[batch %d] done in %.1fs — %d/%d chunks relevant",
            batch_idx, elapsed, len(relevant), len(batch),
        )
        return result
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        log.error("[batch %d] failed in %.1fs: %s", batch_idx, elapsed, exc)
        return BatchResult()


def _rank_and_collect(results: list[BatchResult]) -> list[dict]:
    all_matches: list[ChunkMatch] = []
    for r in results:
        all_matches.extend(r.matches)

    all_matches.sort(key=lambda m: m.relevance_score, reverse=True)
    return [m.model_dump() for m in all_matches if m.covers_crisis]


def _get_cached(crisis_id: UUID) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, crisis_id, has_legal_support, summary,
                       citations, leverage_routes, created_at
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
        "cached": True,
        "elapsed_seconds": 0,
        "created_at": row["created_at"].isoformat(),
    }


async def match_and_ground(crisis_id: UUID, force: bool = False) -> dict[str, Any]:
    t_start = time.perf_counter()

    # 0. Return cached result if available (instant for demos)
    if not force:
        cached = _get_cached(crisis_id)
        if cached:
            log.info("[ground] cache hit for %s (%.3fs)", crisis_id, time.perf_counter() - t_start)
            return cached

    # 1. Fetch crisis
    log.info("[ground] fetching crisis %s", crisis_id)
    crisis = fetch_crisis(crisis_id)
    if not crisis:
        raise ValueError(f"Crisis not found: {crisis_id}")
    log.info("[ground] crisis: %s (%s)", crisis.get("title"), crisis.get("country_iso"))

    # 2. Fetch legal chunks
    log.info("[ground] fetching legal chunks for jurisdiction")
    catalog = fetch_chunks_for_crisis(crisis.get("country_iso"))
    if not catalog:
        raise RuntimeError("Legal corpus is empty — run build_corpus.py first")
    log.info("[ground] loaded %d chunks (total chars: %d)", len(catalog), sum(len(c.get("text", "")) for c in catalog))

    # 3. Split into batches and send to LLM in parallel
    batches = [catalog[i : i + BATCH_SIZE] for i in range(0, len(catalog), BATCH_SIZE)]
    log.info("[ground] split into %d batches of ~%d chunks", len(batches), BATCH_SIZE)

    llm = _get_llm()
    results: list[BatchResult] = list(
        await asyncio.gather(*[
            _evaluate_batch(crisis, batch, idx, llm)
            for idx, batch in enumerate(batches)
        ])
    )

    # 4. Rank and return
    log.info("[ground] merging results from %d batches", len(results))
    ranked_matches = _rank_and_collect(results)
    has_support = len(ranked_matches) > 0

    elapsed_total = time.perf_counter() - t_start
    log.info(
        "[ground] done in %.1fs — has_support=%s, %d matching chunks",
        elapsed_total, has_support, len(ranked_matches),
    )

    # Persist
    summary = (
        f"Found {len(ranked_matches)} relevant legal provisions."
        if has_support
        else "No relevant legal provisions found in stored corpus."
    )

    citations_json = json.dumps(ranked_matches).replace("\\u0000", "")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO grounding_results (
                    crisis_id, has_legal_support, summary, citations, leverage_routes
                ) VALUES (%s, %s, %s, %s::jsonb, %s::jsonb)
                RETURNING id, created_at
                """,
                (
                    str(crisis_id),
                    has_support,
                    summary,
                    citations_json,
                    json.dumps([]),
                ),
            )
            result_row = cur.fetchone()
        conn.commit()

    return {
        "grounding_id": str(result_row["id"]),
        "crisis_id": str(crisis_id),
        "has_legal_support": has_support,
        "summary": summary,
        "matched_chunks": ranked_matches,
        "total_chunks_evaluated": len(catalog),
        "batches": len(batches),
        "elapsed_seconds": round(elapsed_total, 2),
        "created_at": result_row["created_at"].isoformat(),
    }
