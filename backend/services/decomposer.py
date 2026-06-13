"""LLM-based task decomposition from a grounded crisis."""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from uuid import UUID

from langchain_google_genai import ChatGoogleGenerativeAI

from config import settings
from db import get_connection
from grounding.retrieve import fetch_crisis, fetch_grounding
from schemas.tasks import SKILL_VOCABULARY, DecomposeResult, TaskDraft

log = logging.getLogger("decomposer")

MODEL = "gemini-3.5-flash"
MIN_TASKS = 3
MAX_TASKS = 6


def _build_prompt(crisis: dict, grounding: dict) -> str:
    compact_chunks = [
        {
            "title": c.get("title"),
            "article_ref": c.get("article_ref"),
            "url": c.get("url"),
            "reason": c.get("reason"),
            "excerpt": c.get("excerpt"),
            "leverage_routes": c.get("leverage_routes") or [],
        }
        for c in (grounding.get("matched_chunks") or [])[:10]
    ]

    return f"""You are a crisis response coordinator. Decompose this grounded crisis into actionable tasks for volunteer helpers (Ansar).

Rules:
1. Produce between {MIN_TASKS} and {MAX_TASKS} tasks.
2. Each task must use required_skills ONLY from this vocabulary: {json.dumps(SKILL_VOCABULARY)}
3. Derive tasks from the crisis context and legal grounding — do not invent legal provisions.
4. Where a task maps to an institutional action (ombudsman, FOI portal, legal aid), set leverage_route_title and leverage_route_url from the matched chunk leverage_routes or URLs provided. Do not invent URLs.
5. task_type should be one of: legal, advocacy, research, logistics, support, translation, fundraising.
6. Tasks should be concrete and actionable (who does what).

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

Return a DecomposeResult with tasks and a brief summary of the decomposition plan."""


def _get_llm() -> ChatGoogleGenerativeAI:
    if not settings.resolved_gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return ChatGoogleGenerativeAI(
        model=MODEL,
        google_api_key=settings.resolved_gemini_api_key,
        temperature=0,
    )


def _get_cached_tasks(crisis_id: UUID) -> dict[str, Any] | None:
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
            rows = cur.fetchall()
    if not rows:
        return None

    tasks = [_serialize_task(row) for row in rows]
    return {
        "crisis_id": str(crisis_id),
        "task_count": len(tasks),
        "tasks": tasks,
        "summary": f"Found {len(tasks)} existing tasks for this crisis.",
        "cached": True,
        "legal_review_needed": any(t.get("legal_review_needed") for t in tasks),
        "elapsed_seconds": 0,
    }


def _serialize_task(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "crisis_id": str(row["crisis_id"]),
        "title": row["title"],
        "description": row["description"],
        "required_skills": row["required_skills"] or [],
        "task_type": row["task_type"],
        "status": row["status"],
        "legal_review_needed": row.get("legal_review_needed", False),
        "created_at": row["created_at"].isoformat(),
    }


def _validate_skills(skills: list[str]) -> list[str]:
    valid = set(SKILL_VOCABULARY)
    return [s for s in skills if s in valid]


async def decompose_crisis(crisis_id: UUID, force: bool = False) -> dict[str, Any]:
    t_start = time.perf_counter()

    if not force:
        cached = _get_cached_tasks(crisis_id)
        if cached:
            log.info("[decompose] cache hit for %s", crisis_id)
            return cached

    grounding = fetch_grounding(crisis_id)
    if not grounding:
        raise ValueError(
            f"Crisis not grounded: {crisis_id}. Run POST /ground/{crisis_id} first."
        )

    crisis = fetch_crisis(crisis_id)
    if not crisis:
        raise ValueError(f"Crisis not found: {crisis_id}")

    legal_review_needed = not grounding.get("has_legal_support")

    log.info("[decompose] crisis: %s (legal_review_needed=%s)", crisis.get("title"), legal_review_needed)

    llm = _get_llm()
    structured_llm = llm.with_structured_output(DecomposeResult)
    result = await structured_llm.ainvoke(_build_prompt(crisis, grounding))

    if not isinstance(result, DecomposeResult):
        result = DecomposeResult.model_validate(result)

    drafts = result.tasks[:MAX_TASKS]
    if len(drafts) < MIN_TASKS:
        log.warning("[decompose] LLM returned %d tasks (min %d)", len(drafts), MIN_TASKS)

    if force:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tasks WHERE crisis_id = %s", (str(crisis_id),))
            conn.commit()

    inserted: list[dict] = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            for draft in drafts:
                description = draft.description
                if draft.leverage_route_title and draft.leverage_route_url:
                    description = (
                        f"{description}\n\nLeverage route: {draft.leverage_route_title} — "
                        f"{draft.leverage_route_url}"
                    ).strip()
                if legal_review_needed:
                    description = f"[LEGAL REVIEW NEEDED] {description}"

                skills = _validate_skills(draft.required_skills)
                cur.execute(
                    """
                    INSERT INTO tasks (
                        crisis_id, title, description, required_skills,
                        task_type, status, legal_review_needed
                    ) VALUES (%s, %s, %s, %s, %s, 'open', %s)
                    RETURNING id, crisis_id, title, description, required_skills,
                              task_type, status, legal_review_needed, created_at
                    """,
                    (
                        str(crisis_id),
                        draft.title,
                        description,
                        skills,
                        draft.task_type or "general",
                        legal_review_needed,
                    ),
                )
                inserted.append(_serialize_task(cur.fetchone()))
        conn.commit()

    elapsed = time.perf_counter() - t_start
    log.info("[decompose] created %d tasks in %.1fs", len(inserted), elapsed)

    return {
        "crisis_id": str(crisis_id),
        "task_count": len(inserted),
        "tasks": inserted,
        "summary": result.summary or f"Decomposed into {len(inserted)} actionable tasks.",
        "legal_review_needed": legal_review_needed,
        "elapsed_seconds": round(elapsed, 2),
    }
