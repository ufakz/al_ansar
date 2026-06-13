"""Structured output schemas for legal grounding."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChunkMatch(BaseModel):
    chunk_id: str
    source_id: str = ""
    title: str | None = None
    article_ref: str | None = None
    url: str | None = None
    relevance_score: int = Field(default=0, ge=0, le=10)
    covers_crisis: bool = False
    reason: str = ""
    excerpt: str = ""


class BatchResult(BaseModel):
    matches: list[ChunkMatch] = Field(default_factory=list)
