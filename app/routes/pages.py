from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse
from .. import auth, db, i18n, srs
from ..services.decks import NEW_PER_DAY_VALUES, introduced_counts
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
def home(request: Request, user=Depends(auth.current_user)):
    now, today, uid = srs.now(), srs.day_start(user['tz']), user['id']
    with db.conn() as c:
        rows = c.execute("""SELECT d.id, d.name, d.new_per_day, d.paused,
            SUM(c.id IS NOT NULL AND c.state IS NULL) AS new,
            SUM(c.id IS NOT NULL AND c.due<=?) AS due,
            COUNT(c.id) AS total
            FROM decks d
            LEFT JOIN cards c ON c.deck_id=d.id
            WHERE d.user_id=?
            GROUP BY d.id
            ORDER BY d.pos, d.id""", (now, uid)).fetchall()
        intro = introduced_counts(c, uid, today)

    items = [{
        'id': r['id'],
        'name': r['name'],
        'new_per_day': r['new_per_day'],
        'paused': bool(r['paused']),
        'new_total': int(r['new'] or 0),
        'new': max(0, min(int(r['new'] or 0), int(r['new_per_day']) - int(intro.get(r['id'], 0)))),
        'due': int(r['due'] or 0),
        'total': int(r['total'] or 0),
    } for r in rows]

    stats = {
        'due': sum(x['due'] for x in items if not x['paused']),
        'new': sum(x['new'] for x in items if not x['paused']),
    }
    return page(request, 'home.html', {
        'user': user,
        'decks': items,
        'stats': stats,
        'now': now,
        'today': today,
        'timezones': auth.tz_options(user['tz']),
        'all_decks': items,
        'new_per_day_values': NEW_PER_DAY_VALUES,
    }, lang=i18n.resolve(request, user))
