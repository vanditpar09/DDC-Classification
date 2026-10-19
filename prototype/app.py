"""Serve the adaptive capture prototype on localhost:8011."""
from __future__ import annotations

import io
import json
import hashlib
import os
import copy
from urllib.parse import urlsplit
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from prototype.engine import Engine, Conflict, MissingSession, LANGUAGES, MAX_BYTES, ROOT, TESSDATA, model_version
from prototype.storage import SQLiteStore
from prototype.scene_ocr import backend_status

HERE = Path(__file__).resolve().parent
engine = Engine(store=SQLiteStore(os.environ.get("FIELDNOTE_DB", str(ROOT / "output/fieldnote/experiments.sqlite3"))))
app = FastAPI(title="Fieldnote - local adaptive capture prototype")
ORIGINS = {"http://127.0.0.1:8011", "http://localhost:8011", "http://testserver"}
# Explicit origin opt-in for a private HTTPS LAN test, no wildcard hosts/CORS.
ORIGINS.update(o.strip().rstrip('/') for o in os.environ.get("FIELDNOTE_ORIGINS", "").split(',') if o.strip())
if any(urlsplit(o).scheme not in {'http', 'https'} or not urlsplit(o).hostname or
       urlsplit(o).path or '*' in o for o in ORIGINS):
    raise ValueError("FIELDNOTE_ORIGINS must contain exact http(s) origins")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=sorted({urlsplit(o).hostname for o in ORIGINS}))


@app.middleware("http")
async def local_writes_only(request, call_next):
    origin = request.headers.get("origin")
    if request.method in {"POST", "DELETE", "PUT", "PATCH"} and origin and origin not in ORIGINS:
        return JSONResponse({"detail": "Only the local prototype page may submit requests"}, status_code=403)
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers['Permissions-Policy'] = 'camera=(self), microphone=()'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.exception_handler(ValueError)
async def invalid_input(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=409 if isinstance(exc, Conflict) else 404 if isinstance(exc, MissingSession) else 400)


class TextPage(BaseModel):
    kind: str
    language: str = "eng"
    text: str = Field(min_length=1, max_length=12000)


class RepairRequest(BaseModel):
    language: Optional[str] = None


class ReviewRequest(BaseModel):
    section: str = Field(pattern=r"^[0-9]{3}$")
    reviewer: str = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=2000)
    book_id: str = Field(default="", max_length=150)


def mutate(sid, key, revision, data, operation):
    fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return engine.execute(sid, key, fingerprint, revision, operation)


@app.get("/api/status")
def status():
    return {"model_files_present": any((ROOT / path).exists() for path in (
                "models/hierarchy_v1/classifier.joblib", "models/improved_v1/classifier.joblib")),
            "hierarchical_model_present": (ROOT / "models/hierarchy_v1/classifier.joblib").exists(),
            "languages": {k: v for k, v in LANGUAGES.items() if all((TESSDATA / (part + ".traineddata")).exists() for part in k.split("+"))},
            "cloud_calls": False, "max_ocr_passes": engine.policy.max_ocr_passes,
            "persistence": "sqlite", "model_version": model_version(), "api_version": 2,
            "ocr": backend_status(),
            "readable_exports": {"available": getattr(engine.store,"export_error",None) is None,
                                 "error": getattr(engine.store,"export_error",None)}}


@app.post("/api/sessions")
def create_session():
    return engine.new_session()


@app.get("/api/sessions")
def list_sessions():
    return engine.list_sessions()


@app.get("/api/collection")
def collection_summary():
    from prototype.collection_export import collection_rows, html_table
    with engine.lock:
        data = html_table(collection_rows(engine.store))
    return Response(data, media_type="text/html")


@app.get("/api/collection/export")
def collection_download(format: str = "csv"):
    from prototype.collection_export import collection_rows, csv_text
    if format not in {"csv", "json"}:
        raise ValueError("Use csv or json for collection export")
    with engine.lock:
        rows = collection_rows(engine.store)
        data = csv_text(rows) if format == "csv" else json.dumps(rows, ensure_ascii=False, indent=2)
    return Response(data, media_type="text/csv" if format == "csv" else "application/json",
                    headers={"Content-Disposition": f'attachment; filename="classifications.{format}"'})


@app.get("/api/sessions/{sid}")
def get_session(sid: str):
    with engine.lock:
        return copy.deepcopy(engine.get(sid))


@app.delete("/api/sessions/{sid}")
def delete_session(sid: str):
    engine.delete(sid)
    return {"deleted": True}


@app.post("/api/sessions/{sid}/reclassify")
def reclassify_session(sid: str, idempotency_key: Optional[str] = Header(None), x_book_revision: Optional[int] = Header(None)):
    return mutate(sid,idempotency_key,x_book_revision,["reclassify"],lambda:engine.reclassify(sid))


@app.post("/api/sessions/{sid}/text")
def add_text(sid: str, page: TextPage, idempotency_key: Optional[str] = Header(None), x_book_revision: Optional[int] = Header(None)):
    return mutate(sid, idempotency_key, x_book_revision, ["text", page.model_dump()],
                  lambda: engine.add_text(sid, page.kind, page.text, page.language))


@app.post("/api/sessions/{sid}/image")
async def add_image(sid: str, image: UploadFile = File(...), kind: str = Form(...), language: str = Form("eng"),
                    idempotency_key: Optional[str] = Header(None), x_book_revision: Optional[int] = Header(None)):
    content = await image.read(MAX_BYTES + 1)
    await image.close()
    return await run_in_threadpool(mutate, sid, idempotency_key, x_book_revision,
                                   ["image", kind, language, hashlib.sha256(content).hexdigest()],
                                   lambda: engine.add_image(sid, kind, content, language))


@app.post("/api/sessions/{sid}/pages/{pid}/repair")
def repair(sid: str, pid: str, request: RepairRequest, idempotency_key: Optional[str] = Header(None), x_book_revision: Optional[int] = Header(None)):
    return mutate(sid, idempotency_key, x_book_revision, ["repair", pid, request.language],
                  lambda: engine.repair(sid, pid, request.language))


@app.post("/api/sessions/{sid}/review")
def review(sid: str, request: ReviewRequest, idempotency_key: Optional[str] = Header(None), x_book_revision: Optional[int] = Header(None)):
    return mutate(sid, idempotency_key, x_book_revision, ["review", request.model_dump()],
                  lambda: engine.add_review(sid, request.section, request.reviewer, request.note, request.book_id))


@app.get("/api/sessions/{sid}/pages/{pid}/image")
def page_image(sid: str, pid: str):
    with engine.lock:
        try:
            image = engine.get_image(sid, pid)
        except ValueError:
            raise HTTPException(404, "Image not found")
        thumb = image.copy()
        thumb.thumbnail((1200, 1200))
        buffer = io.BytesIO()
        thumb.save(buffer, format="PNG")
    return Response(buffer.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


@app.get("/api/sessions/{sid}/export")
def export(sid: str):
    with engine.lock:
        data = json.dumps(engine.get(sid), indent=2, ensure_ascii=False)
    return Response(data, media_type="application/json", headers={"Content-Disposition": 'attachment; filename="capture-experiment.json"'})


@app.get("/api/samples")
def samples():
    path = HERE / "samples/manifest.json"
    return json.loads(path.read_text()) if path.exists() else []


if (HERE / "samples").exists():
    app.mount("/samples", StaticFiles(directory=str(HERE / "samples")), name="samples")
app.mount("/", StaticFiles(directory=str(HERE / "static"), html=True), name="static")
