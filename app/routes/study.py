from fastapi import APIRouter, Depends, Form, HTTPException

from .. import auth, db, srs
from ..services.decks import introduced_today
from ..services.ownership import own_card, own_deck

router = APIRouter()


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
            ORDER BY due, id
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
                'left': due_left + actual_new_left,
            }
        if actual_new_left <= 0:
            return None
        new_row = c.execute(
            """SELECT id, front, back, note
            FROM cards
            WHERE deck_id=? AND state IS NULL
            ORDER BY id
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
