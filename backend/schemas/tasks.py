"""Structured output schemas for task decomposition."""

from __future__ import annotations

from pydantic import BaseModel, Field

SKILL_VOCABULARY = [
    "legal_aid",
    "advocacy",
    "translation",
    "remote_research",
    "foi_request",
    "psychological_support",
    "logistics",
    "fundraising",
    "medical_triage",
    "on_ground_aid",
]


class TaskDraft(BaseModel):
    title: str
    description: str = ""
    required_skills: list[str] = Field(default_factory=list)
    task_type: str = ""
    leverage_route_title: str | None = None
    leverage_route_url: str | None = None


class DecomposeResult(BaseModel):
    tasks: list[TaskDraft] = Field(default_factory=list)
    summary: str = ""
