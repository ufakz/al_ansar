"""Structured output schemas for Ansar user matching."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserMatch(BaseModel):
    ansar_id: str
    name: str | None = None
    skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    trust_tier: str = "unverified"
    relevance_score: int = Field(default=0, ge=0, le=10)
    is_relevant: bool = False
    reason: str = ""
    matched_skills: list[str] = Field(default_factory=list)


class UserBatchResult(BaseModel):
    matches: list[UserMatch] = Field(default_factory=list)
