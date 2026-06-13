#!/usr/bin/env python3
"""Local test: fetch crisis + chunks via docker psql, run Gemini matching in venv."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from uuid import UUID

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))


def _psql_json(query: str) -> list | dict | None:
    cmd = [
        "docker", "exec", "alansar-postgres",
        "psql", "-U", "alansar", "-d", "alansar", "-t", "-A", "-c", query,
    ]
    raw = subprocess.check_output(cmd, text=True).strip()
    if not raw or raw == "null":
        return None
    return json.loads(raw)


def fetch_crisis_local(crisis_id: str) -> dict | None:
    row = _psql_json(
        f"""
        SELECT row_to_json(c) FROM (
          SELECT id, title, summary, country_iso, tags, type, severity
          FROM crisis_objects WHERE id = '{crisis_id}'
        ) c
        """
    )
    return row


def fetch_catalog_local(country_iso: str | None) -> list[dict]:
    if country_iso == "FIN":
        jurisdictions = ["FIN", "EU", "ECHR", "EVIDENCE"]
    else:
        jurisdictions = ["EU", "ECHR", "EVIDENCE"]
    jurs = ",".join(f"'{j}'" for j in jurisdictions)

    rows = _psql_json(
        f"""
        SELECT COALESCE(json_agg(row ORDER BY jurisdiction, title, chunk_index), '[]'::json)
        FROM (
          SELECT
            c.id::text AS chunk_id,
            c.chunk_text AS text,
            c.article_ref,
            c.chunk_index,
            s.id::text AS source_id,
            s.title,
            s.url,
            s.jurisdiction,
            s.leverage_routes
          FROM legal_chunks c
          JOIN legal_sources s ON s.id = c.source_id
          WHERE s.jurisdiction IN ({jurs})
          ORDER BY s.jurisdiction, s.title, c.chunk_index
        ) row
        """
    )
    return rows or []


def main() -> None:
    crisis_id = sys.argv[1] if len(sys.argv) > 1 else "31111111-1111-4111-8111-111111111101"

    crisis = fetch_crisis_local(crisis_id)
    if not crisis:
        print(f"Crisis not found: {crisis_id}", file=sys.stderr)
        sys.exit(1)

    catalog = fetch_catalog_local(crisis.get("country_iso"))
    print(f"Crisis: {crisis['title']}")
    print(f"Country: {crisis.get('country_iso')} | Chunks in catalog: {len(catalog)}")
    print("Calling Gemini (gemini-2.5-flash)...\n")

    from grounding.citation_validator import validate_citations, validate_leverage_routes, validate_matched_chunks
    from grounding.match_and_ground import _allowed_routes, _call_gemini, _catalog_lookup

    raw = _call_gemini(crisis, catalog)
    chunks_by_id = _catalog_lookup(catalog)

    validated_citations = validate_citations(raw.get("citations") or [], chunks_by_id)
    validated_matches = validate_matched_chunks(raw.get("matched_chunks") or [], chunks_by_id)
    validated_routes = validate_leverage_routes(
        raw.get("leverage_routes") or [],
        _allowed_routes(catalog),
    )

    has_legal_support = bool(validated_citations) and raw.get("has_legal_support", False)
    result = {
        "crisis_id": crisis_id,
        "has_legal_support": has_legal_support,
        "confidence": raw.get("confidence"),
        "summary": raw.get("summary"),
        "insufficient_evidence": not validated_citations,
        "matched_chunks": validated_matches,
        "citations": validated_citations,
        "leverage_routes": validated_routes,
    }

    print(json.dumps(result, indent=2))
    print(f"\nValidated citations: {len(validated_citations)}")
    print(f"Leverage routes: {len(validated_routes)}")


if __name__ == "__main__":
    main()
