import secrets

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from . import auth, db, i18n
from .routes import (
    auth as auth_routes,
    cards as card_routes,
    decks as deck_routes,
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
app.include_router(deck_routes.router)
app.include_router(import_export_routes.router)
app.include_router(card_routes.router)
app.include_router(study_routes.router)


CSP = (
    "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
    "form-action 'self'; img-src 'self' data:; style-src 'self'; connect-src 'self'; "
    "manifest-src 'self'; worker-src 'self'; script-src 'self' 'nonce-{}'"
)


@app.exception_handler(StarletteHTTPException)
async def localized_errors(request, exc):
    """Translate API and page errors in the language of the request."""
    lang = i18n.lang_for(request)
    if isinstance(exc, i18n.LocalizedHTTPException):
        detail = i18n.render(exc.code, lang, **exc.params)
        body = {"detail": detail, "code": exc.code.removeprefix("error.")}
        field = exc.params.get("field")
        if field:
            body["field"] = str(field).removeprefix("field.")
    else:
        detail = exc.detail
        body = {"detail": detail, "code": "http_error"}
    response = JSONResponse(
        body,
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
    )
    response.headers["Content-Language"] = lang
    return response


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    """Keep malformed JSON and wrong field types on the same error contract."""
    lang = i18n.lang_for(request)
    response = JSONResponse(
        {
            "detail": i18n.render("error.invalid_request", lang),
            "code": "invalid_request",
        },
        status_code=422,
    )
    response.headers["Content-Language"] = lang
    return response


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
    # would look "reset"). Static assets are cache-busted by ?v= only at their
    # entry point, so internal ES-module imports keep the bare URL. Tell the
    # browser to revalidate them instead of guessing a heuristic lifetime:
    # otherwise a phone can keep an old module (and its old UI) for days.
    if request.url.path.startswith("/static/"):
        resp.headers.setdefault("Cache-Control", "no-cache")
    else:
        resp.headers["Content-Security-Policy"] = CSP.format(nonce)
        resp.headers["Cache-Control"] = "no-store"
    return resp
