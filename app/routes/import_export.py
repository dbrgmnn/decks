import csv
import io

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from .. import auth, db
from ..i18n import error
from ..services.cards import card_key
from ..services.decks import check_deck_name, next_deck_pos
from ..services.ownership import own_deck
from ..services.tags import join_tags, parse_tags
from ..services.validators import clean, clean_deck_name, normalize_name_key

router = APIRouter()

CSV_FIELDS = ['deck', 'front', 'back', 'note', 'tags']

# A reasonable upper bound for a text CSV of flashcards.
MAX_CSV_BYTES = 5 * 1024 * 1024

# Spreadsheet apps in many locales save CSV with semicolons. Import accepts
# both, detected from the header; export always writes commas.
CSV_DELIMITERS = (',', ';')


def read_csv_rows(text):
    """Parse CSV rows, trying each supported delimiter.

    The delimiter is picked by matching the header against CSV_FIELDS, so a
    quoted value containing the other delimiter is not mistaken for a column
    separator. Raises ``error.csv_columns`` when no delimiter matches and
    ``error.csv_unparseable`` for a malformed file (e.g. an oversized field).
    """
    parse_error = False
    for delimiter in CSV_DELIMITERS:
        try:
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            if reader.fieldnames == CSV_FIELDS:
                return list(reader)
        except csv.Error:
            parse_error = True
    if parse_error:
        raise error(400, 'error.csv_unparseable')
    raise error(400, 'error.csv_columns')


@router.post('/api/export/cards.csv')
def export_cards_csv(
    scope: str = Form('all'),
    deck_id: int = Form(0),
    user=Depends(auth.current_user),
):
    uid = user['id']
    sql = '''SELECT d.name AS deck, c.front, c.back, c.note, c.tags
             FROM cards c
             JOIN decks d ON d.id = c.deck_id
             WHERE d.user_id = ?'''
    params = [uid]
    with db.conn() as c:
        if scope == 'deck':
            if not deck_id:
                raise error(400, 'error.export_deck_required')
            deck = own_deck(c, uid, deck_id)
            sql += ' AND d.id = ?'
            params.append(deck['id'])
        elif scope != 'all':
            raise error(400, 'error.export_scope_invalid')
        sql += ' ORDER BY d.pos, d.id, c.id DESC'
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
        rows = read_csv_rows(text)
    except csv.Error:
        # A malformed file or a single field past csv's size limit.
        raise error(400, 'error.csv_unparseable')

    if not rows:
        return {'ok': True, 'decks': 0, 'cards': 0}

    uid = user['id']
    created_decks = 0
    created_cards = 0

    with db.conn() as c:
        deck_cache = {
            normalize_name_key(r['name']): r['id']
            for r in c.execute('SELECT id, name FROM decks WHERE user_id=?', (uid,))
        }
        card_cache = {}

        for i, row in enumerate(rows, 2):
            deck = clean_deck_name(row.get('deck', ''), 'field.deck', 60, line=i)
            front = clean(row.get('front', ''), 'field.front', 200, line=i)
            back = clean(row.get('back', ''), 'field.back', 200, line=i)
            note = clean(row.get('note', ''), 'field.note', 300, required=False, line=i)
            tags = parse_tags(row.get('tags', ''), line=i)

            deck_key = normalize_name_key(deck)
            deck_id = deck_cache.get(deck_key)
            if not deck_id:
                check_deck_name(c, uid, deck)
                deck_id = c.execute(
                    'INSERT INTO decks(user_id, name, pos) VALUES(?,?,?)',
                    (uid, deck, next_deck_pos(c, uid)),
                ).lastrowid
                deck_cache[deck_key] = deck_id
                created_decks += 1

            keys = card_cache.get(deck_id)
            if keys is None:
                keys = {
                    card_key(r['front'], r['back'])
                    for r in c.execute(
                        'SELECT front, back FROM cards WHERE deck_id=?', (deck_id,)
                    )
                }
                card_cache[deck_id] = keys

            key = card_key(front, back)
            if key in keys:
                continue
            c.execute(
                'INSERT INTO cards(deck_id, front, back, note, tags) VALUES(?,?,?,?,?)',
                (deck_id, front, back, note, join_tags(tags)),
            )
            keys.add(key)
            created_cards += 1

    return {'ok': True, 'decks': created_decks, 'cards': created_cards}
