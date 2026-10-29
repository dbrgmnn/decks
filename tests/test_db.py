import sqlite3

import pytest

import app.db as db


def test_init_creates_the_current_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)

    db.init()

    with db.conn() as c:
        tables = {
            row[0]
            for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert tables == {"users", "decks", "cards", "reviews"}

        user_columns = {row[1] for row in c.execute("PRAGMA table_info(users)")}
        assert user_columns == {
            "id",
            "email",
            "password_hash",
            "api_token_hash",
            "name",
            "created_at",
            "tz",
            "token_version",
            "lang",
        }

        deck_columns = {row[1] for row in c.execute("PRAGMA table_info(decks)")}
        assert deck_columns == {"id", "user_id", "name", "pos", "new_per_day", "paused"}

        card_columns = {row[1] for row in c.execute("PRAGMA table_info(cards)")}
        assert card_columns == {
            "id",
            "deck_id",
            "front",
            "back",
            "note",
            "state",
            "due",
            "tags",
        }

        review_columns = {row[1] for row in c.execute("PRAGMA table_info(reviews)")}
        assert review_columns == {"id", "card_id", "rating", "ts"}

        indexes = {
            row[0]
            for row in c.execute("SELECT name FROM sqlite_master WHERE type='index'")
        }
        assert {
            "i_user_email",
            "i_deck_name",
            "i_card_due",
            "i_card_new",
            "i_review_card",
            "i_review_ts",
        } <= indexes
        assert "i_deck_user" not in indexes

        assert c.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION


def test_init_keeps_an_existing_current_database(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    db.init()

    with db.conn() as c:
        c.execute(
            "INSERT INTO users(email, password_hash) VALUES(?, ?)",
            ("user@example.com", "hash"),
        )

    db.init()

    with db.conn() as c:
        assert c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1


@pytest.mark.parametrize("version", [0, 2, 3, 4, 5, 99])
def test_init_rejects_an_unsupported_schema(tmp_path, monkeypatch, version):
    database = tmp_path / "decks.db"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE unsupported(id INTEGER PRIMARY KEY)")
    connection.execute(f"PRAGMA user_version={version}")
    connection.commit()
    connection.close()

    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    with pytest.raises(RuntimeError, match="is not supported"):
        db.init()
