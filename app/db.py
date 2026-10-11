import pathlib
import sqlite3

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"

USERS_SQL = """
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

FOLDERS_SQL = """
CREATE TABLE folders(
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  pos INTEGER NOT NULL DEFAULT 0,
  UNIQUE(id, user_id),
  UNIQUE(user_id, pos)
)
"""

DECKS_SQL = """
CREATE TABLE decks(
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
CREATE TABLE cards(
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
CREATE TABLE reviews(
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


def conn():
    c = sqlite3.connect(DATA_DIR / "decks.db", timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def init():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DATA_DIR / "decks.db", timeout=10, isolation_level=None)
    try:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        has_users = c.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        if has_users:
            return

        c.execute("BEGIN")
        for name in ORDER:
            c.execute(TABLES[name])
        for sql in INDEXES:
            c.execute(sql)
        c.execute("COMMIT")
    except BaseException:
        c.execute("ROLLBACK")
        raise
    finally:
        c.close()
