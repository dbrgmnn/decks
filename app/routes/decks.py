from fastapi import APIRouter, Depends, Form, HTTPException, Request

from .. import auth, db
from ..services.decks import check_deck_name
from ..services.ownership import need_folder, own_deck
from ..services.validators import clean_quick_add_name

router = APIRouter()


@router.post('/api/decks')
def create_deck(name: str = Form(...), folder_id: int = Form(...), user=Depends(auth.current_user)):
    name = clean_quick_add_name(name, 'Deck name', 60)
    uid = user['id']
    with db.conn() as c:
        # A deck must belong to a folder owned by the same user.
        folder_id = need_folder(c, uid, folder_id)
        check_deck_name(c, folder_id, name)
        pos = c.execute('SELECT COALESCE(MAX(pos), 0) + 1 FROM decks WHERE user_id=?', (uid,)).fetchone()[0]
        deck_id = c.execute(
            'INSERT INTO decks(user_id, folder_id, name, pos) VALUES(?,?,?,?)',
            (uid, folder_id, name, pos),
        ).lastrowid
    return {'ok': True, 'id': deck_id}


@router.put('/api/decks/{deck_id}')
def update_deck(
    deck_id: int,
    name: str = Form(...),
    folder_id: int = Form(...),
    new_per_day: str = Form(...),
    paused: int = Form(0),
    user=Depends(auth.current_user),
):
    name = clean_quick_add_name(name, 'Deck name', 60)
    try:
        new_per_day = int(new_per_day)
    except (TypeError, ValueError):
        raise HTTPException(400, 'Choose a valid daily limit')
    if new_per_day not in (1, 5, 10, 15, 20, 30):
        raise HTTPException(400, 'Choose one of the allowed daily limits')
    uid = user['id']
    with db.conn() as c:
        own_deck(c, uid, deck_id)
        # Moving a deck is allowed only inside the current user's folders.
        folder_id = need_folder(c, uid, folder_id)
        check_deck_name(c, folder_id, name, deck_id)
        c.execute(
            'UPDATE decks SET name=?, folder_id=?, new_per_day=?, paused=? WHERE id=? AND user_id=?',
            (name, folder_id, new_per_day, 1 if paused else 0, deck_id, uid),
        )
    return {'ok': True}


@router.delete('/api/decks/{deck_id}')
def delete_deck(deck_id: int, user=Depends(auth.current_user)):
    uid = user['id']
    with db.conn() as c:
        own_deck(c, uid, deck_id)
        c.execute('DELETE FROM decks WHERE id=? AND user_id=?', (deck_id, uid))
    return {'ok': True}


@router.get('/api/decks/{deck_id}/cards')
def deck_cards(deck_id: int, user=Depends(auth.current_user)):
    uid = user['id']
    with db.conn() as c:
        own_deck(c, uid, deck_id)
        rows = c.execute(
            'SELECT id, front, back, note FROM cards WHERE deck_id=? ORDER BY id DESC',
            (deck_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.post('/api/decks/order')
async def order_decks(request: Request, user=Depends(auth.current_user)):
    form = await request.form()
    try:
        ids = [int(x) for x in form.getlist('ids')]
    except (TypeError, ValueError):
        raise HTTPException(400, 'Invalid deck order')
    uid = user['id']
    if not ids:
        return {'ok': True}
    if len(ids) != len(set(ids)):
        raise HTTPException(400, 'Invalid deck order')
    with db.conn() as c:
        all_ids = [r[0] for r in c.execute(
            'SELECT id FROM decks WHERE user_id=? ORDER BY pos, id',
            (uid,),
        ).fetchall()]
        owned = set(all_ids)
        subset = set(ids)
        if subset - owned:
            raise HTTPException(400, 'Invalid deck order')
        # Keep decks outside this view in place; only reshuffle the submitted subset.
        it = iter(ids)
        ordered = [next(it) if deck_id in subset else deck_id for deck_id in all_ids]
        for temp_pos, deck_id in enumerate(ordered, 1):
            c.execute('UPDATE decks SET pos=? WHERE id=? AND user_id=?', (-temp_pos, deck_id, uid))
        for pos, deck_id in enumerate(ordered, 1):
            c.execute('UPDATE decks SET pos=? WHERE id=? AND user_id=?', (pos, deck_id, uid))
    return {'ok': True}


@router.post('/api/decks/{deck_id}/pin')
def pin_deck(deck_id: int, pinned: int = Form(...), user=Depends(auth.current_user)):
    uid = user['id']
    with db.conn() as c:
        own_deck(c, uid, deck_id)
        c.execute('UPDATE decks SET pinned=? WHERE id=? AND user_id=?', (1 if pinned else 0, deck_id, uid))
    return {'ok': True}
