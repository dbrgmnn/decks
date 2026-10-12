import os
import re
import secrets
import time
from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request

from . import db


POPULAR_TZ = [
    "UTC", "Pacific/Honolulu", "America/Anchorage", "America/Los_Angeles", "America/Denver", "America/Chicago",
    "America/New_York", "America/Toronto", "America/Mexico_City", "America/Bogota", "America/Sao_Paulo",
    "America/Argentina/Buenos_Aires", "Atlantic/Reykjavik", "Europe/London", "Europe/Dublin", "Europe/Lisbon",
    "Europe/Madrid", "Europe/Paris", "Europe/Berlin", "Europe/Amsterdam", "Europe/Rome", "Europe/Zurich",
    "Europe/Vienna", "Europe/Warsaw", "Europe/Prague", "Europe/Stockholm", "Europe/Athens", "Europe/Kyiv",
    "Europe/Istanbul", "Europe/Minsk", "Europe/Moscow", "Africa/Cairo", "Africa/Lagos", "Africa/Johannesburg",
    "Asia/Jerusalem", "Asia/Dubai", "Asia/Tbilisi", "Asia/Yerevan", "Asia/Baku", "Asia/Tashkent", "Asia/Karachi",
    "Asia/Almaty", "Asia/Kolkata", "Asia/Dhaka", "Asia/Bangkok", "Asia/Shanghai", "Asia/Singapore",
    "Asia/Hong_Kong", "Asia/Tokyo", "Asia/Seoul", "Australia/Perth", "Australia/Sydney", "Pacific/Auckland",
]
TZ_SET = set(available_timezones()) | {"UTC"}  # any valid zone is accepted, the dropdown shows the popular ones
HTTPS_ONLY = os.environ.get("HTTPS_ONLY") == "1"

# Argon2id with the OWASP minimum parameters (light enough for a Raspberry Pi)
_ph = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
DUMMY = _ph.hash("dummy-password")  # verified for unknown emails so timing looks the same

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
COMMON = {
    "password", "password1", "12345678", "123456789", "1234567890", "qwertyui", "qwerty123",
    "iloveyou", "11111111", "00000000", "abcd1234", "admin123", "letmein1", "welcome1",
}

# Tiny in-memory rate limiter (resets on restart, fine for a home server)
_fails = {}


def tz_options(current):
    """[(zone, label)] sorted by current UTC offset; the user's own zone is always included."""
    zones = POPULAR_TZ + ([current] if current and current not in POPULAR_TZ and current in TZ_SET else [])
    out = []
    for z in zones:
        mins = int(datetime.now(ZoneInfo(z)).utcoffset().total_seconds() // 60)
        h, m = divmod(abs(mins), 60)
        city = z.split("/")[-1].replace("_", " ")
        out.append((mins, z, f"(UTC{'+' if mins >= 0 else '-'}{h:02d}:{m:02d}) {city}"))
    return [(z, label) for _, z, label in sorted(out, key=lambda t: (t[0], t[2]))]


def secret_key():
    if os.environ.get("SESSION_SECRET"):
        return os.environ["SESSION_SECRET"]
    f = db.DATA_DIR / ".session_secret"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(secrets.token_hex(32))
        f.chmod(0o600)
    return f.read_text().strip()


def hash_pw(pw):
    return _ph.hash(pw)


def generate_api_token():
    return f"dlk_{secrets.token_urlsafe(32)}"


def hash_api_token(token):
    return _ph.hash(token)


def verify_api_token(hashed, token):
    if not hashed or len(token) > 256:
        return False
    try:
        return _ph.verify(hashed, token)
    except (VerificationError, InvalidHashError):
        return False


def verify(hashed, pw):
    if len(pw) > 128:
        return False
    try:
        return _ph.verify(hashed, pw)
    except (VerificationError, InvalidHashError):
        return False


def clean_email(email):
    email = email.strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise HTTPException(400, "Enter a valid email address")
    return email


def check_password(pw):
    if len(pw) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if len(pw) > 128:
        raise HTTPException(400, "Password is too long (max 128)")
    if pw.lower() in COMMON or len(set(pw)) < 4:
        raise HTTPException(400, "Password is too easy to guess")


def blocked(key, limit=5, window=600):
    now = time.time()
    _fails[key] = [t for t in _fails.get(key, []) if now - t < window]
    return len(_fails[key]) >= limit


def fail(key):
    _fails.setdefault(key, []).append(time.time())


def clear(key):
    _fails.pop(key, None)


def ip(request: Request):
    return request.client.host if request.client else "?"


def current_user(request: Request):
    uid = request.session.get("uid")
    row = db.conn().execute("SELECT id, email, name, tz FROM users WHERE id=?", (uid,)).fetchone() if uid else None
    if row:
        return row
    request.session.clear()
    if request.url.path.startswith("/api/"):
        raise HTTPException(401, "Please sign in")
    raise HTTPException(303, headers={"Location": "/login"})


def current_user_or_token(request: Request):
    uid = request.session.get("uid")
    if uid:
        row = db.conn().execute("SELECT id, email, name, tz FROM users WHERE id=?", (uid,)).fetchone()
        if row:
            return row
        request.session.clear()

    auth_header = request.headers.get('Authorization', '')
    token = ''
    if auth_header.lower().startswith('bearer '):
        token = auth_header[7:].strip()
    if not token:
        token = request.headers.get('X-API-Token', '').strip()

    if token:
        with db.conn() as c:
            rows = c.execute('SELECT id, email, name, tz, api_token_hash FROM users WHERE api_token_hash != ""').fetchall()
        for row in rows:
            if verify_api_token(row['api_token_hash'], token):
                return row

    if request.url.path.startswith('/api/'):
        raise HTTPException(401, 'Please sign in')
    raise HTTPException(303, headers={'Location': '/login'})
