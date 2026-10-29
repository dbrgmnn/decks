import unicodedata


def _key(value):
    return unicodedata.normalize('NFC', value).strip().casefold()


def card_key(front, back):
    """Case- and Unicode-insensitive identity of a card inside one deck."""
    return (_key(front), _key(back))


def find_duplicate(c, deck_id, front, back, exclude_id=0):
    """Return an existing card with the same front/back, or None."""
    key = card_key(front, back)
    rows = c.execute(
        'SELECT id, front, back, note, tags FROM cards WHERE deck_id=? AND id<>?',
        (deck_id, exclude_id),
    ).fetchall()
    for row in rows:
        if card_key(row['front'], row['back']) == key:
            return row
    return None
