import csv
import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from .. import auth, db
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
            folder_id = own_folder(c, uid, folder_id)
            sql += ' AND d.folder_id = ?'
            params.append(folder_id)
        elif scope == 'deck':
            deck = own_deck(c, uid, deck_id)
            sql += ' AND d.id = ?'
            params.append(deck['id'])
        elif scope != 'all':
            raise HTTPException(400, 'Choose all cards, one folder, or one deck')
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
        raise HTTPException(400, 'Upload a CSV file')
    raw = file.file.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(413, 'CSV file is too large (max 5 MB)')
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise HTTPException(400, 'CSV must be UTF-8 encoded')
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != CSV_FIELDS:
        raise HTTPException(400, 'CSV columns must be exactly: folder, deck, front, back, note')

    rows = list(reader)
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
            folder = clean(row.get('folder', ''), f'Folder on line {i}', 60)
            deck = clean(row.get('deck', ''), f'Deck on line {i}', 60)
            front = clean(row.get('front', ''), f'Front on line {i}', 200)
            back = clean(row.get('back', ''), f'Back on line {i}', 200)
            note = clean(row.get('note', ''), f'Note on line {i}', 300, required=False)

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
