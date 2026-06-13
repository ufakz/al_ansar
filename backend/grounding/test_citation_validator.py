"""Tests for citation validation."""

from grounding.citation_validator import (
    validate_citations,
    validate_leverage_routes,
    validate_matched_chunks,
)


def test_validate_citations_accepts_verbatim_excerpt():
    chunks = {
        "c1": {
            "source_id": "s1",
            "chunk_text": "Section 7\nEmployer's duty to promote equality",
            "url": "https://example.fi/law",
            "title": "Test Act",
            "article_ref": "Section 7",
        }
    }
    citations = [
        {
            "source_id": "s1",
            "chunk_id": "c1",
            "excerpt": "Employer's duty to promote equality",
            "url": "https://example.fi/law",
        }
    ]
    result = validate_citations(citations, chunks)
    assert len(result) == 1
    assert result[0]["excerpt"] == "Employer's duty to promote equality"


def test_validate_citations_rejects_hallucinated_excerpt():
    chunks = {
        "c1": {
            "source_id": "s1",
            "chunk_text": "Section 7 text",
            "url": "https://example.fi/law",
        }
    }
    citations = [
        {
            "source_id": "s1",
            "chunk_id": "c1",
            "excerpt": "This text does not exist in the chunk",
            "url": "https://example.fi/law",
        }
    ]
    assert validate_citations(citations, chunks) == []


def test_validate_leverage_routes_only_allowed_urls():
    allowed = [{"route_type": "ombudsman", "body": "Ombudsman", "url": "https://allowed.fi"}]
    routes = [
        {"route_type": "ombudsman", "body": "Ombudsman", "url": "https://allowed.fi", "template_action": "File"},
        {"route_type": "foi", "body": "Fake", "url": "https://invented.fi", "template_action": "No"},
    ]
    result = validate_leverage_routes(routes, allowed)
    assert len(result) == 1
    assert result[0]["url"] == "https://allowed.fi"


def test_validate_matched_chunks():
    chunks = {
        "c1": {
            "source_id": "s1",
            "chunk_text": "religion and belief discrimination",
        }
    }
    matches = [
        {
            "chunk_id": "c1",
            "source_id": "s1",
            "relevance_score": 0.9,
            "match_reason": "Religious discrimination",
            "excerpt": "religion and belief",
        }
    ]
    result = validate_matched_chunks(matches, chunks)
    assert len(result) == 1
