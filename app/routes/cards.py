from fastapi import APIRouter, Depends, Form

from .. import auth, db
from ..i18n import error
from ..services.ownership import own_card, own_deck
from ..services.validators import clean

router = APIRouter()


@router.post('/api/cards')
def create_card(
    deck_id: int = Form(...),
    front: str = Form(...),
    back: str = Form(...),
    note: str = Form(''),
    user=Depends(auth.current_user),
):
    front = clean(front, 'field.front', 200)
    back = clean(back, 'field.back', 200)
    note = clean(note, 'field.note', 300, required=False)
    uid = user['id']
    with db.conn() as c:
        # A card can be created only inside a deck owned by the current user.
        own_deck(c, uid, deck_id)
        # Duplicate detection is scoped to the same deck.
        exists = c.execute(
            'SELECT 1 FROM cards WHERE deck_id=? AND lower(front)=lower(?) AND lower(back)=lower(?)',
            (deck_id, front, back),
        ).fetchone()
        if exists:
            raise error(400, 'error.card_exists')
        card_id = c.execute(
            'INSERT INTO cards(deck_id, front, back, note) VALUES(?,?,?,?)',
            (deck_id, front, back, note),
        ).lastrowid
    return {'ok': True, 'id': card_id}


@router.put('/api/cards/{card_id}')
def update_card(
    card_id: int,
    front: str = Form(...),
    back: str = Form(...),
    note: str = Form(''),
    user=Depends(auth.current_user),
):
    front = clean(front, 'field.front', 200)
    back = clean(back, 'field.back', 200)
    note = clean(note, 'field.note', 300, required=False)
    uid = user['id']
    with db.conn() as c:
        row = own_card(c, uid, card_id)
        # Use the card's current deck to keep duplicate checks local to that deck.
        exists = c.execute(
            'SELECT 1 FROM cards WHERE deck_id=? AND lower(front)=lower(?) AND lower(back)=lower(?) AND id<>?',
            (row['deck_id'], front, back, card_id),
        ).fetchone()
        if exists:
            raise error(400, 'error.card_exists')
        c.execute(
            'UPDATE cards SET front=?, back=?, note=? WHERE id=?',
            (front, back, note, card_id),
        )
    return {'ok': True}


@router.delete('/api/cards/{card_id}')
def delete_card(card_id: int, user=Depends(auth.current_user)):
    uid = user['id']
    with db.conn() as c:
        own_card(c, uid, card_id)
        c.execute('DELETE FROM cards WHERE id=?', (card_id,))
    return {'ok': True}
