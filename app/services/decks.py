from fastapi import HTTPException

from .validators import normalize_name_key


def check_deck_name(c, folder_id, name, skip_id=0):
    key = normalize_name_key(name)
    rows = c.execute(
        "SELECT id, name FROM decks WHERE folder_id=? AND id!=?",
        (folder_id, skip_id),
    ).fetchall()
    if any(normalize_name_key(row['name']) == key for row in rows):
        raise HTTPException(400, "A deck with this name already exists in this folder")


def check_folder_name(c, uid, name, skip_id=0):
    key = normalize_name_key(name)
    rows = c.execute(
        "SELECT id, name FROM folders WHERE user_id=? AND id!=?",
        (uid, skip_id),
    ).fetchall()
    if any(normalize_name_key(row['name']) == key for row in rows):
        raise HTTPException(400, "A folder with this name already exists")


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
