import sqlite3

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import auth, db
from .routes import (
    auth as auth_routes,
    cards as card_routes,
    decks as deck_routes,
    folders as folder_routes,
    import_export as import_export_routes,
    pages as page_routes,
    study as study_routes,
)
from .web import BASE


app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=auth.secret_key(),
    session_cookie="decks_session",
    same_site="lax",
    https_only=auth.HTTPS_ONLY,
    max_age=60 * 60 * 24 * 30,
)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

db.init()
app.include_router(auth_routes.router)
app.include_router(page_routes.router)
app.include_router(folder_routes.router)
app.include_router(deck_routes.router)
app.include_router(import_export_routes.router)
app.include_router(card_routes.router)
app.include_router(study_routes.router)


@app.middleware("http")
async def no_cache(request, call_next):
    # pages and API answers must never come from the browser cache (settings would look "reset")
    resp = await call_next(request)
    if not request.url.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.exception_handler(sqlite3.IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse({"detail": "This name or email already exists"}, 400)
