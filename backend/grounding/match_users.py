"""LLM-based Ansar user matching: batch-parallel user comparison against a grounded crisis."""

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
from grounding.retrieve import fetch_crisis, fetch_grounding, fetch_users_for_crisis
from schemas.matching import UserBatchResult, UserMatch

log = logging.getLogger("matching")

MODEL = "gemini-3.5-flash"
BATCH_SIZE = 5

TRUST_TIER_WEIGHT = {"trusted": 3, "org_verified": 2, "unverified": 1}


def _build_batch_prompt(
    crisis: dict,
    grounding: dict,
    batch: list[dict],
) -> str:
    compact_users = [
        {
            "ansar_id": u["ansar_id"],
            "name": u.get("name"),
            "skills": u.get("skills") or [],
            "languages": u.get("languages") or [],
            "trust_tier": u.get("trust_tier"),
            "lat": u.get("lat"),
            "lng": u.get("lng"),
        }
        for u in batch
    ]

    compact_chunks = [
        {
            "title": c.get("title"),
            "article_ref": c.get("article_ref"),
            "reason": c.get("reason"),
            "excerpt": c.get("excerpt"),
        }
        for c in (grounding.get("matched_chunks") or [])[:10]
    ]

    return f"""You are an Ansar helper matching assistant. For each Ansar user below, determine whether they are relevant to help respond to the given grounded crisis.

Rules:
1. Use ONLY the provided users — do not invent helpers.
2. For each user, return a relevance score (0-10) and whether they are relevant (is_relevant=true when score >= 5).
3. If relevant, explain why citing specific skills, languages, location/geo fit, and trust_tier.
4. List matched_skills: the subset of the user's skills that apply to this crisis.
5. Every ansar_id in your response MUST come from the batch below.
6. Prefer local helpers for on-ground tasks; remote_research/foi_request skills can be remote.

CRISIS:
- title: {crisis.get("title")}
- summary: {crisis.get("summary")}
- country_iso: {crisis.get("country_iso")}
- tags: {crisis.get("tags") or []}
- type: {crisis.get("type")}
- severity: {crisis.get("severity")}

LEGAL GROUNDING:
- has_legal_support: {grounding.get("has_legal_support")}
- summary: {grounding.get("summary")}
- matched_chunks: {json.dumps(compact_chunks, indent=2)}

ANSAR USERS:
{json.dumps(compact_users, indent=2)}

Return your assessment for every user in this batch."""


def _get_llm() -> ChatGoogleGenerativeAI:
    if not settings.resolved_gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return ChatGoogleGenerativeAI(
        model=MODEL,
        google_api_key=settings.resolved_gemini_api_key,
        temperature=0,
    )


def _enrich_match(match: UserMatch, user_lookup: dict[str, dict]) -> UserMatch:
    user = user_lookup.get(match.ansar_id)
    if not user:
        return match
    return UserMatch(
        ansar_id=match.ansar_id,
        name=user.get("name") or match.name,
        skills=user.get("skills") or match.skills,
        languages=user.get("languages") or match.languages,
        trust_tier=user.get("trust_tier") or match.trust_tier,
        relevance_score=match.relevance_score,
        is_relevant=match.is_relevant,
        reason=match.reason,
        matched_skills=match.matched_skills,
    )


def _sanitize_batch_matches(
    batch: list[dict],
    result: UserBatchResult,
) -> UserBatchResult:
    valid_ids = {u["ansar_id"] for u in batch}
    user_lookup = {u["ansar_id"]: u for u in batch}
    cleaned: list[UserMatch] = []
    for match in result.matches:
        if match.ansar_id not in valid_ids:
            continue
        cleaned.append(_enrich_match(match, user_lookup))
    return UserBatchResult(matches=cleaned)


async def _evaluate_user_batch(
    crisis: dict,
    grounding: dict,
    batch: list[dict],
    batch_idx: int,
    llm: ChatGoogleGenerativeAI,
) -> UserBatchResult:
    log.info("[user-batch %d] sending %d users to LLM", batch_idx, len(batch))
    t0 = time.perf_counter()

    try:
        structured_llm = llm.with_structured_output(UserBatchResult)
        prompt = _build_batch_prompt(crisis, grounding, batch)
        result = await structured_llm.ainvoke(prompt)

        elapsed = time.perf_counter() - t0
        if not isinstance(result, UserBatchResult):
            result = UserBatchResult.model_validate(result)

        result = _sanitize_batch_matches(batch, result)
        relevant = [m for m in result.matches if m.is_relevant]
        log.info(
            "[user-batch %d] done in %.1fs — %d/%d users relevant",
            batch_idx, elapsed, len(relevant), len(batch),
        )
        return result
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        log.error("[user-batch %d] failed in %.1fs: %s", batch_idx, elapsed, exc)
        return UserBatchResult()


def _rank_user_matches(
    results: list[UserBatchResult],
    catalog: list[dict],
) -> list[dict]:
    capacity_lookup = {u["ansar_id"]: u.get("capacity", 1) for u in catalog}
    all_matches: list[UserMatch] = []
    for r in results:
        all_matches.extend(r.matches)

    all_matches.sort(
        key=lambda m: (
            m.relevance_score,
            TRUST_TIER_WEIGHT.get(m.trust_tier, 0),
            capacity_lookup.get(m.ansar_id, 1),
        ),
        reverse=True,
    )
    return [m.model_dump() for m in all_matches if m.is_relevant]


def _get_cached_user_matches(crisis_id: UUID) -> dict[str, Any] | None:
    grounding = fetch_grounding(crisis_id)
    if not grounding:
        return None

    matched_users = grounding.get("matched_users") or []
    if not matched_users:
        return None

    return {
        "grounding_id": grounding["grounding_id"],
        "crisis_id": str(crisis_id),
        "has_matches": len(matched_users) > 0,
        "summary": (
            f"Found {len(matched_users)} relevant Ansar helpers."
            if matched_users
            else "No relevant Ansar helpers found."
        ),
        "matched_users": matched_users,
        "cached": True,
        "elapsed_seconds": 0,
        "created_at": grounding["created_at"].isoformat(),
    }


async def match_users_for_crisis(crisis_id: UUID, force: bool = False) -> dict[str, Any]:
    t_start = time.perf_counter()

    if not force:
        cached = _get_cached_user_matches(crisis_id)
        if cached:
            log.info("[match] cache hit for %s (%.3fs)", crisis_id, time.perf_counter() - t_start)
            return cached

    grounding = fetch_grounding(crisis_id)
    if not grounding:
        raise ValueError(
            f"Crisis not grounded: {crisis_id}. Run POST /ground/{crisis_id} first."
        )

    crisis = fetch_crisis(crisis_id)
    if not crisis:
        raise ValueError(f"Crisis not found: {crisis_id}")

    log.info("[match] crisis: %s (%s)", crisis.get("title"), crisis.get("country_iso"))

    catalog = fetch_users_for_crisis(crisis.get("country_iso"))
    if not catalog:
        raise RuntimeError("Ansar user catalog is empty — run seed_users.py first")

    log.info("[match] loaded %d candidate users", len(catalog))

    batches = [catalog[i : i + BATCH_SIZE] for i in range(0, len(catalog), BATCH_SIZE)]
    log.info("[match] split into %d batches of ~%d users", len(batches), BATCH_SIZE)

    llm = _get_llm()
    results: list[UserBatchResult] = list(
        await asyncio.gather(*[
            _evaluate_user_batch(crisis, grounding, batch, idx, llm)
            for idx, batch in enumerate(batches)
        ])
    )

    ranked_matches = _rank_user_matches(results, catalog)
    has_matches = len(ranked_matches) > 0

    elapsed_total = time.perf_counter() - t_start
    log.info(
        "[match] done in %.1fs — has_matches=%s, %d matching users",
        elapsed_total, has_matches, len(ranked_matches),
    )

    summary = (
        f"Found {len(ranked_matches)} relevant Ansar helpers."
        if has_matches
        else "No relevant Ansar helpers found."
    )

    matched_users_json = json.dumps(ranked_matches).replace("\\u0000", "")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE grounding_results
                SET matched_users = %s::jsonb
                WHERE id = %s
                RETURNING created_at
                """,
                (matched_users_json, grounding["grounding_id"]),
            )
            result_row = cur.fetchone()
        conn.commit()

    return {
        "grounding_id": grounding["grounding_id"],
        "crisis_id": str(crisis_id),
        "has_matches": has_matches,
        "summary": summary,
        "matched_users": ranked_matches,
        "total_users_evaluated": len(catalog),
        "batches": len(batches),
        "elapsed_seconds": round(elapsed_total, 2),
        "created_at": result_row["created_at"].isoformat(),
    }
