import unicodedata


def _key(value):
    return ' '.join(unicodedata.normalize('NFC', value).split()).casefold()


def front_key(front):
    """Case-, whitespace- and Unicode-insensitive identity of a card in a deck."""
    return _key(front)


def find_duplicate(c, deck_id, front, exclude_id=0):
    """Return an existing card with the same front, or None."""
    key = front_key(front)
    rows = c.execute(
        'SELECT id, front, back, note, tags FROM cards WHERE deck_id=? AND id<>?',
        (deck_id, exclude_id),
    ).fetchall()
    for row in rows:
        if front_key(row['front']) == key:
            return row
    return None
