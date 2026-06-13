from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from schemas.reports import PromoteResult, ReportCreate, ReportOut
from services import reports as report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=201)
def submit_report(payload: ReportCreate):
    return report_service.create_report(payload)


@router.get("", response_model=list[ReportOut])
def get_reports(
    status: str | None = Query(None),
    country_iso: str | None = Query(None),
):
    return report_service.list_reports(status=status, country_iso=country_iso)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: UUID):
    report = report_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/{report_id}/promote", response_model=PromoteResult)
def promote_report(report_id: UUID, triage_notes: str | None = None):
    try:
        return report_service.promote_report(report_id, triage_notes=triage_notes)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
