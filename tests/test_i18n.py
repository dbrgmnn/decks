import json
import pathlib
import re

from app import db, i18n


CATALOG_DIR = pathlib.Path(__file__).resolve().parent.parent / "app" / "i18n"
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _catalog(lang):
    return json.loads((CATALOG_DIR / f"{lang}.json").read_text("utf-8"))


def _signup(client, email="i18n@example.com"):
    response = client.post(
        "/api/signup",
        data={"email": email, "password": "GoodPass123", "password2": "GoodPass123", "tz": "UTC"},
    )
    assert response.status_code == 200, response.text


def test_catalogs_have_the_same_keys_and_placeholders():
    en, de = _catalog("en"), _catalog("de")
    assert set(en) == set(de)
    for key in en:
        assert isinstance(en[key], type(de[key])), key
        if isinstance(en[key], str):
            assert en[key].strip() and de[key].strip(), key
            assert set(PLACEHOLDER.findall(en[key])) == set(PLACEHOLDER.findall(de[key])), key
        else:
            assert set(en[key]) == set(de[key]), key


def test_translation_falls_back_to_english_and_then_to_the_key():
    assert i18n.t("home.study", "de") == "Lernen"
    assert i18n.t("home.study", "fr") == "Study"
    assert i18n.t("missing.key", "de") == "missing.key"


def test_german_plural_forms():
    assert i18n.plural("home.cards", 1, "de") == "1 Karte"
    assert i18n.plural("home.cards", 5, "de") == "5 Karten"
    assert i18n.plural("home.cards", 1, "en") == "1 card"


def test_login_page_follows_accept_language(client):
    response = client.get("/login", headers={"accept-language": "de-DE,de;q=0.9,en;q=0.5"})

    assert response.status_code == 200
    assert response.headers["content-language"] == "de"
    assert '<html lang="de">' in response.text
    assert 'placeholder="E-Mail"' in response.text
    assert "Anmelden" in response.text


def test_signup_stores_the_language_cookie(client):
    client.cookies.set("decks_lang", "de")
    _signup(client)

    with db.conn() as c:
        assert c.execute("SELECT lang FROM users").fetchone()["lang"] == "de"

    home = client.get("/")
    assert home.headers["content-language"] == "de"
    assert "Neue Karten pro Tag" in home.text
    assert "Abmelden" in home.text


def test_account_language_setting_persists_and_changes_the_ui(client):
    _signup(client)
    assert "New cards per day" in client.get("/").text

    response = client.post("/api/settings/language", data={"lang": "de"})
    assert response.status_code == 200
    assert response.cookies["decks_lang"] == "de"

    with db.conn() as c:
        assert c.execute("SELECT lang FROM users").fetchone()["lang"] == "de"

    home = client.get("/")
    assert "Neue Karten pro Tag" in home.text
    assert 'id="lang"' in home.text

    # An empty value means "automatic": clear both the column and the cookie.
    response = client.post("/api/settings/language", data={"lang": ""})
    assert response.status_code == 200
    assert "decks_lang" not in response.cookies
    with db.conn() as c:
        assert c.execute("SELECT lang FROM users").fetchone()["lang"] == ""


def test_login_restores_the_users_saved_language(client):
    client.cookies.set("decks_lang", "de")
    _signup(client)
    client.post("/api/logout")
    client.cookies.delete("decks_lang")

    response = client.post(
        "/api/login",
        data={"email": "i18n@example.com", "password": "GoodPass123"},
    )

    assert response.status_code == 200
    assert response.cookies["decks_lang"] == "de"


def test_login_saves_the_language_cookie_when_the_account_has_none(client):
    _signup(client)
    client.post("/api/logout")
    client.cookies.set("decks_lang", "de")

    response = client.post(
        "/api/login",
        data={"email": "i18n@example.com", "password": "GoodPass123"},
    )

    assert response.status_code == 200
    with db.conn() as c:
        assert c.execute("SELECT lang FROM users").fetchone()["lang"] == "de"


def test_api_errors_are_translated(client):
    client.cookies.set("decks_lang", "de")
    _signup(client)

    response = client.delete("/api/cards/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Karte nicht gefunden"
    assert response.headers["content-language"] == "de"


def test_api_token_errors_use_the_account_language(client):
    client.cookies.set("decks_lang", "de")
    _signup(client)
    token = client.post("/api/account/token").json()["token"]
    client.post("/api/logout")
    client.cookies.delete("decks_lang")

    response = client.post(
        "/api/quick-add",
        data={"text": "a/b,c"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Verwende entweder / oder , – nicht beides"


def test_user_setting_wins_over_the_cookie(client):
    client.cookies.set("decks_lang", "de")
    _signup(client)
    client.post("/api/settings/language", data={"lang": "en"})

    # A stale cookie must not override the account preference.
    client.cookies.set("decks_lang", "de")
    assert "New cards per day" in client.get("/").text
