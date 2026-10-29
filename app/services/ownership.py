from ..i18n import error


def own_deck(c, uid, deck_id):
    row = c.execute(
        "SELECT id, name, new_per_day, paused FROM decks WHERE id=? AND user_id=?",
        (deck_id, uid),
    ).fetchone()
    if not row:
        raise error(404, 'error.deck_not_found')
    return row


def own_card(c, uid, card_id):
    row = c.execute(
        "SELECT c.id, c.state, c.deck_id FROM cards c JOIN decks d ON d.id=c.deck_id WHERE c.id=? AND d.user_id=?",
        (card_id, uid),
    ).fetchone()
    if not row:
        raise error(404, 'error.card_not_found')
    return row
