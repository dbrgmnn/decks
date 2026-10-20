import pathlib
import sqlite3

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"

USERS_SQL = """
CREATE TABLE IF NOT EXISTS users(
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

FOLDERS_SQL = """
CREATE TABLE IF NOT EXISTS folders(
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  pos INTEGER NOT NULL DEFAULT 0,
  UNIQUE(id, user_id),
  UNIQUE(user_id, pos)
)
"""

DECKS_SQL = """
CREATE TABLE IF NOT EXISTS decks(
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  folder_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  pos INTEGER NOT NULL DEFAULT 0,
  new_per_day INTEGER NOT NULL DEFAULT 10 CHECK(new_per_day IN (1, 5, 10, 15, 20, 30)),
  paused INTEGER NOT NULL DEFAULT 0 CHECK(paused IN (0, 1)),
  pinned INTEGER NOT NULL DEFAULT 0 CHECK(pinned IN (0, 1)),
  FOREIGN KEY(folder_id, user_id) REFERENCES folders(id, user_id) ON DELETE CASCADE,
  UNIQUE(user_id, pos)
)
"""

CARDS_SQL = """
CREATE TABLE IF NOT EXISTS cards(
  id INTEGER PRIMARY KEY,
  deck_id INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
  front TEXT NOT NULL,
  back TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  state TEXT,
  due TEXT
)
"""

REVIEWS_SQL = """
CREATE TABLE IF NOT EXISTS reviews(
  id INTEGER PRIMARY KEY,
  card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 4),
  ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

# Tables are created in dependency order.
TABLES = {
    "users": USERS_SQL,
    "folders": FOLDERS_SQL,
    "decks": DECKS_SQL,
    "cards": CARDS_SQL,
    "reviews": REVIEWS_SQL,
}

INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS i_user_email ON users(lower(email))",
    "CREATE UNIQUE INDEX IF NOT EXISTS i_folder_name ON folders(user_id, lower(name))",
    "CREATE UNIQUE INDEX IF NOT EXISTS i_deck_name ON decks(folder_id, lower(name))",
    "CREATE INDEX IF NOT EXISTS i_deck_user ON decks(user_id, pos)",
    "CREATE INDEX IF NOT EXISTS i_card_due ON cards(deck_id, due)",
    "CREATE INDEX IF NOT EXISTS i_card_new ON cards(deck_id, id) WHERE state IS NULL",
    "CREATE INDEX IF NOT EXISTS i_review_card ON reviews(card_id, ts)",
    "CREATE INDEX IF NOT EXISTS i_review_ts ON reviews(ts)",
]

ORDER = ["users", "folders", "decks", "cards", "reviews"]

# Bump SCHEMA_VERSION and add a step to MIGRATIONS when the schema changes.
# Existing databases are upgraded in order; fresh ones run every step.
SCHEMA_VERSION = 3


def _migrate_1(c):
    for name in ORDER:
        c.execute(TABLES[name])
    for sql in INDEXES:
        c.execute(sql)


def _migrate_2(c):
    # token_version lets a password change or sign-out invalidate old sessions.
    columns = {row[1] for row in c.execute("PRAGMA table_info(users)")}
    if "token_version" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0")


def _migrate_3(c):
    # Empty lang means "follow the browser"; en/de are explicit choices.
    columns = {row[1] for row in c.execute("PRAGMA table_info(users)")}
    if "lang" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN lang TEXT NOT NULL DEFAULT ''")


# version -> callable applying the change that brings the database to it.
MIGRATIONS = {
    1: _migrate_1,
    2: _migrate_2,
    3: _migrate_3,
}


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
    try:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        version = c.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {version} is newer than this app ({SCHEMA_VERSION}); upgrade the app"
            )
        if version == SCHEMA_VERSION:
            return

        c.execute("BEGIN")
        try:
            # Databases created before schema versioning report 0 but already
            # hold the version 1 tables, so the first step stays idempotent.
            for target in range(version + 1, SCHEMA_VERSION + 1):
                MIGRATIONS[target](c)
            c.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            c.execute("COMMIT")
        except BaseException:
            c.execute("ROLLBACK")
            raise
    finally:
        c.close()
