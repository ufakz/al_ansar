import re
from uuid import UUID

from db import get_connection
from schemas.reports import EvidenceOut, PromoteResult, ReportCreate, ReportOut


def _title_from_narrative(narrative: str, location_text: str | None) -> str:
    first_sentence = re.split(r"[.!?]\s", narrative.strip())[0]
    title = first_sentence[:120].strip()
    if location_text and location_text.lower() not in title.lower():
        title = f"{title} — {location_text}"
    return title


def create_report(payload: ReportCreate) -> ReportOut:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO crisis_reports (
                    narrative, incident_at, location_text, lat, lng, country_iso,
                    type, tags, reporter_name, reporter_email, reporter_phone,
                    is_anonymous, preferred_language
                ) VALUES (
                    %(narrative)s, %(incident_at)s, %(location_text)s, %(lat)s, %(lng)s,
                    %(country_iso)s, %(type)s, %(tags)s, %(reporter_name)s,
                    %(reporter_email)s, %(reporter_phone)s, %(is_anonymous)s,
                    %(preferred_language)s
                )
                RETURNING *
                """,
                payload.model_dump(exclude={"evidence"}),
            )
            report = cur.fetchone()

            evidence_rows = []
            for item in payload.evidence:
                cur.execute(
                    """
                    INSERT INTO report_evidence (report_id, evidence_type, file_url, description)
                    VALUES (%(report_id)s, %(evidence_type)s, %(file_url)s, %(description)s)
                    RETURNING *
                    """,
                    {"report_id": report["id"], **item.model_dump()},
                )
                evidence_rows.append(cur.fetchone())

        conn.commit()

    return _report_to_out(report, evidence_rows)


def list_reports(status: str | None = None, country_iso: str | None = None) -> list[ReportOut]:
    clauses = []
    params: dict = {}

    if status:
        clauses.append("status = %(status)s")
        params["status"] = status
    if country_iso:
        clauses.append("country_iso = %(country_iso)s")
        params["country_iso"] = country_iso

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM crisis_reports {where} ORDER BY created_at DESC",
                params,
            )
            reports = cur.fetchall()

            result = []
            for report in reports:
                cur.execute(
                    "SELECT * FROM report_evidence WHERE report_id = %s ORDER BY created_at",
                    (report["id"],),
                )
                evidence = cur.fetchall()
                result.append(_report_to_out(report, evidence))

    return result


def get_report(report_id: UUID) -> ReportOut | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM crisis_reports WHERE id = %s", (report_id,))
            report = cur.fetchone()
            if not report:
                return None
            cur.execute(
                "SELECT * FROM report_evidence WHERE report_id = %s ORDER BY created_at",
                (report_id,),
            )
            evidence = cur.fetchall()

    return _report_to_out(report, evidence)


def promote_report(report_id: UUID, triage_notes: str | None = None) -> PromoteResult:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM crisis_reports WHERE id = %s", (report_id,))
            report = cur.fetchone()
            if not report:
                raise ValueError("Report not found")
            if report["promoted_crisis_id"]:
                return PromoteResult(
                    report_id=report_id,
                    crisis_id=report["promoted_crisis_id"],
                    status=report["status"],
                )

            title = _title_from_narrative(report["narrative"], report["location_text"])
            severity = _estimate_severity(report["tags"] or [])
            urgency = "weeks" if severity <= 2 else "days"

            cur.execute(
                """
                INSERT INTO crisis_objects (
                    title, summary, type, country_iso, lat, lng,
                    severity, urgency, tags, source, source_report_id
                ) VALUES (
                    %(title)s, %(summary)s, %(type)s, %(country_iso)s, %(lat)s, %(lng)s,
                    %(severity)s, %(urgency)s, %(tags)s, 'user_report', %(source_report_id)s
                )
                RETURNING id
                """,
                {
                    "title": title,
                    "summary": report["narrative"],
                    "type": report["type"] or "persecution",
                    "country_iso": report["country_iso"],
                    "lat": report["lat"],
                    "lng": report["lng"],
                    "severity": severity,
                    "urgency": urgency,
                    "tags": report["tags"] or [],
                    "source_report_id": report_id,
                },
            )
            crisis_id = cur.fetchone()["id"]

            notes = triage_notes or "Promoted from community report for legal grounding and Ansar matching."
            cur.execute(
                """
                UPDATE crisis_reports
                SET status = 'promoted',
                    promoted_crisis_id = %(crisis_id)s,
                    triage_notes = %(notes)s,
                    updated_at = NOW()
                WHERE id = %(report_id)s
                """,
                {"crisis_id": crisis_id, "notes": notes, "report_id": report_id},
            )

        conn.commit()

    return PromoteResult(report_id=report_id, crisis_id=crisis_id, status="promoted")


def _estimate_severity(tags: list[str]) -> int:
    high = {"medical_need", "displacement", "food_insecurity"}
    medium = {"legal_aid_needed", "psychological_support", "advocacy"}
    if any(t in high for t in tags):
        return 4
    if any(t in medium for t in tags):
        return 3
    return 2


def _report_to_out(report: dict, evidence: list[dict]) -> ReportOut:
    return ReportOut(
        id=report["id"],
        narrative=report["narrative"],
        incident_at=report["incident_at"],
        location_text=report["location_text"],
        lat=report["lat"],
        lng=report["lng"],
        country_iso=report["country_iso"],
        type=report["type"],
        tags=report["tags"] or [],
        is_anonymous=report["is_anonymous"],
        preferred_language=report["preferred_language"],
        status=report["status"],
        promoted_crisis_id=report["promoted_crisis_id"],
        triage_notes=report["triage_notes"],
        created_at=report["created_at"],
        updated_at=report["updated_at"],
        evidence=[EvidenceOut(**row) for row in evidence],
    )
