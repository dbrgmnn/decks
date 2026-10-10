from fastapi import APIRouter, Depends, Form, HTTPException, Request

from .. import auth, db

router = APIRouter()

@router.post('/api/signup')
def signup(request: Request, email: str = Form(...), password: str = Form(...), password2: str = Form(''), tz: str = Form('')):
    key = f"signup:{auth.ip(request)}"
    if auth.blocked(key, 10, 3600):
        raise HTTPException(429, 'Too many attempts. Try again later.')
    auth.fail(key)
    email = auth.clean_email(email)
    auth.check_password(password)
    if password != password2:
        raise HTTPException(400, 'Passwords do not match')
    with db.conn() as c:
        if c.execute('SELECT 1 FROM users WHERE lower(email)=?', (email,)).fetchone():
            raise HTTPException(400, 'This email is already registered')
        uid = c.execute(
            'INSERT INTO users(email,password_hash,name,tz) VALUES(?,?,?,?)',
            (email, auth.hash_pw(password), email.split('@')[0][:40], tz if tz in auth.TZ_SET else 'UTC'),
        ).lastrowid
    auth.clear(key)
    request.session.clear()
    request.session['uid'] = uid
    return {'ok': True}

@router.post('/api/login')
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    email = auth.clean_email(email)
    key = f"login:{auth.ip(request)}:{email}"
    if auth.blocked(key):
        raise HTTPException(429, 'Too many attempts. Try again in a few minutes.')
    with db.conn() as c:
        row = c.execute('SELECT id, password_hash FROM users WHERE lower(email)=?', (email,)).fetchone()
    if not auth.verify(row['password_hash'] if row else auth.DUMMY, password) or not row:
        auth.fail(key)
        raise HTTPException(400, 'Invalid email or password')
    auth.clear(key)
    request.session.clear()
    request.session['uid'] = row['id']
    return {'ok': True}

@router.post('/api/logout')
def logout(request: Request):
    request.session.clear()
    return {'ok': True}

@router.post('/api/password')
def change_password(request: Request, current: str = Form(...), password: str = Form(...), password2: str = Form(...), user=Depends(auth.current_user)):
    key = f"pw:{user['id']}"
    if auth.blocked(key):
        raise HTTPException(429, 'Too many attempts. Try again in a few minutes.')
    with db.conn() as c:
        row = c.execute('SELECT password_hash FROM users WHERE id=?', (user['id'],)).fetchone()
        if not auth.verify(row['password_hash'], current):
            auth.fail(key)
            raise HTTPException(400, 'Current password is incorrect')
        auth.check_password(password)
        if password != password2:
            raise HTTPException(400, 'Passwords do not match')
        if password == current:
            raise HTTPException(400, 'New password must be different')
        c.execute('UPDATE users SET password_hash=? WHERE id=?', (auth.hash_pw(password), user['id']))
    auth.clear(key)
    return {'ok': True}

@router.post('/api/settings')
def save_settings(tz: str = Form(...), user=Depends(auth.current_user)):
    if tz not in auth.TZ_SET:
        raise HTTPException(400, 'Unknown time zone')
    with db.conn() as c:
        c.execute('UPDATE users SET tz=? WHERE id=?', (tz, user['id']))
    return {'ok': True}

@router.post('/api/account/delete')
def delete_account(request: Request, password: str = Form(...), user=Depends(auth.current_user)):
    key = f"pw:{user['id']}"
    if auth.blocked(key):
        raise HTTPException(429, 'Too many attempts. Try again in a few minutes.')
    uid = user['id']
    with db.conn() as c:
        row = c.execute('SELECT password_hash FROM users WHERE id=?', (uid,)).fetchone()
        if not auth.verify(row['password_hash'], password):
            auth.fail(key)
            raise HTTPException(400, 'Password is incorrect')
        c.execute('DELETE FROM users WHERE id=?', (uid,))
    auth.clear(key)
    request.session.clear()
    return {'ok': True}
