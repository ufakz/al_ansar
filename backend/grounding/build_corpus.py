"""Ingest legal PDFs and inline sources into Postgres."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from uuid import UUID

import fitz

from db import get_connection
from grounding.chunkers import chunk_document, _estimate_tokens

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if os.environ.get("AL_ANSAR_ROOT"):
    PROJECT_ROOT = Path(os.environ["AL_ANSAR_ROOT"])
MANIFEST_PATH = PROJECT_ROOT / "data" / "legal" / "manifest.json"


def _load_manifest() -> list[dict]:
    with MANIFEST_PATH.open(encoding="utf-8") as f:
        return json.load(f)["sources"]


def _extract_pdf_text(file_path: Path) -> str:
    doc = fitz.open(file_path)
    return "".join(page.get_text() for page in doc)


def _resolve_path(entry: dict) -> Path | None:
    file_path = entry.get("file_path")
    if not file_path:
        return None
    path = PROJECT_ROOT / file_path
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    return path


def _upsert_source(cur, entry: dict) -> UUID:
    source_id = UUID(entry["id"])
    cur.execute(
        """
        INSERT INTO legal_sources (
            id, title, jurisdiction, source_type, url, celex_or_ref,
            slug, file_path, topic_tags, leverage_routes
        ) VALUES (
            %(id)s, %(title)s, %(jurisdiction)s, %(source_type)s, %(url)s, %(celex_or_ref)s,
            %(slug)s, %(file_path)s, %(topic_tags)s, %(leverage_routes)s::jsonb
        )
        ON CONFLICT (slug) DO UPDATE SET
            title = EXCLUDED.title,
            jurisdiction = EXCLUDED.jurisdiction,
            source_type = EXCLUDED.source_type,
            url = EXCLUDED.url,
            celex_or_ref = EXCLUDED.celex_or_ref,
            file_path = EXCLUDED.file_path,
            topic_tags = EXCLUDED.topic_tags,
            leverage_routes = EXCLUDED.leverage_routes
        RETURNING id
        """,
        {
            "id": str(source_id),
            "title": entry["title"],
            "jurisdiction": entry["jurisdiction"],
            "source_type": entry["source_type"],
            "url": entry["url"],
            "celex_or_ref": entry.get("celex_or_ref"),
            "slug": entry["slug"],
            "file_path": entry.get("file_path"),
            "topic_tags": entry.get("topic_tags", []),
            "leverage_routes": json.dumps(entry.get("leverage_routes", [])),
        },
    )
    return cur.fetchone()["id"]


def _replace_chunks(cur, source_id: UUID, entry: dict, chunks) -> int:
    cur.execute("DELETE FROM legal_chunks WHERE source_id = %s", (str(source_id),))
    topic_tags = entry.get("topic_tags", [])
    inserted = 0
    for chunk in chunks:
        cur.execute(
            """
            INSERT INTO legal_chunks (
                source_id, chunk_text, article_ref, topic_tags, chunk_index, token_count
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                str(source_id),
                chunk.text,
                chunk.article_ref,
                topic_tags,
                chunk.chunk_index,
                _estimate_tokens(chunk.text),
            ),
        )
        inserted += 1
    return inserted


def ingest_source(entry: dict) -> tuple[str, int]:
    inline_text = entry.get("inline_text")
    pdf_path = _resolve_path(entry) if entry.get("file_path") else None

    if inline_text:
        text = inline_text
    elif pdf_path:
        text = _extract_pdf_text(pdf_path)
    else:
        raise ValueError(f"Source {entry['slug']} has no text or PDF")

    chunks = chunk_document(
        text,
        strategy=entry.get("chunk_strategy", "paragraph"),
        max_chunks=entry.get("max_chunks"),
    )
    if not chunks:
        raise ValueError(f"No chunks produced for {entry['slug']}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            source_id = _upsert_source(cur, entry)
            count = _replace_chunks(cur, source_id, entry, chunks)
        conn.commit()

    return entry["slug"], count


def build_corpus() -> dict[str, int]:
    results: dict[str, int] = {}
    for entry in _load_manifest():
        slug, count = ingest_source(entry)
        results[slug] = count
    return results


def main() -> None:
    try:
        results = build_corpus()
    except Exception as exc:
        print(f"Corpus build failed: {exc}", file=sys.stderr)
        sys.exit(1)

    total = sum(results.values())
    print(f"Ingested {total} chunks from {len(results)} sources:")
    for slug, count in results.items():
        print(f"  {slug}: {count} chunks")


if __name__ == "__main__":
    main()
