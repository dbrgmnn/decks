"""Tiny UI localization layer.

Catalogs are plain JSON files shared by Jinja and the browser. Only the
interface is translated; deck and card text stays exactly as the user typed it.
"""

import json
import os
import pathlib
import sqlite3
from functools import lru_cache

from fastapi import HTTPException

from .. import db


BASE = pathlib.Path(__file__).parent
DEFAULT = "en"
SUPPORTED = ("en", "de")
LOCALES = {"en": "en", "de": "de-DE"}
COOKIE = "decks_lang"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365
HTTPS_ONLY = os.environ.get("HTTPS_ONLY") == "1"


@lru_cache(maxsize=None)
def _load(lang):
    return json.loads((BASE / f"{lang}.json").read_text("utf-8"))


def t(key, lang=DEFAULT, **vars):
    """Look up a message and fill in {placeholders}, falling back to English."""
    lang = lang if lang in SUPPORTED else DEFAULT
    value = _load(lang).get(key)
    if value is None:
        value = _load(DEFAULT).get(key, key)
    if not isinstance(value, str):
        # A plural entry used without a count: show its "other" form.
        value = value.get("other", key) if isinstance(value, dict) else key
    try:
        return value.format(**vars)
    except (KeyError, IndexError, ValueError):
        return value


def _plural_category(lang, count):
    if lang == "en":
        return "one" if count == 1 else "other"
    # German uses the same one/other split as English.
    return "one" if count == 1 else "other"


def plural(key, count, lang=DEFAULT, **vars):
    """Pick the plural form for `count` and fill in {placeholders}.

    Catalogs keep plurals as flat keys (`x.one`, `x.other`) so the JSON stays
    easy to diff and validate.
    """
    lang = lang if lang in SUPPORTED else DEFAULT
    forms = _load(lang).get(key)
    if not isinstance(forms, dict):
        forms = {
            cat: _load(lang).get(f"{key}.{cat}")
            for cat in ("one", "other")
        }
    if not any(forms.values()):
        forms = _load(DEFAULT).get(key)
        if not isinstance(forms, dict):
            forms = {cat: _load(DEFAULT).get(f"{key}.{cat}") for cat in ("one", "other")}
    if not any(forms.values()):
        return key
    value = forms.get(_plural_category(lang, count)) or forms.get("other") or key
    try:
        return value.format(count=count, **vars)
    except (KeyError, IndexError, ValueError):
        return value


def render(key, lang=DEFAULT, **params):
    """Translate an error key, translating a `field` key such as field.front too."""
    field = params.get("field")
    if isinstance(field, str) and field.startswith("field."):
        params = {**params, "field": t(field, lang)}
    return t(key, lang, **params)


class LocalizedHTTPException(HTTPException):
    """An HTTP error that carries a catalog key instead of a fixed sentence."""

    def __init__(self, status_code, code, **params):
        self.code = code
        self.params = params
        super().__init__(status_code, render(code, DEFAULT, **params))


def error(status_code, code, **params):
    return LocalizedHTTPException(status_code, code, **params)


def from_accept_language(header):
    for part in (header or "").split(","):
        code = part.split(";")[0].strip().lower().replace("_", "-")
        base = code.split("-")[0]
        if base in SUPPORTED:
            return base
    return None


def lang_from_cookie(request):
    cookie = request.cookies.get(COOKIE)
    return cookie if cookie in SUPPORTED else None


def lang_for(request):
    """Current UI language: user setting, then cookie, then Accept-Language."""
    cached = getattr(request.state, "lang", None)
    if cached in SUPPORTED:
        return cached

    lang = None
    try:
        uid = request.session.get("uid")
    except (AssertionError, AttributeError):
        uid = None
    if uid:
        try:
            with db.conn() as c:
                row = c.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
            if row and row["lang"] in SUPPORTED:
                lang = row["lang"]
        except (sqlite3.Error, KeyError):
            # A locale must never break a request if the database is unavailable.
            lang = None

    if not lang:
        lang = lang_from_cookie(request)
    if not lang:
        lang = from_accept_language(request.headers.get("accept-language", ""))
    if not lang:
        lang = DEFAULT

    request.state.lang = lang
    return lang


def resolve(request, user=None):
    """Like lang_for, but uses an already loaded user row when available."""
    cached = getattr(request.state, "lang", None)
    if cached in SUPPORTED:
        return cached
    if user and user.get("lang") in SUPPORTED:
        request.state.lang = user["lang"]
        return user["lang"]
    return lang_for(request)


def catalog_json(lang):
    """English merged with the selected language, so the browser has a fallback."""
    lang = lang if lang in SUPPORTED else DEFAULT
    data = dict(_load(DEFAULT))
    data.update(_load(lang))
    data["__lang"] = lang
    data["__locale"] = LOCALES[lang]
    # Keep the inline JSON from closing its own <script> element.
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def set_language_cookie(response, lang):
    # Not HttpOnly on purpose: the static offline page reads this cookie to pick
    # its language when the service worker shows it without a server round-trip.
    response.set_cookie(
        COOKIE,
        lang,
        max_age=COOKIE_MAX_AGE,
        path="/",
        samesite="lax",
        secure=HTTPS_ONLY,
    )


def clear_language_cookie(response):
    response.delete_cookie(COOKIE, path="/")
