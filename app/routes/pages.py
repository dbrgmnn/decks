from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse
from .. import auth, db, i18n, srs
from ..services.decks import introduced_counts
from ..web import BASE, page

router = APIRouter()

@router.get('/login')
def login_page(request: Request):
    if request.session.get('uid'):
        return RedirectResponse('/', 303)
    return page(request, 'login.html')

@router.get('/sw.js', include_in_schema=False)
def service_worker():
    # Served from the site root so the worker scope covers the whole app.
    return FileResponse(BASE / 'static' / 'sw.js', media_type='application/javascript')

@router.get('/')
def home(request: Request, folder: int = 0, user=Depends(auth.current_user)):
    now, today, uid = srs.now(), srs.day_start(user['tz']), user['id']
    with db.conn() as c:
        rows = c.execute("""SELECT d.id, d.name, d.new_per_day, d.paused, d.folder_id, d.pinned,
            SUM(c.id IS NOT NULL AND c.state IS NULL) AS new,
            SUM(c.id IS NOT NULL AND c.due<=?) AS due,
            COUNT(c.id) AS total
            FROM decks d
            LEFT JOIN cards c ON c.deck_id=d.id
            WHERE d.user_id=?
            GROUP BY d.id
            ORDER BY d.pos, d.id""", (now, uid)).fetchall()
        intro = introduced_counts(c, uid, today)
        folder_rows = c.execute('SELECT id, name FROM folders WHERE user_id=? ORDER BY pos, id', (uid,)).fetchall()

    folder_names = {f['id']: f['name'] for f in folder_rows}

    items = [{
        'id': r['id'],
        'name': r['name'],
        'folder_id': r['folder_id'],
        'folder_name': folder_names.get(r['folder_id']),
        'path': f"{folder_names[r['folder_id']]}/{r['name']}" if r['folder_id'] in folder_names else r['name'],
        'new_per_day': r['new_per_day'],
        'paused': bool(r['paused']),
        'pinned': bool(r['pinned']),
        'new_total': int(r['new'] or 0),
        'new': max(0, min(int(r['new'] or 0), int(r['new_per_day']) - int(intro.get(r['id'], 0)))),
        'due': int(r['due'] or 0),
        'total': int(r['total'] or 0),
    } for r in rows]

    folder_map = {
        f['id']: {
            'id': f['id'],
            'name': f['name'],
            'count': 0,
            'cards': 0,
            'new': 0,
            'due': 0,
            'paused': True,
        }
        for f in folder_rows
    }
    for deck in items:
        folder_info = folder_map.get(deck['folder_id'])
        if not folder_info:
            continue
        folder_info['count'] += 1
        folder_info['cards'] += deck['total']
        if not deck['paused']:
            folder_info['new'] += deck['new']
            folder_info['due'] += deck['due']
            folder_info['paused'] = False

    folders = list(folder_map.values())
    selected_folder = folder_map.get(folder) if folder else None
    decks = [d for d in items if d['folder_id'] == folder] if selected_folder else [d for d in items if d['pinned']]
    stats = {
        'due': sum(x['due'] for x in items if not x['paused']),
        'new': sum(x['new'] for x in items if not x['paused']),
    }
    return page(request, 'home.html', {
        'folders': folders,
        'folder': selected_folder,
        'user': user,
        'decks': decks,
        'stats': stats,
        'now': now,
        'today': today,
        'timezones': auth.tz_options(user['tz']),
        'all_decks': items,
    }, lang=i18n.resolve(request, user))
