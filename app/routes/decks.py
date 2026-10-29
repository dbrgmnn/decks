from fastapi import APIRouter, Depends, Form, Request

from .. import auth, db
from ..i18n import error
from ..services.decks import check_deck_name, next_deck_pos, parse_new_per_day
from ..services.ownership import own_deck
from ..services.tags import tags_from_db
from ..services.validators import clean_deck_name

router = APIRouter()


@router.post('/api/decks')
def create_deck(name: str = Form(...), user=Depends(auth.current_user)):
    name = clean_deck_name(name, 'field.deck_name', 60)
    uid = user['id']
    with db.conn() as c:
        check_deck_name(c, uid, name)
        pos = next_deck_pos(c, uid)
        deck_id = c.execute(
            'INSERT INTO decks(user_id, name, pos) VALUES(?,?,?)',
            (uid, name, pos),
        ).lastrowid
    return {'ok': True, 'id': deck_id}


@router.put('/api/decks/{deck_id}')
def update_deck(
    deck_id: int,
    name: str = Form(...),
    new_per_day: str = Form(...),
    paused: int = Form(0),
    user=Depends(auth.current_user),
):
    name = clean_deck_name(name, 'field.deck_name', 60)
    new_per_day = parse_new_per_day(new_per_day)
    uid = user['id']
    with db.conn() as c:
        own_deck(c, uid, deck_id)
        check_deck_name(c, uid, name, deck_id)
        c.execute(
            'UPDATE decks SET name=?, new_per_day=?, paused=? WHERE id=? AND user_id=?',
            (name, new_per_day, 1 if paused else 0, deck_id, uid),
        )
    return {'ok': True}


@router.post('/api/decks/{deck_id}/settings')
def update_deck_settings(
    deck_id: int,
    new_per_day: str = Form(...),
    paused: int = Form(0),
    user=Depends(auth.current_user),
):
    """Change only the quick study settings shown on a deck."""
    uid = user['id']
    with db.conn() as c:
        own_deck(c, uid, deck_id)
        new_per_day = parse_new_per_day(new_per_day)
        c.execute(
            'UPDATE decks SET new_per_day=?, paused=? WHERE id=? AND user_id=?',
            (new_per_day, 1 if paused else 0, deck_id, uid),
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
            'SELECT id, front, back, note, tags FROM cards WHERE deck_id=? ORDER BY id DESC',
            (deck_id,),
        ).fetchall()
    return [
        {
            'id': row['id'],
            'front': row['front'],
            'back': row['back'],
            'note': row['note'],
            'tags': tags_from_db(row['tags']),
        }
        for row in rows
    ]


@router.post('/api/decks/order')
async def order_decks(request: Request, user=Depends(auth.current_user)):
    form = await request.form()
    try:
        ids = [int(x) for x in form.getlist('ids')]
    except (TypeError, ValueError):
        raise error(400, 'error.deck_order_invalid')
    uid = user['id']
    if not ids:
        return {'ok': True}
    if len(ids) != len(set(ids)):
        raise error(400, 'error.deck_order_invalid')
    with db.conn() as c:
        all_ids = [r[0] for r in c.execute(
            'SELECT id FROM decks WHERE user_id=? ORDER BY pos, id',
            (uid,),
        ).fetchall()]
        owned = set(all_ids)
        subset = set(ids)
        if subset - owned:
            raise error(400, 'error.deck_order_invalid')
        # Keep decks outside this view in place; only reshuffle the submitted subset.
        it = iter(ids)
        ordered = [next(it) if deck_id in subset else deck_id for deck_id in all_ids]
        for temp_pos, deck_id in enumerate(ordered, 1):
            c.execute('UPDATE decks SET pos=? WHERE id=? AND user_id=?', (-temp_pos, deck_id, uid))
        for pos, deck_id in enumerate(ordered, 1):
            c.execute('UPDATE decks SET pos=? WHERE id=? AND user_id=?', (pos, deck_id, uid))
    return {'ok': True}
