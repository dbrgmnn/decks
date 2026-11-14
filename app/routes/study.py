from fastapi import APIRouter, Depends, Form

from .. import auth, db, srs
from ..i18n import error
from ..services.decks import introduced_counts, introduced_today
from ..services.ownership import own_card, own_deck
from ..services.tags import tags_from_db

router = APIRouter()


def _active_decks(c, uid):
    return c.execute('SELECT id, new_per_day FROM decks WHERE user_id=? AND paused=0 ORDER BY pos, id', (uid,)).fetchall()


# FSRS state numbers: 1 = learning, 2 = review, 3 = relearning. Malformed
# state text is treated as a graduated review so it is never served as new.
_STATE_NUMBER = "COALESCE(CASE WHEN json_valid(state) THEN json_extract(state, '$.state') END, 0)"
_REVIEW_CONDITION = f"{_STATE_NUMBER} NOT IN (1, 3)"
_LEARNING_CONDITION = f"{_STATE_NUMBER} IN (1, 3)"


def _card_payload(row, left):
    return {
        'id': row['id'],
        'deck_id': row['deck_id'],
        'front': row['front'],
        'back': row['back'],
        'note': row['note'],
        'tags': tags_from_db(row['tags']),
        'kind': srs.card_kind(row['state']),
        'state': row['state'],
        'due': row['due'],
        'left': left,
    }


@router.get('/api/next/active')
def next_active_card(user=Depends(auth.current_user)):
    uid = user['id']
    now = srs.now()
    today = srs.day_start(user['tz'])
    with db.conn() as c:
        decks = _active_decks(c, uid)
        if not decks:
            return None

        introduced = introduced_counts(c, uid, today)

        # Session order: accumulated reviews, then today's new quota, then
        # cards already rated in this session (learning and relearning).
        due_review = c.execute(
            f"""SELECT id, deck_id, front, back, note, tags, state, due
            FROM cards
            WHERE deck_id IN (SELECT id FROM decks WHERE user_id=? AND paused=0)
              AND state IS NOT NULL AND due<=? AND {_REVIEW_CONDITION}
            ORDER BY RANDOM()
            LIMIT 1""",
            (uid, now),
        ).fetchone()
        review_left = c.execute(
            f"""SELECT COUNT(*)
            FROM cards
            WHERE deck_id IN (SELECT id FROM decks WHERE user_id=? AND paused=0)
              AND state IS NOT NULL AND due<=? AND {_REVIEW_CONDITION}""",
            (uid, now),
        ).fetchone()[0]
        learning_left = c.execute(
            f"""SELECT COUNT(*)
            FROM cards
            WHERE deck_id IN (SELECT id FROM decks WHERE user_id=? AND paused=0)
              AND state IS NOT NULL AND due<=? AND {_LEARNING_CONDITION}""",
            (uid, now),
        ).fetchone()[0]

        # One grouped count instead of a query per deck.
        unseen_by_deck = dict(c.execute(
            """SELECT deck_id, COUNT(*) FROM cards
            WHERE state IS NULL AND deck_id IN (SELECT id FROM decks WHERE user_id=? AND paused=0)
            GROUP BY deck_id""",
            (uid,),
        ).fetchall())

        actual_new_left = 0
        eligible_new_decks = []
        for deck in decks:
            quota_left = max(0, int(deck['new_per_day']) - int(introduced.get(deck['id'], 0)))
            can_new = min(int(unseen_by_deck.get(deck['id'], 0)), quota_left)
            actual_new_left += can_new
            if can_new > 0:
                eligible_new_decks.append(deck['id'])

        left = review_left + learning_left + actual_new_left

        if due_review:
            return _card_payload(due_review, left)

        if actual_new_left > 0 and eligible_new_decks:
            placeholders = ','.join('?' * len(eligible_new_decks))
            new_row = c.execute(
                f"""SELECT id, deck_id, front, back, note, tags, state, due
                FROM cards
                WHERE deck_id IN ({placeholders}) AND state IS NULL
                ORDER BY RANDOM()
                LIMIT 1""",
                eligible_new_decks,
            ).fetchone()
            if new_row:
                return _card_payload(new_row, left)

        due_learning = c.execute(
            f"""SELECT id, deck_id, front, back, note, tags, state, due
            FROM cards
            WHERE deck_id IN (SELECT id FROM decks WHERE user_id=? AND paused=0)
              AND state IS NOT NULL AND due<=? AND {_LEARNING_CONDITION}
            ORDER BY RANDOM()
            LIMIT 1""",
            (uid, now),
        ).fetchone()
        if due_learning:
            return _card_payload(due_learning, left)
        return None


@router.get('/api/next/{deck_id}')
def next_card(deck_id: int, user=Depends(auth.current_user)):
    uid = user['id']
    now = srs.now()
    today = srs.day_start(user['tz'])
    with db.conn() as c:
        deck = own_deck(c, uid, deck_id)
        # A paused deck is not studied from the API either.
        if deck['paused']:
            return None
        # New-card quota is calculated per user's local day.
        seen_today = introduced_today(c, deck_id, today)
        new_left = max(0, int(deck['new_per_day']) - seen_today)
        unseen = c.execute(
            'SELECT COUNT(*) FROM cards WHERE deck_id=? AND state IS NULL',
            (deck_id,),
        ).fetchone()[0]
        actual_new_left = min(unseen, new_left)

        review_left = c.execute(
            f"""SELECT COUNT(*) FROM cards
            WHERE deck_id=? AND state IS NOT NULL AND due<=? AND {_REVIEW_CONDITION}""",
            (deck_id, now),
        ).fetchone()[0]
        learning_left = c.execute(
            f"""SELECT COUNT(*) FROM cards
            WHERE deck_id=? AND state IS NOT NULL AND due<=? AND {_LEARNING_CONDITION}""",
            (deck_id, now),
        ).fetchone()[0]
        left = review_left + learning_left + actual_new_left

        # Same order as the active queue: accumulated reviews, new cards, then
        # cards rated earlier in this session.
        due_review = c.execute(
            f"""SELECT id, deck_id, front, back, note, tags, state, due
            FROM cards
            WHERE deck_id=? AND state IS NOT NULL AND due<=? AND {_REVIEW_CONDITION}
            ORDER BY RANDOM()
            LIMIT 1""",
            (deck_id, now),
        ).fetchone()
        if due_review:
            return _card_payload(due_review, left)

        if actual_new_left > 0:
            new_row = c.execute(
                """SELECT id, deck_id, front, back, note, tags, state, due
                FROM cards
                WHERE deck_id=? AND state IS NULL
                ORDER BY RANDOM()
                LIMIT 1""",
                (deck_id,),
            ).fetchone()
            if new_row:
                return _card_payload(new_row, left)

        due_learning = c.execute(
            f"""SELECT id, deck_id, front, back, note, tags, state, due
            FROM cards
            WHERE deck_id=? AND state IS NOT NULL AND due<=? AND {_LEARNING_CONDITION}
            ORDER BY RANDOM()
            LIMIT 1""",
            (deck_id, now),
        ).fetchone()
        if due_learning:
            return _card_payload(due_learning, left)
        return None


@router.post('/api/rate/{card_id}')
def rate_card(card_id: int, rating: int = Form(...), user=Depends(auth.current_user)):
    if rating not in (1, 2, 3, 4):
        raise error(400, 'error.rating_range')
    uid = user['id']
    ts = srs.now()
    with db.conn() as c:
        row = own_card(c, uid, card_id)
        # FSRS updates both the serialized state and the next due timestamp.
        state_json, due = srs.review(row['state'], rating)
        c.execute('UPDATE cards SET state=?, due=? WHERE id=?', (state_json, due, card_id))
        c.execute('INSERT INTO reviews(card_id, rating, ts) VALUES(?,?,?)', (card_id, rating, ts))
    return {'ok': True}


@router.post('/api/undo/{card_id}')
def undo_card(card_id: int, prev_state: str = Form(''), prev_due: str = Form(''), user=Depends(auth.current_user)):
    uid = user['id']
    with db.conn() as c:
        own_card(c, uid, card_id)
        last = c.execute(
            'SELECT id FROM reviews WHERE card_id=? ORDER BY ts DESC, id DESC LIMIT 1',
            (card_id,),
        ).fetchone()
        if not last:
            raise error(400, 'error.nothing_to_undo')
        c.execute('DELETE FROM reviews WHERE id=?', (last['id'],))
        c.execute(
            'UPDATE cards SET state=?, due=? WHERE id=?',
            (prev_state if prev_state else None, prev_due if prev_due else None, card_id),
        )
    return {'ok': True}
