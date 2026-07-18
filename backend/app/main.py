from __future__ import annotations

"""FastAPI app. The API lives under /api; the static reader client is served at
/ from the same origin, so the browser needs no CORS."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config, db
from .routers import library, progress, read, state


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_dirs()
    conn = db.connect()
    try:
        db.init_db(conn)
        # Two users to start; the asymmetry between them is all data, no code.
        for name in ("alex", "mei"):
            db.ensure_user(conn, name)
    finally:
        conn.close()
    yield


app = FastAPI(title="Chinese Reader", version="0.2.0", lifespan=lifespan)

app.include_router(read.router, prefix="/api", tags=["read"])
app.include_router(library.router, prefix="/api", tags=["library"])
app.include_router(state.router, prefix="/api", tags=["state"])
app.include_router(progress.router, prefix="/api", tags=["progress"])


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "app": "chinese-reader", "version": "0.2.0"}


# Mount the static reader last so /api/* wins. Guard the mount so the app still
# imports for tests if the web/ dir is absent.
if config.WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(config.WEB_DIR), html=True), name="web")
