from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceInput(BaseModel):
    evidence_type: str = Field(..., examples=["url", "document", "photo", "screenshot"])
    file_url: str | None = None
    description: str | None = None


class ReportCreate(BaseModel):
    narrative: str = Field(..., min_length=20)
    incident_at: datetime | None = None
    location_text: str | None = None
    lat: float | None = None
    lng: float | None = None
    country_iso: str = "FIN"
    type: str | None = None
    tags: list[str] = []
    reporter_name: str | None = None
    reporter_email: str | None = None
    reporter_phone: str | None = None
    is_anonymous: bool = True
    preferred_language: str = "en"
    evidence: list[EvidenceInput] = []


class EvidenceOut(BaseModel):
    id: UUID
    evidence_type: str
    file_url: str | None
    description: str | None
    created_at: datetime


class ReportOut(BaseModel):
    id: UUID
    narrative: str
    incident_at: datetime | None
    location_text: str | None
    lat: float | None
    lng: float | None
    country_iso: str
    type: str | None
    tags: list[str]
    is_anonymous: bool
    preferred_language: str
    status: str
    promoted_crisis_id: UUID | None
    triage_notes: str | None
    created_at: datetime
    updated_at: datetime
    evidence: list[EvidenceOut] = []


class PromoteResult(BaseModel):
    report_id: UUID
    crisis_id: UUID
    status: str
