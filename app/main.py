"""Webhook / request inspector: create a bin, point any client at it, watch requests arrive."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .store import BinStore

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(store: BinStore | None = None) -> FastAPI:
    store = store or BinStore()
    app = FastAPI(title="Webhook Inspector", version="1.0.0")

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
        )
        return JSONResponse({"received": True, "id": req.id}, status_code=200)

    if STATIC_DIR.exists():
        @app.get("/")
        def index():
            return FileResponse(STATIC_DIR / "index.html")
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app


app = create_app()
