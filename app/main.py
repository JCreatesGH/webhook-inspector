"""Webhook / request inspector: create a bin, point any client at it, watch requests arrive."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .store import BinStore

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class ResponseConfig(BaseModel):
    status: int = Field(default=200, ge=100, le=599)
    body: str = ""
    content_type: str = "application/json"


def create_app(store: Optional[BinStore] = None) -> FastAPI:
    store = store or BinStore()
    app = FastAPI(title="Webhook Inspector", version="1.1.0")

    @app.post("/api/bins")
    def new_bin():
        return {"bin_id": store.create_bin()}

    @app.get("/api/bins/{bin_id}/requests")
    def list_requests(bin_id: str, since: int = 0):
        if not store.exists(bin_id):
            raise HTTPException(404, "unknown bin")
        return [r.to_dict() for r in store.requests(bin_id, since)]

    @app.delete("/api/bins/{bin_id}/requests")
    def clear(bin_id: str):
        if not store.exists(bin_id):
            raise HTTPException(404, "unknown bin")
        store.clear(bin_id)
        return {"ok": True}

    @app.get("/api/bins/{bin_id}/response")
    def get_response(bin_id: str):
        if not store.exists(bin_id):
            raise HTTPException(404, "unknown bin")
        return {"custom": store.has_custom_response(bin_id), **store.response(bin_id)}

    @app.put("/api/bins/{bin_id}/response")
    def set_response(bin_id: str, cfg: ResponseConfig):
        if not store.exists(bin_id):
            raise HTTPException(404, "unknown bin")
        store.set_response(bin_id, status=cfg.status, body=cfg.body, content_type=cfg.content_type)
        return {"ok": True, **cfg.model_dump()}

    @app.delete("/api/bins/{bin_id}/response")
    def reset_response(bin_id: str):
        if not store.exists(bin_id):
            raise HTTPException(404, "unknown bin")
        store.reset_response(bin_id)
        return {"ok": True}

    @app.api_route("/b/{bin_id}/{path:path}",
                   methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
    @app.api_route("/b/{bin_id}",
                   methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
    async def capture(bin_id: str, request: Request, path: str = ""):
        if not store.exists(bin_id):
            raise HTTPException(404, "unknown bin")
        body = (await request.body()).decode("utf-8", "replace")
        req = store.capture(
            bin_id,
            method=request.method,
            path="/" + path,
            query=dict(request.query_params),
            headers={k: v for k, v in request.headers.items()},
            body=body,
            ts=datetime.now(timezone.utc).isoformat(),
            ip=request.client.host if request.client else "",
        )
        if store.has_custom_response(bin_id):
            cfg = store.response(bin_id)
            return Response(content=cfg["body"], status_code=cfg["status"], media_type=cfg["content_type"])
        return JSONResponse({"received": True, "id": req.id}, status_code=200)

    if STATIC_DIR.exists():
        @app.get("/")
        def index():
            return FileResponse(STATIC_DIR / "index.html")
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app


app = create_app()
