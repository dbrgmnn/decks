from fastapi import APIRouter, Depends, Form, HTTPException, Request

from .. import auth, db
from ..services.decks import check_deck_name, check_folder_name
from ..services.ownership import own_folder
from ..services.validators import clean, clean_quick_add_name, normalize_name_key

router = APIRouter()


def _next_pos(c, table: str, uid: int) -> int:
    return c.execute(f'SELECT COALESCE(MAX(pos), 0) + 1 FROM {table} WHERE user_id=?', (uid,)).fetchone()[0]


def _get_or_create_folder(c, uid: int, name: str):
    key = normalize_name_key(name)
    rows = c.execute('SELECT id, name FROM folders WHERE user_id=?', (uid,)).fetchall()
    for row in rows:
        if normalize_name_key(row['name']) == key:
            return {'id': row['id'], 'name': row['name'], 'status': 'existing'}
    check_folder_name(c, uid, name)
    folder_id = c.execute(
        'INSERT INTO folders(user_id, name, pos) VALUES(?,?,?)',
        (uid, name, _next_pos(c, 'folders', uid)),
    ).lastrowid
    return {'id': folder_id, 'name': name, 'status': 'created'}


def _get_or_create_deck(c, uid: int, folder_id: int, name: str):
    key = normalize_name_key(name)
    rows = c.execute(
        'SELECT id, name FROM decks WHERE user_id=? AND folder_id=?',
        (uid, folder_id),
    ).fetchall()
    for row in rows:
        if normalize_name_key(row['name']) == key:
            return {'id': row['id'], 'name': row['name'], 'status': 'existing'}
    check_deck_name(c, folder_id, name)
    deck_id = c.execute(
        'INSERT INTO decks(user_id, folder_id, name, pos) VALUES(?,?,?,?)',
        (uid, folder_id, name, _next_pos(c, 'decks', uid)),
    ).lastrowid
    return {'id': deck_id, 'name': name, 'status': 'created'}


def _parse_quick_add(raw_text: str):
    has_comma = ',' in raw_text
    has_slash = '/' in raw_text
    if has_comma and has_slash:
        raise HTTPException(400, 'Use only / or ,')

    separator = ',' if has_comma else '/'
    parts = [part.strip() for part in raw_text.split(separator)] if (has_comma or has_slash) else [raw_text.strip()]

    if any(not part for part in parts):
        raise HTTPException(400, 'Empty part')
    if len(parts) == 3:
        raise HTTPException(400, 'Need front and back')
    if len(parts) > 5:
        raise HTTPException(400, 'Too many parts')
    if len(parts) not in (1, 2, 4, 5):
        raise HTTPException(400, 'Wrong format')
    return parts


def _apply_quick_add(c, uid: int, raw_text: str):
    parts = _parse_quick_add(raw_text)

    folder_name = clean_quick_add_name(parts[0], 'Folder name', 60)
    folder = _get_or_create_folder(c, uid, folder_name)
    result = {'ok': True, 'kind': 'folder', 'folder': folder}

    if len(parts) == 1:
        return result

    deck_name = clean_quick_add_name(parts[1], 'Deck name', 60)
    deck = _get_or_create_deck(c, uid, folder['id'], deck_name)
    result.update({'kind': 'deck', 'deck': deck})

    if len(parts) == 2:
        return result

    front = clean(parts[2], 'Front', 200)
    back = clean(parts[3], 'Back', 200)
    note = clean(parts[4] if len(parts) == 5 else '', 'Note', 300, required=False)
    exists = c.execute(
        'SELECT id FROM cards WHERE deck_id=? AND lower(front)=lower(?) AND lower(back)=lower(?)',
        (deck['id'], front, back),
    ).fetchone()
    if exists:
        result.update({
            'kind': 'card',
            'card': {'id': exists['id'], 'status': 'existing'},
        })
        return result

    card_id = c.execute(
        'INSERT INTO cards(deck_id, front, back, note) VALUES(?,?,?,?)',
        (deck['id'], front, back, note),
    ).lastrowid
    result.update({
        'kind': 'card',
        'card': {'id': card_id, 'status': 'created'},
    })
    return result


@router.post('/api/quick-add')
def quick_add(
    text: str = Form(''),
    name: str = Form(''),
    user=Depends(auth.current_user_or_token),
):
    uid = user['id']
    raw_text = text or name
    with db.conn() as c:
        return _apply_quick_add(c, uid, raw_text)


@router.put('/api/folders/{folder_id}')
def update_folder(folder_id: int, name: str = Form(...), user=Depends(auth.current_user)):
    name = clean_quick_add_name(name, 'Folder name', 60)
    uid = user['id']
    with db.conn() as c:
        own_folder(c, uid, folder_id)
        check_folder_name(c, uid, name, folder_id)
        c.execute('UPDATE folders SET name=? WHERE id=? AND user_id=?', (name, folder_id, uid))
    return {'ok': True}


@router.delete('/api/folders/{folder_id}')
def delete_folder(folder_id: int, user=Depends(auth.current_user)):
    uid = user['id']
    with db.conn() as c:
        own_folder(c, uid, folder_id)
        c.execute('DELETE FROM folders WHERE id=? AND user_id=?', (folder_id, uid))
    return {'ok': True}


@router.post('/api/folders/order')
async def order_folders(request: Request, user=Depends(auth.current_user)):
    form = await request.form()
    try:
        ids = [int(x) for x in form.getlist('ids')]
    except (TypeError, ValueError):
        raise HTTPException(400, 'Invalid folder order')
    uid = user['id']
    if not ids:
        return {'ok': True}
    if len(ids) != len(set(ids)):
        raise HTTPException(400, 'Invalid folder order')
    with db.conn() as c:
        owned = {r[0] for r in c.execute('SELECT id FROM folders WHERE user_id=?', (uid,))}
        if set(ids) - owned:
            raise HTTPException(400, 'Invalid folder order')
        for temp_pos, folder_id in enumerate(ids, 1):
            c.execute('UPDATE folders SET pos=? WHERE id=? AND user_id=?', (-temp_pos, folder_id, uid))
        for pos, folder_id in enumerate(ids, 1):
            c.execute('UPDATE folders SET pos=? WHERE id=? AND user_id=?', (pos, folder_id, uid))
    return {'ok': True}
