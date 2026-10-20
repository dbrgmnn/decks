import sqlite3

from fastapi import APIRouter, Depends, Form, Request, Response

from .. import auth, db, i18n
from ..i18n import error

router = APIRouter()

@router.post('/api/signup')
def signup(request: Request, email: str = Form(...), password: str = Form(...), password2: str = Form(''), tz: str = Form('')):
    key = f"signup:{auth.ip(request)}"
    if auth.blocked(key, 10, 3600):
        raise error(429, 'error.too_many_signups')
    auth.fail(key)
    email = auth.clean_email(email)
    auth.check_password(password)
    if password != password2:
        raise error(400, 'error.passwords_mismatch')
    lang = i18n.lang_from_cookie(request) or ''
    with db.conn() as c:
        if c.execute('SELECT 1 FROM users WHERE lower(email)=?', (email,)).fetchone():
            raise error(400, 'error.email_registered')
        try:
            uid = c.execute(
                'INSERT INTO users(email,password_hash,name,tz,lang) VALUES(?,?,?,?,?)',
                (email, auth.hash_pw(password), email.split('@')[0][:40], tz if tz in auth.TZ_SET else 'UTC', lang),
            ).lastrowid
        except sqlite3.IntegrityError:
            # Lost a race against a concurrent signup for the same address.
            raise error(400, 'error.email_registered')
    auth.clear(key)
    request.session.clear()
    request.session['uid'] = uid
    request.session['tv'] = 0
    return {'ok': True}

@router.post('/api/login')
def login(request: Request, response: Response, email: str = Form(...), password: str = Form(...)):
    email = auth.clean_email(email)
    key = f"login:{auth.ip(request)}:{email}"
    if auth.blocked(key):
        raise error(429, 'error.too_many_attempts')
    with db.conn() as c:
        row = c.execute('SELECT id, password_hash, token_version, lang FROM users WHERE lower(email)=?', (email,)).fetchone()
    if not auth.verify(row['password_hash'] if row else auth.DUMMY, password) or not row:
        auth.fail(key)
        raise error(400, 'error.invalid_credentials')
    auth.clear(key)
    request.session.clear()
    request.session['uid'] = row['id']
    request.session['tv'] = row['token_version']
    if row['lang'] in i18n.SUPPORTED:
        i18n.set_language_cookie(response, row['lang'])
    else:
        # The user picked a language on the login page before signing in.
        cookie_lang = i18n.lang_from_cookie(request)
        if cookie_lang:
            with db.conn() as c:
                c.execute('UPDATE users SET lang=? WHERE id=?', (cookie_lang, row['id']))
    return {'ok': True}

@router.post('/api/logout')
def logout(request: Request):
    uid = request.session.get('uid')
    if uid:
        # Bumping the version revokes every cookie issued for this account.
        with db.conn() as c:
            c.execute('UPDATE users SET token_version=token_version+1 WHERE id=?', (uid,))
    request.session.clear()
    return {'ok': True}

@router.post('/api/password')
def change_password(request: Request, current: str = Form(...), password: str = Form(...), password2: str = Form(...), user=Depends(auth.current_user)):
    key = f"pw:{user['id']}"
    if auth.blocked(key):
        raise error(429, 'error.too_many_attempts')
    with db.conn() as c:
        row = c.execute('SELECT password_hash FROM users WHERE id=?', (user['id'],)).fetchone()
        if not auth.verify(row['password_hash'], current):
            auth.fail(key)
            raise error(400, 'error.current_password_incorrect')
        auth.check_password(password)
        if password != password2:
            raise error(400, 'error.passwords_mismatch')
        if password == current:
            raise error(400, 'error.new_password_same')
        c.execute(
            'UPDATE users SET password_hash=?, token_version=token_version+1 WHERE id=?',
            (auth.hash_pw(password), user['id']),
        )
        token_version = c.execute('SELECT token_version FROM users WHERE id=?', (user['id'],)).fetchone()[0]
    auth.clear(key)
    # Keep this device signed in, but every other session is now invalid.
    request.session['tv'] = token_version
    return {'ok': True}

@router.post('/api/settings')
def save_settings(tz: str = Form(...), user=Depends(auth.current_user)):
    if tz not in auth.TZ_SET:
        raise error(400, 'error.unknown_tz')
    with db.conn() as c:
        c.execute('UPDATE users SET tz=? WHERE id=?', (tz, user['id']))
    return {'ok': True}


@router.post('/api/settings/language')
def save_language(response: Response, lang: str = Form(''), user=Depends(auth.current_user)):
    if lang and lang not in i18n.SUPPORTED:
        raise error(400, 'error.unknown_language')
    with db.conn() as c:
        c.execute('UPDATE users SET lang=? WHERE id=?', (lang, user['id']))
    if lang:
        i18n.set_language_cookie(response, lang)
    else:
        i18n.clear_language_cookie(response)
    return {'ok': True}

@router.post('/api/account/token')
def regenerate_api_token(user=Depends(auth.current_user)):
    token = auth.generate_api_token()
    token_hash = auth.hash_api_token(token)
    with db.conn() as c:
        c.execute('UPDATE users SET api_token_hash=? WHERE id=?', (token_hash, user['id']))
    return {'ok': True, 'token': token}

@router.post('/api/account/delete')
def delete_account(request: Request, password: str = Form(...), user=Depends(auth.current_user)):
    key = f"pw:{user['id']}"
    if auth.blocked(key):
        raise error(429, 'error.too_many_attempts')
    uid = user['id']
    with db.conn() as c:
        row = c.execute('SELECT password_hash FROM users WHERE id=?', (uid,)).fetchone()
        if not auth.verify(row['password_hash'], password):
            auth.fail(key)
            raise error(400, 'error.password_incorrect')
        c.execute('DELETE FROM users WHERE id=?', (uid,))
    auth.clear(key)
    request.session.clear()
    return {'ok': True}
