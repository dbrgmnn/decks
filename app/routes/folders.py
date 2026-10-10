from fastapi import APIRouter, Depends, Form, HTTPException, Request

from .. import auth, db
from ..services.decks import check_folder_name
from ..services.ownership import own_folder
from ..services.validators import clean

router = APIRouter()


@router.post('/api/folders')
def create_folder(name: str = Form(...), user=Depends(auth.current_user)):
    name = clean(name, 'Folder name', 60)
    uid = user['id']
    with db.conn() as c:
        check_folder_name(c, uid, name)
        pos = c.execute('SELECT COALESCE(MAX(pos), 0) + 1 FROM folders WHERE user_id=?', (uid,)).fetchone()[0]
        folder_id = c.execute('INSERT INTO folders(user_id, name, pos) VALUES(?,?,?)', (uid, name, pos)).lastrowid
    return {'ok': True, 'id': folder_id}


@router.put('/api/folders/{folder_id}')
def update_folder(folder_id: int, name: str = Form(...), user=Depends(auth.current_user)):
    name = clean(name, 'Folder name', 60)
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
    ids = [int(x) for x in form.getlist('ids')]
    uid = user['id']
    if not ids:
        return {'ok': True}
    with db.conn() as c:
        owned = {r[0] for r in c.execute('SELECT id FROM folders WHERE user_id=?', (uid,))}
        if set(ids) - owned:
            raise HTTPException(400, 'Invalid folder order')
        for temp_pos, folder_id in enumerate(ids, 1):
            c.execute('UPDATE folders SET pos=? WHERE id=? AND user_id=?', (-temp_pos, folder_id, uid))
        for pos, folder_id in enumerate(ids, 1):
            c.execute('UPDATE folders SET pos=? WHERE id=? AND user_id=?', (pos, folder_id, uid))
    return {'ok': True}
