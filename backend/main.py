import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import check_db_connection
from grounding.match_and_ground import match_and_ground
from grounding.match_users import match_users_for_crisis
from grounding.retrieve import fetch_grounding
from routers.reports import router as reports_router
from services.decomposer import decompose_crisis
from services.dashboard import get_crisis_summary, list_ansar, list_crises, list_tasks
from services.matcher import list_task_matches, match_tasks_for_crisis
from services.notify import notify_matches_for_crisis
from services import legal as legal_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    check_db_connection()
    yield


app = FastAPI(
    title="Al-Ansar API",
    description="Crisis ingestion, legal grounding, task matching",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    check_db_connection()
    return {"status": "ok", "database": "connected"}


@app.get("/dashboard/crises")
def dashboard_crises():
    return {"crises": list_crises()}


@app.get("/dashboard/crises/{crisis_id}")
def dashboard_crisis(crisis_id: str):
    try:
        parsed_id = UUID(crisis_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid crisis_id") from exc

    crisis = get_crisis_summary(parsed_id)
    if not crisis:
        raise HTTPException(status_code=404, detail="Crisis not found")
    return crisis


@app.get("/dashboard/grounding/{crisis_id}")
def dashboard_grounding(crisis_id: str):
    try:
        parsed_id = UUID(crisis_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid crisis_id") from exc

    grounding = fetch_grounding(parsed_id)
    if not grounding:
        raise HTTPException(
            status_code=404,
            detail=f"No grounding found for crisis {crisis_id}. Run POST /ground/{crisis_id} first.",
        )
    return {
        "grounding_id": grounding["grounding_id"],
        "crisis_id": grounding["crisis_id"],
        "has_legal_support": grounding["has_legal_support"],
        "summary": grounding["summary"],
        "matched_chunks": grounding["matched_chunks"],
        "matched_users": grounding["matched_users"],
        "created_at": grounding["created_at"].isoformat(),
    }


@app.get("/dashboard/tasks")
def dashboard_tasks(crisis_id: str | None = Query(None)):
    parsed_id: UUID | None = None
    if crisis_id:
        try:
            parsed_id = UUID(crisis_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid crisis_id") from exc
    return {"tasks": list_tasks(crisis_id=parsed_id)}


@app.get("/dashboard/matches")
def dashboard_matches(crisis_id: str | None = Query(None)):
    parsed_id: UUID | None = None
    if crisis_id:
        try:
            parsed_id = UUID(crisis_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid crisis_id") from exc
    matches = list_task_matches(crisis_id=parsed_id)
    return {
        "matches": matches,
        "tasks": _group_matches_response(matches),
    }


def _group_matches_response(matches: list[dict]) -> list[dict]:
    by_task: dict[str, dict] = {}
    for m in matches:
        tid = m["task_id"]
        if tid not in by_task:
            by_task[tid] = {
                "task_id": tid,
                "task_title": m.get("task_title"),
                "task_status": m.get("task_status"),
                "matches": [],
            }
        by_task[tid]["matches"].append(m)
    return list(by_task.values())


@app.get("/dashboard/ansar")
def dashboard_ansar():
    return {"ansar": list_ansar()}


@app.get("/legal/sources")
def legal_sources(jurisdiction: str | None = Query(None)):
    return {"sources": legal_service.list_legal_sources(jurisdiction=jurisdiction)}


@app.get("/legal/sources/{source_id}")
def legal_source(source_id: str):
    try:
        parsed_id = UUID(source_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid source_id") from exc

    source = legal_service.get_legal_source(parsed_id)
    if not source:
        raise HTTPException(status_code=404, detail="Legal source not found")
    return source


@app.get("/legal/chunks")
def legal_chunks(
    jurisdiction: str | None = Query(None),
    source_id: str | None = Query(None),
    include_text: bool = Query(True),
):
    parsed_source_id: UUID | None = None
    if source_id:
        try:
            parsed_source_id = UUID(source_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid source_id") from exc

    return {
        "chunks": legal_service.list_legal_chunks(
            jurisdiction=jurisdiction,
            source_id=parsed_source_id,
            include_text=include_text,
        )
    }


@app.post("/ingest/gdelt")
def ingest_gdelt():
    return {"message": "Not implemented — Person 1", "crisis_id": None}


@app.post("/ground/{crisis_id}")
async def ground_crisis(crisis_id: str, force: bool = False):
    try:
        parsed_id = UUID(crisis_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid crisis_id") from exc

    try:
        return await match_and_ground(parsed_id, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/match/{crisis_id}")
async def match_crisis_users(crisis_id: str, force: bool = False):
    try:
        parsed_id = UUID(crisis_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid crisis_id") from exc

    try:
        return await match_users_for_crisis(parsed_id, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/decompose/{crisis_id}")
async def decompose_crisis_tasks(crisis_id: str, force: bool = False):
    try:
        parsed_id = UUID(crisis_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid crisis_id") from exc

    try:
        return await decompose_crisis(parsed_id, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/match/tasks/{crisis_id}")
def match_tasks(crisis_id: str, force: bool = False):
    try:
        parsed_id = UUID(crisis_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid crisis_id") from exc

    try:
        return match_tasks_for_crisis(parsed_id, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/notify/{crisis_id}")
def notify_crisis(crisis_id: str, force: bool = False):
    try:
        parsed_id = UUID(crisis_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid crisis_id") from exc

    try:
        return notify_matches_for_crisis(parsed_id, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/pipeline/run/{crisis_id}")
def run_pipeline(crisis_id: str):
    return {"message": "Not implemented — integration checkpoint", "crisis_id": crisis_id}
