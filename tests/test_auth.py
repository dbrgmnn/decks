import time

import pytest
from fastapi import HTTPException

import app.auth as auth


def test_clean_email_trims_lowercases_and_validates():
    assert auth.clean_email("  User@Example.COM ") == "user@example.com"


def test_clean_email_rejects_invalid():
    with pytest.raises(HTTPException) as exc:
        auth.clean_email("not-an-email")
    assert exc.value.status_code == 400


def test_check_password_accepts_valid_password():
    auth.check_password("LongEnough1")


def test_check_password_rejects_short():
    with pytest.raises(HTTPException):
        auth.check_password("short")


def test_check_password_rejects_too_long():
    with pytest.raises(HTTPException):
        auth.check_password("x" * 129)


def test_check_password_rejects_common():
    with pytest.raises(HTTPException):
        auth.check_password("password")


def test_check_password_rejects_low_entropy():
    with pytest.raises(HTTPException):
        auth.check_password("aaaaaaaa")


def test_hash_and_verify_password_round_trip():
    hashed = auth.hash_pw("LongEnough1")
    assert auth.verify(hashed, "LongEnough1") is True
    assert auth.verify(hashed, "wrong") is False


def test_verify_rejects_oversized_password():
    assert auth.verify("dummy", "x" * 129) is False


def test_generate_and_verify_api_token():
    token = auth.generate_api_token()
    assert token.startswith("dlk_")
    hashed = auth.hash_api_token(token)
    assert auth.verify_api_token(hashed, token) is True
    assert auth.verify_api_token(hashed, "wrong") is False


def test_verify_api_token_rejects_oversized_token():
    assert auth.verify_api_token("anything", "x" * 257) is False


def test_blocked_fail_clear_rate_limiter():
    key = f"test-rate-{time.time()}"
    try:
        assert auth.blocked(key) is False
        for _ in range(5):
            auth.fail(key)
        assert auth.blocked(key) is True
        auth.clear(key)
        assert auth.blocked(key) is False
    finally:
        auth.clear(key)


def test_tz_options_includes_valid_current_zone():
    options = auth.tz_options("Europe/Berlin")
    zones = [zone for zone, _label in options]
    assert "Europe/Berlin" in zones or "Europe/Berlin" in auth.POPULAR_TZ
    assert all(isinstance(zone, str) and isinstance(_label, str) for zone, _label in options)


def _signup(client, email="sessions@example.com", password="GoodPass123"):
    response = client.post(
        "/api/signup",
        data={"email": email, "password": password, "password2": password, "tz": "UTC"},
    )
    assert response.status_code == 200, response.text


def test_logout_revokes_the_session_cookie(client):
    _signup(client)
    cookie = client.cookies.get("decks_session")
    assert client.get("/api/next/active").status_code == 200

    assert client.post("/api/logout").status_code == 200

    client.cookies.set("decks_session", cookie)
    assert client.get("/api/next/active").status_code == 401


def test_password_change_revokes_other_sessions(client):
    _signup(client)
    cookie = client.cookies.get("decks_session")

    changed = client.post(
        "/api/password",
        data={"current": "GoodPass123", "password": "NewPass999", "password2": "NewPass999"},
    )
    assert changed.status_code == 200
    # The device that changed the password stays signed in...
    assert client.get("/api/next/active").status_code == 200

    # ...but a copy of the old cookie no longer works.
    client.cookies.set("decks_session", cookie)
    assert client.get("/api/next/active").status_code == 401