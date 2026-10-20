import csv
import io

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from .. import auth, db
from ..i18n import error
from ..services.decks import check_deck_name, check_folder_name
from ..services.ownership import own_deck, own_folder
from ..services.validators import clean

router = APIRouter()

CSV_FIELDS = ['folder', 'deck', 'front', 'back', 'note']

# A reasonable upper bound for a text CSV of flashcards.
MAX_CSV_BYTES = 5 * 1024 * 1024


@router.post('/api/export/cards.csv')
def export_cards_csv(
    scope: str = Form('all'),
    folder_id: int = Form(0),
    deck_id: int = Form(0),
    user=Depends(auth.current_user),
):
    uid = user['id']
    sql = '''SELECT f.name AS folder, d.name AS deck, c.front, c.back, c.note
             FROM cards c
             JOIN decks d ON d.id = c.deck_id
             JOIN folders f ON f.id = d.folder_id AND f.user_id = d.user_id
             WHERE d.user_id = ?'''
    params = [uid]
    with db.conn() as c:
        if scope == 'folder':
            if not folder_id:
                raise error(400, 'error.export_folder_required')
            folder_id = own_folder(c, uid, folder_id)
            sql += ' AND d.folder_id = ?'
            params.append(folder_id)
        elif scope == 'deck':
            if not deck_id:
                raise error(400, 'error.export_deck_required')
            deck = own_deck(c, uid, deck_id)
            sql += ' AND d.id = ?'
            params.append(deck['id'])
        elif scope != 'all':
            raise error(400, 'error.export_scope_invalid')
        sql += ' ORDER BY f.pos, f.id, d.pos, d.id, c.id DESC'
        rows = c.execute(sql, params).fetchall()

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row[key] or '' for key in CSV_FIELDS})
    out = io.BytesIO(buf.getvalue().encode('utf-8-sig'))
    return StreamingResponse(
        out,
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="decks-cards.csv"'},
    )


@router.post('/api/import/cards.csv')
def import_cards_csv(file: UploadFile = File(...), user=Depends(auth.current_user)):
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise error(400, 'error.csv_file_required')
    raw = file.file.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        raise error(413, 'error.csv_too_large')
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise error(400, 'error.csv_not_utf8')
    try:
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames != CSV_FIELDS:
            raise error(400, 'error.csv_columns')
        rows = list(reader)
    except csv.Error:
        # A malformed file or a single field past csv's size limit.
        raise error(400, 'error.csv_unparseable')

    if not rows:
        return {'ok': True, 'folders': 0, 'decks': 0, 'cards': 0}

    uid = user['id']
    created_folders = 0
    created_decks = 0
    created_cards = 0

    with db.conn() as c:
        folder_cache = {r['name'].casefold(): r['id'] for r in c.execute('SELECT id, name FROM folders WHERE user_id=?', (uid,))}
        deck_cache = {
            (r['folder_id'], r['name'].casefold()): r['id']
            for r in c.execute('SELECT id, folder_id, name FROM decks WHERE user_id=?', (uid,))
        }

        for i, row in enumerate(rows, 2):
            folder = clean(row.get('folder', ''), 'field.folder', 60, line=i)
            deck = clean(row.get('deck', ''), 'field.deck', 60, line=i)
            front = clean(row.get('front', ''), 'field.front', 200, line=i)
            back = clean(row.get('back', ''), 'field.back', 200, line=i)
            note = clean(row.get('note', ''), 'field.note', 300, required=False, line=i)

            folder_key = folder.casefold()
            folder_id = folder_cache.get(folder_key)
            if not folder_id:
                check_folder_name(c, uid, folder)
                pos = c.execute('SELECT COALESCE(MAX(pos), 0) + 1 FROM folders WHERE user_id=?', (uid,)).fetchone()[0]
                folder_id = c.execute(
                    'INSERT INTO folders(user_id, name, pos) VALUES(?,?,?)',
                    (uid, folder, pos),
                ).lastrowid
                folder_cache[folder_key] = folder_id
                created_folders += 1

            deck_key = (folder_id, deck.casefold())
            deck_id = deck_cache.get(deck_key)
            if not deck_id:
                check_deck_name(c, folder_id, deck)
                pos = c.execute('SELECT COALESCE(MAX(pos), 0) + 1 FROM decks WHERE user_id=?', (uid,)).fetchone()[0]
                deck_id = c.execute(
                    'INSERT INTO decks(user_id, folder_id, name, pos) VALUES(?,?,?,?)',
                    (uid, folder_id, deck, pos),
                ).lastrowid
                deck_cache[deck_key] = deck_id
                created_decks += 1

            exists = c.execute(
                'SELECT 1 FROM cards WHERE deck_id=? AND lower(front)=lower(?) AND lower(back)=lower(?)',
                (deck_id, front, back),
            ).fetchone()
            if exists:
                continue
            c.execute(
                'INSERT INTO cards(deck_id, front, back, note) VALUES(?,?,?,?)',
                (deck_id, front, back, note),
            )
            created_cards += 1

    return {'ok': True, 'folders': created_folders, 'decks': created_decks, 'cards': created_cards}
