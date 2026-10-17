import secrets

from fastapi import FastAPI
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


# The interactive docs are disabled: they would expose the whole API surface
# without authentication.
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

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


CSP = (
    "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
    "form-action 'self'; img-src 'self' data:; style-src 'self'; connect-src 'self'; "
    "manifest-src 'self'; worker-src 'self'; script-src 'self' 'nonce-{}'"
)


@app.middleware("http")
async def http_headers(request, call_next):
    # A fresh nonce per request lets the inline theme bootstrap run while every
    # other script stays same-origin only.
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    if auth.HTTPS_ONLY:
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    # Pages and API answers must never come from the browser cache (settings
    # would look "reset"); static assets may.
    if not request.url.path.startswith("/static/"):
        resp.headers["Content-Security-Policy"] = CSP.format(nonce)
        resp.headers["Cache-Control"] = "no-store"
    return resp
