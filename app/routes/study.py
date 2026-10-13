from fastapi import APIRouter, Depends, Form, HTTPException

from .. import auth, db, srs
from ..services.decks import introduced_today
from ..services.ownership import own_card, own_deck

router = APIRouter()


def _active_decks(c, uid):
    return c.execute('SELECT id, new_per_day FROM decks WHERE user_id=? AND paused=0 ORDER BY pos, id', (uid,)).fetchall()


@router.get('/api/next/active')
def next_active_card(user=Depends(auth.current_user)):
    uid = user['id']
    now = srs.now()
    today = srs.day_start(user['tz'])
    with db.conn() as c:
        decks = _active_decks(c, uid)
        if not decks:
            return None

        intro_rows = c.execute(
            """SELECT c.deck_id, COUNT(DISTINCT r.card_id)
            FROM reviews r
            JOIN cards c ON c.id=r.card_id
            JOIN decks d ON d.id=c.deck_id
            WHERE d.user_id=? AND d.paused=0 AND r.ts>=? AND NOT EXISTS (
              SELECT 1 FROM reviews p WHERE p.card_id=r.card_id AND p.ts<?)
            GROUP BY c.deck_id""",
            (uid, today, today),
        ).fetchall()
        introduced = {row[0]: row[1] for row in intro_rows}

        due_candidates = c.execute(
            """SELECT id, deck_id, front, back, note
            FROM cards
            WHERE deck_id IN (SELECT id FROM decks WHERE user_id=? AND paused=0)
              AND state IS NOT NULL AND due<=?
            ORDER BY RANDOM()
            LIMIT 1""",
            (uid, now),
        ).fetchone()

        due_left = c.execute(
            """SELECT COUNT(*)
            FROM cards
            WHERE deck_id IN (SELECT id FROM decks WHERE user_id=? AND paused=0)
              AND state IS NOT NULL AND due<=?""",
            (uid, now),
        ).fetchone()[0]

        actual_new_left = 0
        for deck in decks:
            unseen = c.execute('SELECT COUNT(*) FROM cards WHERE deck_id=? AND state IS NULL', (deck['id'],)).fetchone()[0]
            quota_left = max(0, int(deck['new_per_day']) - int(introduced.get(deck['id'], 0)))
            actual_new_left += min(unseen, quota_left)

        if due_candidates:
            return {
                'id': due_candidates['id'],
                'front': due_candidates['front'],
                'back': due_candidates['back'],
                'note': due_candidates['note'],
                'kind': 'review',
                'left': due_left + actual_new_left,
            }

        if actual_new_left <= 0:
            return None

        new_candidates = c.execute(
            """SELECT id, deck_id, front, back, note
            FROM cards
            WHERE deck_id IN (SELECT id FROM decks WHERE user_id=? AND paused=0)
              AND state IS NULL
            ORDER BY RANDOM()
            LIMIT 200""",
            (uid,),
        ).fetchall()

        for row in new_candidates:
            quota_left = 0
            deck_id = row['deck_id']
            for deck in decks:
                if deck['id'] == deck_id:
                    quota_left = max(0, int(deck['new_per_day']) - int(introduced.get(deck_id, 0)))
                    break
            if quota_left > 0:
                return {
                    'id': row['id'],
                    'front': row['front'],
                    'back': row['back'],
                    'note': row['note'],
                    'kind': 'new',
                    'left': actual_new_left,
                }
        return None


@router.get('/api/next/{deck_id}')
def next_card(deck_id: int, user=Depends(auth.current_user)):
    uid = user['id']
    now = srs.now()
    today = srs.day_start(user['tz'])
    with db.conn() as c:
        deck = own_deck(c, uid, deck_id)
        # New-card quota is calculated per user's local day.
        seen_today = introduced_today(c, deck_id, today)
        new_left = max(0, int(deck['new_per_day']) - seen_today)
        unseen = c.execute(
            'SELECT COUNT(*) FROM cards WHERE deck_id=? AND state IS NULL',
            (deck_id,),
        ).fetchone()[0]
        actual_new_left = min(unseen, new_left)
        # Due review cards always come before unseen cards.
        due_row = c.execute(
            """SELECT id, front, back, note
            FROM cards
            WHERE deck_id=? AND state IS NOT NULL AND due<=?
            ORDER BY RANDOM()
            LIMIT 1""",
            (deck_id, now),
        ).fetchone()
        if due_row:
            due_left = c.execute(
                'SELECT COUNT(*) FROM cards WHERE deck_id=? AND state IS NOT NULL AND due<=?',
                (deck_id, now),
            ).fetchone()[0]
            return {
                'id': due_row['id'],
                'front': due_row['front'],
                'back': due_row['back'],
                'note': due_row['note'],
                'kind': 'review',
                'left': due_left + actual_new_left,
            }
        if actual_new_left <= 0:
            return None
        new_row = c.execute(
            """SELECT id, front, back, note
            FROM cards
            WHERE deck_id=? AND state IS NULL
            ORDER BY RANDOM()
            LIMIT 1""",
            (deck_id,),
        ).fetchone()
        if not new_row:
            return None
    return {
        'id': new_row['id'],
        'front': new_row['front'],
        'back': new_row['back'],
        'note': new_row['note'],
        'kind': 'new',
        'left': actual_new_left,
    }


@router.post('/api/rate/{card_id}')
def rate_card(card_id: int, rating: int = Form(...), user=Depends(auth.current_user)):
    if rating not in (1, 2, 3, 4):
        raise HTTPException(400, 'Rating must be between 1 and 4')
    uid = user['id']
    ts = srs.now()
    with db.conn() as c:
        row = own_card(c, uid, card_id)
        # FSRS updates both the serialized state and the next due timestamp.
        state_json, due = srs.review(row['state'], rating)
        c.execute('UPDATE cards SET state=?, due=? WHERE id=?', (state_json, due, card_id))
        c.execute('INSERT INTO reviews(card_id, rating, ts) VALUES(?,?,?)', (card_id, rating, ts))
    return {'ok': True}
