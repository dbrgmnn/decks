from fastapi import HTTPException

NEW_STEPS = (1, 5, 10, 15, 20, 30)


def check_deck_name(c, folder_id, name, skip_id=0):
    if c.execute(
        "SELECT 1 FROM decks WHERE folder_id=? AND lower(name)=lower(?) AND id!=?",
        (folder_id, name, skip_id),
    ).fetchone():
        raise HTTPException(400, "A deck with this name already exists in this folder")


def check_folder_name(c, uid, name, skip_id=0):
    if c.execute(
        "SELECT 1 FROM folders WHERE user_id=? AND lower(name)=lower(?) AND id!=?",
        (uid, name, skip_id),
    ).fetchone():
        raise HTTPException(400, "A folder with this name already exists")


def introduced_today(c, deck_id, since):
    return c.execute(
        """SELECT COUNT(DISTINCT r.card_id)
        FROM reviews r
        JOIN cards c ON c.id = r.card_id
        WHERE c.deck_id=?
          AND r.ts>=?
          AND NOT EXISTS (SELECT 1 FROM reviews p WHERE p.card_id=r.card_id AND p.ts<?)
          AND NOT EXISTS (SELECT 1 FROM cards old WHERE old.id=r.card_id AND old.state IS NOT NULL AND old.due<?)""",
        (deck_id, since, since, since),
    ).fetchone()[0]
