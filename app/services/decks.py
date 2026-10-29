from ..i18n import error

from .validators import normalize_name_key


NEW_PER_DAY_VALUES = (1, 5, 10, 15, 20, 30)


def parse_new_per_day(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise error(400, 'error.daily_limit_invalid')
    if value not in NEW_PER_DAY_VALUES:
        raise error(400, 'error.daily_limit_not_allowed')
    return value


def check_deck_name(c, uid, name, skip_id=0):
    key = normalize_name_key(name)
    rows = c.execute(
        "SELECT id, name FROM decks WHERE user_id=? AND id!=?",
        (uid, skip_id),
    ).fetchall()
    if any(normalize_name_key(row['name']) == key for row in rows):
        raise error(400, "error.deck_name_exists")


def next_deck_pos(c, uid):
    return c.execute(
        'SELECT COALESCE(MAX(pos), 0) + 1 FROM decks WHERE user_id=?', (uid,)
    ).fetchone()[0]


def get_or_create_deck(c, uid, name):
    """Return the user's deck with this name, creating it when missing."""
    key = normalize_name_key(name)
    rows = c.execute('SELECT id, name FROM decks WHERE user_id=?', (uid,)).fetchall()
    for row in rows:
        if normalize_name_key(row['name']) == key:
            return {'id': row['id'], 'name': row['name'], 'created': False}
    check_deck_name(c, uid, name)
    deck_id = c.execute(
        'INSERT INTO decks(user_id, name, pos) VALUES(?,?,?)',
        (uid, name, next_deck_pos(c, uid)),
    ).lastrowid
    return {'id': deck_id, 'name': name, 'created': True}


def introduced_counts(c, uid, since):
    rows = c.execute(
        """SELECT c.deck_id, COUNT(DISTINCT r.card_id)
        FROM reviews r
        JOIN cards c ON c.id=r.card_id
        JOIN decks d ON d.id=c.deck_id
        WHERE d.user_id=? AND r.ts>=? AND NOT EXISTS (
          SELECT 1 FROM reviews p WHERE p.card_id=r.card_id AND p.ts<?)
        GROUP BY c.deck_id""",
        (uid, since, since),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def introduced_today(c, deck_id, since):
    return c.execute(
        """SELECT COUNT(DISTINCT r.card_id)
        FROM reviews r
        JOIN cards c ON c.id = r.card_id
        WHERE c.deck_id=?
          AND r.ts>=?
          AND NOT EXISTS (SELECT 1 FROM reviews p WHERE p.card_id=r.card_id AND p.ts<?)""",
        (deck_id, since, since),
    ).fetchone()[0]
