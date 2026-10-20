import time

import pytest
from fastapi import HTTPException

import app.auth as auth
from app import db
from tests.conftest import login_user, signup_user


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


def test_signup_rejects_mismatched_passwords(client):
    response = client.post(
        "/api/signup",
        data={"email": "new@example.com", "password": "GoodPass123", "password2": "DifferentPass456"},
    )
    assert response.status_code == 400


def test_signup_rejects_duplicate_email(client):
    signup_user(client, email="dup@example.com")
    duplicate = client.post(
        "/api/signup",
        data={"email": "DUP@example.com", "password": "GoodPass123", "password2": "GoodPass123"},
    )
    assert duplicate.status_code == 400


def test_login_success_and_wrong_password(client):
    signup_user(client, email="login@example.com", password="GoodPass123")
    client.post("/api/logout")

    wrong = client.post(
        "/api/login",
        data={"email": "login@example.com", "password": "WrongPassword"},
    )
    assert wrong.status_code == 400

    correct = login_user(client, email="login@example.com", password="GoodPass123")
    assert correct.status_code == 200


def test_login_rate_limiting(client):
    email = "ratelimit@example.com"
    for _ in range(5):
        client.post("/api/login", data={"email": email, "password": "WrongPassword"})

    blocked_resp = client.post("/api/login", data={"email": email, "password": "WrongPassword"})
    assert blocked_resp.status_code == 429


def test_logout_revokes_the_session_cookie(auth_client):
    cookie = auth_client.cookies.get("decks_session")
    assert auth_client.get("/api/next/active").status_code == 200

    assert auth_client.post("/api/logout").status_code == 200

    auth_client.cookies.set("decks_session", cookie)
    assert auth_client.get("/api/next/active").status_code == 401


def test_password_change_revokes_other_sessions(auth_client):
    cookie = auth_client.cookies.get("decks_session")

    changed = auth_client.post(
        "/api/password",
        data={"current": "GoodPass123", "password": "NewPass999", "password2": "NewPass999"},
    )
    assert changed.status_code == 200
    # Current session remains active
    assert auth_client.get("/api/next/active").status_code == 200

    # Old session is revoked
    auth_client.cookies.set("decks_session", cookie)
    assert auth_client.get("/api/next/active").status_code == 401


def test_password_change_rejects_same_password_and_wrong_current(auth_client):
    # Same password
    same = auth_client.post(
        "/api/password",
        data={"current": "GoodPass123", "password": "GoodPass123", "password2": "GoodPass123"},
    )
    assert same.status_code == 400

    # Wrong current password
    wrong_curr = auth_client.post(
        "/api/password",
        data={"current": "WrongOldPass", "password": "NewPass999", "password2": "NewPass999"},
    )
    assert wrong_curr.status_code == 400


def test_save_settings_updates_timezone(auth_client):
    response = auth_client.post("/api/settings", data={"tz": "Europe/Berlin"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    with db.conn() as c:
        assert c.execute("SELECT tz FROM users WHERE email='test@example.com'").fetchone()["tz"] == "Europe/Berlin"

    invalid = auth_client.post("/api/settings", data={"tz": "Mars/Base1"})
    assert invalid.status_code == 400


def test_api_token_generation_and_bearer_authentication(auth_client, client):
    token_resp = auth_client.post("/api/account/token")
    assert token_resp.status_code == 200
    token = token_resp.json()["token"]
    assert token.startswith("dlk_")

    # Clear cookies so requests rely solely on the token
    auth_client.cookies.clear()

    # Use Bearer token from another unauthenticated client
    bearer_resp = auth_client.post(
        "/api/quick-add",
        data={"text": "TokenFolder"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bearer_resp.status_code == 200

    # Use X-API-Token header
    x_header_resp = auth_client.post(
        "/api/quick-add",
        data={"text": "TokenFolder2"},
        headers={"X-API-Token": token},
    )
    assert x_header_resp.status_code == 200

    # Invalid token fails
    invalid_resp = auth_client.post(
        "/api/quick-add",
        data={"text": "Fail"},
        headers={"Authorization": "Bearer dlk_invalid"},
    )
    assert invalid_resp.status_code == 401


def test_delete_account_removes_user_and_cascades_data(auth_client, make_deck, make_card):
    deck_id = make_deck()
    make_card(deck_id=deck_id)

    # Wrong password fails
    wrong = auth_client.post("/api/account/delete", data={"password": "WrongPassword"})
    assert wrong.status_code == 400

    # Correct password deletes account
    response = auth_client.post("/api/account/delete", data={"password": "GoodPass123"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    # Session is now invalid
    assert auth_client.get("/api/next/active").status_code == 401

    # User, decks and cards are gone from the database
    with db.conn() as c:
        assert c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM folders").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM decks").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 0