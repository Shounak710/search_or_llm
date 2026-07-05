import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .admin_auth import require_admin_key
from .db import check_db_connection, close_db, init_db

from .classification_service import classify
from .query_log import log_classification, log_feedback, update_log_preference
from .geo_service import client_ip, country_from_headers
from .stats_log import log_request_stat, summarize_stats
from .routing_urls import (
    build_handoff_params,
    build_llm_url,
    build_search_url,
    preferences_from_params,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Nemka", version="1.0.0")

_cors_origins = os.getenv("CORS_ORIGINS", "*")
_origins = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]
_allow_all = len(_origins) == 1 and _origins[0] == "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _origins,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.on_event("shutdown")
def shutdown() -> None:
    close_db()


@app.middleware("http")
async def block_sensitive_paths(request: Request, call_next):
    path = request.url.path.lower()
    if path.startswith("/logs") or path.endswith(".jsonl") or "/logs/" in path:
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return await call_next(request)


class ClassifyRequest(BaseModel):
    query: str = Field(..., min_length=1)


class ClassifyResponse(BaseModel):
    query: str
    route: str
    source: str
    confidence: float | None = None
    reason: str | None = None
    redirect_url: str | None = None
    stackoverflow_title: str | None = None
    stackoverflow_score: int | None = None
    stackoverflow_accepted: bool | None = None


class FeedbackRequest(BaseModel):
    query: str = Field(..., min_length=1)
    predicted_route: str
    chosen_route: str
    useful_route: str
    manual_override: bool = False
    classified_at: str | None = None


class FeedbackResponse(BaseModel):
    status: str = "ok"


class LogPreferenceRequest(BaseModel):
    log_id: str = Field(..., min_length=1)
    useful_route: str
    query: str = Field(..., min_length=1)
    predicted_route: str


class LogPreferenceResponse(BaseModel):
    status: str = "ok"


def _schedule_request_stats(
    background_tasks: BackgroundTasks,
    request: Request,
    *,
    endpoint: str,
    result: dict,
    latency_ms: float,
    query_logged: bool,
) -> None:
    background_tasks.add_task(
        log_request_stat,
        ip=client_ip(request),
        country_hint=country_from_headers(request),
        endpoint=endpoint,
        result=result,
        latency_ms=latency_ms,
        query_logged=query_logged,
    )


def _resolve_search_destination(query: str, result: dict, preferences: dict) -> str:
    if result.get("redirect_url"):
        return result["redirect_url"]
    return build_search_url(query, preferences)


@app.get("/")
def home_page():
    return FileResponse(STATIC_DIR / "setup.html")


@app.get("/setup")
def setup_page():
    return RedirectResponse(url="/", status_code=302)


@app.get("/route-handoff")
def route_handoff_page():
    return FileResponse(STATIC_DIR / "route_handoff.html")


@app.get("/search")
def search_redirect(
    request: Request,
    background_tasks: BackgroundTasks,
    q: str = Query(..., min_length=1),
    se: str = Query("google"),
    llm: str = Query("openai"),
    csu: str = Query(""),
    clu: str = Query(""),
    log: str = Query("1"),
):
    started = time.perf_counter()
    query = q.strip()
    if query in {"%s", "%25s"}:
        raise HTTPException(
            status_code=400,
            detail="Search URL placeholder was not replaced. Re-copy the URL from the home page — it must contain q=%s, not q=%25s.",
        )
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    log_queries = log != "0"
    preferences = preferences_from_params(se=se, llm=llm, csu=csu, clu=clu)
    result = classify(query)
    latency_ms = (time.perf_counter() - started) * 1000

    _schedule_request_stats(
        background_tasks,
        request,
        endpoint="/search",
        result=result,
        latency_ms=latency_ms,
        query_logged=log_queries,
    )

    log_id = None
    if log_queries:
        log_id = log_classification(query, result)

    base_url = str(request.base_url)

    if result["route"] == "llm":
        handoff_params = build_handoff_params(preferences, log_queries=log_queries)
        final_dest = f"{base_url}llm-handoff?q={quote(query)}&{handoff_params}"
    else:
        final_dest = _resolve_search_destination(query, result, preferences)

    if log_queries and log_id:
        handoff_query = urlencode(
            {
                "q": query,
                "log_id": log_id,
                "route": result["route"],
                "source": result["source"],
                "ts": datetime.now(timezone.utc).isoformat(),
                "dest": final_dest,
            }
        )
        return RedirectResponse(url=f"/route-handoff?{handoff_query}", status_code=302)

    return RedirectResponse(url=final_dest, status_code=302)


@app.get("/llm-handoff")
def llm_handoff(
    q: str = Query(..., min_length=1),
    se: str = Query("google"),
    llm: str = Query("openai"),
    csu: str = Query(""),
    clu: str = Query(""),
):
    query = q.strip()
    preferences = preferences_from_params(se=se, llm=llm, csu=csu, clu=clu)
    llm_url = build_llm_url(query, preferences)
    query_json = json.dumps(query)
    llm_url_json = json.dumps(llm_url)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Opening LLM…</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      display: grid;
      place-items: center;
      min-height: 100vh;
      margin: 0;
      background: #f4f6fb;
      color: #1f2937;
    }}
    .card {{
      width: min(420px, 90vw);
      padding: 24px;
      border-radius: 16px;
      background: white;
      box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Opening LLM</h1>
    <p id="message">Copying your query to the clipboard…</p>
  </div>
  <script>
    const query = {query_json};
    const llmUrl = {llm_url_json};
    const message = document.getElementById("message");

    async function go() {{
      try {{
        await navigator.clipboard.writeText(query);
        message.textContent = "Copied to clipboard. Paste with ⌘V / Ctrl+V.";
      }} catch (error) {{
        message.textContent = "Could not copy automatically. Paste this query manually.";
      }}
      window.location.href = llmUrl;
    }}

    go();
  </script>
</body>
</html>"""

    return HTMLResponse(content=html)


@app.get("/health")
def health():
    if check_db_connection():
        return {"status": "ok", "database": "connected"}
    return JSONResponse(
        {"status": "degraded", "database": "unavailable"},
        status_code=503,
    )


@app.post("/classify", response_model=ClassifyResponse)
def classify_query(
    body: ClassifyRequest, request: Request, background_tasks: BackgroundTasks
):
    started = time.perf_counter()
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    result = classify(query)
    latency_ms = (time.perf_counter() - started) * 1000
    log_classification(query, result)

    _schedule_request_stats(
        background_tasks,
        request,
        endpoint="/classify",
        result=result,
        latency_ms=latency_ms,
        query_logged=True,
    )

    return ClassifyResponse(
        query=query,
        route=result["route"],
        source=result["source"],
        confidence=result.get("confidence"),
        reason=result.get("reason"),
        redirect_url=result.get("redirect_url"),
        stackoverflow_title=result.get("stackoverflow_title"),
        stackoverflow_score=result.get("stackoverflow_score"),
        stackoverflow_accepted=result.get("stackoverflow_accepted"),
    )


@app.get("/api/stats/summary")
def stats_summary(request: Request, days: int = Query(30, ge=1, le=365)):
    require_admin_key(request)
    return summarize_stats(days=days)


@app.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(body: FeedbackRequest):
    if body.useful_route not in {"search", "llm", "both", "neither"}:
        raise HTTPException(status_code=400, detail="Invalid useful_route")

    log_feedback(body.model_dump())
    return FeedbackResponse()


@app.post("/api/log-preference", response_model=LogPreferenceResponse)
def submit_log_preference(body: LogPreferenceRequest):
    if body.useful_route not in {"search", "llm"}:
        raise HTTPException(status_code=400, detail="Invalid useful_route")

    updated = update_log_preference(body.log_id, body.useful_route)
    if not updated:
        raise HTTPException(status_code=404, detail="Log entry not found")

    log_feedback(
        {
            "log_id": body.log_id,
            "query": body.query,
            "predicted_route": body.predicted_route,
            "chosen_route": body.predicted_route,
            "useful_route": body.useful_route,
            "manual_override": False,
            "source": "setup_history",
        }
    )
    return LogPreferenceResponse()
