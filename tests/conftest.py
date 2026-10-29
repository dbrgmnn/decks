import importlib
import sqlite3

import pytest
from fastapi.testclient import TestClient

import app.db as db


def _create_schema(conn):
    db.create_schema(conn)
    conn.execute(f"PRAGMA user_version={db.SCHEMA_VERSION}")
    conn.commit()


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    _create_schema(connection)
    yield connection
    connection.close()


@pytest.fixture
def user_id(conn):
    cur = conn.execute(
        "INSERT INTO users(email, password_hash, name, tz) VALUES(?,?,?,?)",
        ("user@example.com", "hash", "user", "UTC"),
    )
    conn.commit()
    return cur.lastrowid


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A TestClient backed by a throw-away SQLite database."""
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    import app.main as main

    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c


def signup_user(client, email="test@example.com", password="GoodPass123", tz="UTC"):
    """Register and sign in a new user."""
    response = client.post(
        "/api/signup",
        data={"email": email, "password": password, "password2": password, "tz": tz},
    )
    assert response.status_code == 200, response.text
    return {"email": email, "password": password}


def login_user(client, email="test@example.com", password="GoodPass123"):
    """Log in an existing user."""
    response = client.post(
        "/api/login",
        data={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response


@pytest.fixture
def auth_client(client):
    """A TestClient already signed in with a default user."""
    signup_user(client, email="test@example.com", password="GoodPass123")
    return client


@pytest.fixture
def make_deck(auth_client):
    """Factory fixture to create a deck for the authenticated user."""
    def _make(name="Deck", new_per_day="10"):
        response = auth_client.post("/api/decks", data={"name": name})
        assert response.status_code == 200, response.text
        deck_id = response.json()["id"]
        if new_per_day != "10":
            settings = auth_client.post(
                f"/api/decks/{deck_id}/settings",
                data={"new_per_day": new_per_day, "paused": 0},
            )
            assert settings.status_code == 200, settings.text
        return deck_id
    return _make


@pytest.fixture
def make_card(auth_client, make_deck):
    """Factory fixture to create a card for the authenticated user."""
    def _make(deck_id=None, front="front", back="back", note="", tags=None):
        if deck_id is None:
            deck_id = make_deck()
        response = auth_client.post(
            "/api/cards",
            json={
                "deck_id": deck_id,
                "front": front,
                "back": back,
                "note": note,
                "tags": tags or [],
            },
        )
        assert response.status_code == 201, response.text
        return response.json()["card"]["id"]
    return _make
