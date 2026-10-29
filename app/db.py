import pathlib
import sqlite3

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"

SCHEMA_VERSION = 1

USERS_SQL = """
CREATE TABLE users(
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  api_token_hash TEXT NOT NULL DEFAULT '',
  name TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  tz TEXT NOT NULL DEFAULT 'UTC',
  token_version INTEGER NOT NULL DEFAULT 0,
  lang TEXT NOT NULL DEFAULT ''
)
"""

DECKS_SQL = """
CREATE TABLE decks(
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  pos INTEGER NOT NULL DEFAULT 0,
  new_per_day INTEGER NOT NULL DEFAULT 10 CHECK(new_per_day IN (1, 5, 10, 15, 20, 30)),
  paused INTEGER NOT NULL DEFAULT 0 CHECK(paused IN (0, 1)),
  UNIQUE(user_id, pos)
)
"""

CARDS_SQL = """
CREATE TABLE cards(
  id INTEGER PRIMARY KEY,
  deck_id INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
  front TEXT NOT NULL,
  back TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  tags TEXT NOT NULL DEFAULT '',
  state TEXT,
  due TEXT
)
"""

REVIEWS_SQL = """
CREATE TABLE reviews(
  id INTEGER PRIMARY KEY,
  card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 4),
  ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

# Tables are created in dependency order.
TABLES = (USERS_SQL, DECKS_SQL, CARDS_SQL, REVIEWS_SQL)

# UNIQUE(user_id, pos) on decks already provides an index for deck ordering.
INDEXES = (
    "CREATE UNIQUE INDEX i_user_email ON users(lower(email))",
    "CREATE UNIQUE INDEX i_deck_name ON decks(user_id, lower(name))",
    "CREATE INDEX i_card_due ON cards(deck_id, due)",
    "CREATE INDEX i_card_new ON cards(deck_id, id) WHERE state IS NULL",
    "CREATE INDEX i_review_card ON reviews(card_id, ts)",
    "CREATE INDEX i_review_ts ON reviews(ts)",
)


def create_schema(c):
    for sql in TABLES:
        c.execute(sql)
    for sql in INDEXES:
        c.execute(sql)


class _Connection:
    def __init__(self, connection):
        self._connection = connection

    def __enter__(self):
        return self._connection

    def __exit__(self, exc_type, exc, tb):
        try:
            return self._connection.__exit__(exc_type, exc, tb)
        finally:
            self._connection.close()


def conn():
    c = sqlite3.connect(DATA_DIR / "decks.db", timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return _Connection(c)


def init():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DATA_DIR / "decks.db", timeout=10, isolation_level=None)
    c.row_factory = sqlite3.Row
    try:
        has_tables = c.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()
        if has_tables:
            version = c.execute("PRAGMA user_version").fetchone()[0]
            if version != SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema version {version} is not supported; "
                    f"expected {SCHEMA_VERSION}. Replace data/decks.db with a database created by this version."
                )
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA foreign_keys=ON")
            return

        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("BEGIN")
        try:
            create_schema(c)
            c.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            c.execute("COMMIT")
        except BaseException:
            c.execute("ROLLBACK")
            raise
    finally:
        c.close()
