import importlib
import sqlite3

import pytest
from fastapi.testclient import TestClient

import app.db as db


def _create_schema(conn):
    for name in db.ORDER:
        conn.execute(db.TABLES[name])
    for sql in db.INDEXES:
        conn.execute(sql)
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