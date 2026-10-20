import sqlite3

import pytest

import app.db as db


OLD_USERS_SQL = """
CREATE TABLE users(
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  api_token_hash TEXT NOT NULL DEFAULT '',
  name TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  tz TEXT NOT NULL DEFAULT 'UTC'
)
"""


def test_init_creates_current_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)

    db.init()

    with db.conn() as c:
        columns = {row[1] for row in c.execute("PRAGMA table_info(users)")}
        assert "token_version" in columns
        assert "lang" in columns
        assert c.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION


def test_init_upgrades_a_version_one_database(tmp_path, monkeypatch):
    database = tmp_path / "decks.db"
    connection = sqlite3.connect(database)
    connection.execute(OLD_USERS_SQL)
    connection.execute(
        "INSERT INTO users(email,password_hash,name,tz) VALUES(?,?,?,?)",
        ("old@example.com", "hash", "old", "UTC"),
    )
    connection.execute("PRAGMA user_version=1")
    connection.commit()
    connection.close()

    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    db.init()

    with db.conn() as c:
        columns = {row[1] for row in c.execute("PRAGMA table_info(users)")}
        assert "token_version" in columns
        assert "lang" in columns
        row = c.execute("SELECT email, token_version, lang FROM users").fetchone()
        assert row["email"] == "old@example.com"
        assert row["token_version"] == 0
        assert row["lang"] == ""
        assert c.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION


def test_init_refuses_a_newer_database(tmp_path, monkeypatch):
    database = tmp_path / "decks.db"
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA user_version=99")
    connection.commit()
    connection.close()

    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    with pytest.raises(RuntimeError):
        db.init()
