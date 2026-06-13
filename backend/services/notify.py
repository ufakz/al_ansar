"""Telegram notifications for top-ranked task matches."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from uuid import UUID

import httpx

from config import settings
from db import get_connection
from grounding.retrieve import fetch_crisis, fetch_grounding

log = logging.getLogger("notify")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
DASHBOARD_BASE = "http://localhost:3000"


def _resolved_token() -> str:
    return settings.telegram_bot_token.strip().strip('"').strip("'")


def _resolved_test_chat_id() -> str:
    return settings.telegram_test_chat_id.strip().strip('"').strip("'")


def _is_valid_chat_id(chat_id: str) -> bool:
    return bool(chat_id) and bool(re.fullmatch(r"-?\d+", chat_id))


def send_telegram_message(chat_id: str, text: str) -> dict[str, Any]:
    token = _resolved_token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    if not _is_valid_chat_id(chat_id):
        raise ValueError(f"Invalid Telegram chat_id: {chat_id!r}")

    url = TELEGRAM_API.format(token=token)
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json={"chat_id": chat_id, "text": text})
        data = response.json()

    if not response.is_success or not data.get("ok"):
        description = data.get("description", response.text)
        raise RuntimeError(f"Telegram API error: {description}")

    return data


def _skill_overlap(required: list[str], user_skills: list[str]) -> list[str]:
    return sorted(set(required) & set(user_skills))


def build_notification_text(
    *,
    crisis_title: str,
    crisis_summary: str | None,
    task_title: str,
    task_description: str | None,
    helper_name: str,
    matched_skills: list[str],
    legal_excerpt: str | None,
    crisis_id: str,
) -> str:
    lines = [
        "Al-Ansar — task assignment",
        "",
        f"Crisis: {crisis_title}",
    ]
    if crisis_summary:
        lines.append(crisis_summary[:200] + ("…" if len(crisis_summary) > 200 else ""))
    lines.extend([
        "",
        f"Task: {task_title}",
    ])
    if task_description:
        lines.append(task_description[:300] + ("…" if len(task_description) > 300 else ""))
    lines.extend([
        "",
        f"Matched helper: {helper_name}",
        f"Skills: {', '.join(s.replace('_', ' ') for s in matched_skills) or '—'}",
    ])
    if legal_excerpt:
        lines.extend(["", f"Legal backing: “{legal_excerpt[:200]}{'…' if len(legal_excerpt) > 200 else ''}”"])
    lines.extend([
        "",
        f"View crisis: {DASHBOARD_BASE}/crisis/{crisis_id}",
    ])
    return "\n".join(lines)


def _fetch_top_match(crisis_id: UUID, force: bool) -> dict | None:
    notified_clause = "" if force else "AND m.notified_at IS NULL"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    m.id, m.task_id, m.ansar_id, m.score, m.rank, m.notified_at,
                    t.title AS task_title, t.description AS task_description,
                    t.required_skills,
                    c.id AS crisis_id, c.title AS crisis_title, c.summary AS crisis_summary,
                    u.name AS helper_name, u.skills AS helper_skills,
                    u.telegram_chat_id
                FROM matches m
                JOIN tasks t ON t.id = m.task_id
                JOIN crisis_objects c ON c.id = t.crisis_id
                JOIN ansar_users u ON u.id = m.ansar_id
                WHERE t.crisis_id = %s AND m.rank = 1
                {notified_clause}
                ORDER BY m.score DESC
                LIMIT 1
                """,
                (str(crisis_id),),
            )
            return cur.fetchone()


def _count_skipped_matches(crisis_id: UUID, exclude_match_id: str | None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if exclude_match_id:
                cur.execute(
                    """
                    SELECT COUNT(*) AS n
                    FROM matches m
                    JOIN tasks t ON t.id = m.task_id
                    WHERE t.crisis_id = %s AND m.id != %s::uuid
                    """,
                    (str(crisis_id), exclude_match_id),
                )
            else:
                cur.execute(
                    """
                    SELECT COUNT(*) AS n
                    FROM matches m
                    JOIN tasks t ON t.id = m.task_id
                    WHERE t.crisis_id = %s
                    """,
                    (str(crisis_id),),
                )
            row = cur.fetchone()
            return int(row["n"]) if row else 0


def _record_notification(
    match_id: str,
    status: str,
    payload: dict[str, Any],
    *,
    mark_notified: bool,
) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if mark_notified:
                cur.execute(
                    "UPDATE matches SET notified_at = NOW() WHERE id = %s",
                    (match_id,),
                )
            cur.execute(
                """
                INSERT INTO notifications (match_id, channel, status, payload)
                VALUES (%s, %s, %s, %s::jsonb)
                """,
                (match_id, "telegram", status, json.dumps(payload)),
            )
        conn.commit()


def notify_matches_for_crisis(crisis_id: UUID, force: bool = False) -> dict[str, Any]:
    t_start = time.perf_counter()

    crisis = fetch_crisis(crisis_id)
    if not crisis:
        raise ValueError(f"Crisis not found: {crisis_id}")

    match = _fetch_top_match(crisis_id, force=force)
    if not match:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) AS n
                    FROM matches m
                    JOIN tasks t ON t.id = m.task_id
                    WHERE t.crisis_id = %s
                    """,
                    (str(crisis_id),),
                )
                total = int(cur.fetchone()["n"])
        if total == 0:
            raise ValueError(
                f"No task matches for crisis {crisis_id}. Run POST /match/tasks/{crisis_id} first."
            )
        return {
            "crisis_id": str(crisis_id),
            "sent": 0,
            "skipped": total,
            "failed": 0,
            "cached": True,
            "summary": "Top match already notified. Use ?force=true to resend.",
            "elapsed_seconds": 0,
        }

    chat_id = _resolved_test_chat_id() or (match.get("telegram_chat_id") or "")
    match_id = str(match["id"])

    grounding = fetch_grounding(crisis_id)
    legal_excerpt = None
    if grounding and grounding.get("matched_chunks"):
        chunk = grounding["matched_chunks"][0]
        legal_excerpt = chunk.get("excerpt") or chunk.get("title")

    required = match.get("required_skills") or []
    helper_skills = match.get("helper_skills") or []
    matched_skills = _skill_overlap(required, helper_skills)

    text = build_notification_text(
        crisis_title=match["crisis_title"],
        crisis_summary=match.get("crisis_summary"),
        task_title=match["task_title"],
        task_description=match.get("task_description"),
        helper_name=match["helper_name"],
        matched_skills=matched_skills,
        legal_excerpt=legal_excerpt,
        crisis_id=str(crisis_id),
    )

    skipped = _count_skipped_matches(crisis_id, exclude_match_id=match_id)

    try:
        tg_result = send_telegram_message(chat_id, text)
        payload = {
            "chat_id": chat_id,
            "helper_name": match["helper_name"],
            "task_title": match["task_title"],
            "message_id": tg_result.get("result", {}).get("message_id"),
        }
        _record_notification(match_id, "sent", payload, mark_notified=True)
        elapsed = time.perf_counter() - t_start
        log.info(
            "[notify] sent to %s for match %s (helper %s) in %.1fs",
            chat_id, match_id, match["helper_name"], elapsed,
        )
        return {
            "crisis_id": str(crisis_id),
            "match_id": match_id,
            "chat_id": chat_id,
            "helper_name": match["helper_name"],
            "task_title": match["task_title"],
            "sent": 1,
            "skipped": skipped,
            "failed": 0,
            "cached": False,
            "summary": f"Notified {match['helper_name']} for “{match['task_title']}”.",
            "elapsed_seconds": round(elapsed, 2),
        }
    except Exception as exc:
        payload = {
            "chat_id": chat_id,
            "helper_name": match["helper_name"],
            "task_title": match["task_title"],
            "error": str(exc),
        }
        _record_notification(match_id, "failed", payload, mark_notified=False)
        log.error("[notify] failed for match %s: %s", match_id, exc)
        raise RuntimeError(str(exc)) from exc
