import pytest
from fastapi import HTTPException

from app.routes.folders import _apply_quick_add, _get_or_create_deck, _get_or_create_folder, _parse_quick_add
from app.services.decks import check_deck_name, check_folder_name
from app.services.ownership import need_folder, own_folder


def test_parse_quick_add_formats():
    assert _parse_quick_add("Folder") == ["Folder"]
    assert _parse_quick_add("Folder/Deck") == ["Folder", "Deck"]
    assert _parse_quick_add("Folder/Deck/Front/Back") == [
        "Folder", "Deck", "Front", "Back",
    ]
    assert _parse_quick_add("Folder,Deck,Front,Back,Note") == [
        "Folder", "Deck", "Front", "Back", "Note",
    ]


def test_parse_quick_add_rejects_mixed_separators():
    with pytest.raises(HTTPException) as exc:
        _parse_quick_add("Folder/Deck,Card")
    assert "only / or ," in str(exc.value.detail).lower()


def test_parse_quick_add_rejects_empty_part():
    with pytest.raises(HTTPException) as exc:
        _parse_quick_add("Folder/")
    assert "empty part" in str(exc.value.detail).lower()


def test_parse_quick_add_rejects_three_parts():
    with pytest.raises(HTTPException) as exc:
        _parse_quick_add("Folder/Deck/Front")
    assert "need front and back" in str(exc.value.detail).lower()


def test_parse_quick_add_rejects_too_many_parts():
    with pytest.raises(HTTPException) as exc:
        _parse_quick_add("a,b,c,d,e,f")
    assert "too many parts" in str(exc.value.detail).lower()


def test_get_or_create_folder_creates_and_reuses():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from app.db import TABLES, INDEXES, ORDER
    for name in ORDER:
        conn.execute(TABLES[name])
    for sql in INDEXES:
        conn.execute(sql)
    conn.execute("INSERT INTO users(email,password_hash,name,tz) VALUES(?,?,?,?)", ("u@e.com", "h", "u", "UTC"))
    conn.commit()
    uid = conn.execute("SELECT id FROM users").fetchone()[0]

    first = _get_or_create_folder(conn, uid, "Folder")
    second = _get_or_create_folder(conn, uid, "folder")
    assert first["status"] == "created"
    assert second["status"] == "existing"
    assert first["id"] == second["id"]


def test_get_or_create_deck_creates_and_reuses():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from app.db import TABLES, INDEXES, ORDER
    for name in ORDER:
        conn.execute(TABLES[name])
    for sql in INDEXES:
        conn.execute(sql)
    conn.execute("INSERT INTO users(email,password_hash,name,tz) VALUES(?,?,?,?)", ("u@e.com", "h", "u", "UTC"))
    conn.commit()
    uid = conn.execute("SELECT id FROM users").fetchone()[0]
    folder_id = conn.execute(
        "INSERT INTO folders(user_id,name,pos) VALUES(?,?,?)", (uid, "Folder", 1)
    ).lastrowid
    conn.commit()

    first = _get_or_create_deck(conn, uid, folder_id, "Deck")
    second = _get_or_create_deck(conn, uid, folder_id, "deck")
    assert first["status"] == "created"
    assert second["status"] == "existing"
    assert first["id"] == second["id"]


def test_check_folder_name_rejects_duplicate(conn, user_id):
    conn.execute("INSERT INTO folders(user_id,name,pos) VALUES(?,?,?)", (user_id, "Folder", 1))
    conn.commit()
    with pytest.raises(Exception):
        check_folder_name(conn, user_id, "folder")


def test_check_deck_name_rejects_duplicate(conn, user_id):
    folder_id = conn.execute(
        "INSERT INTO folders(user_id,name,pos) VALUES(?,?,?)", (user_id, "Folder", 1)
    ).lastrowid
    conn.execute(
        "INSERT INTO decks(user_id,folder_id,name,pos) VALUES(?,?,?,?)",
        (user_id, folder_id, "Deck", 1),
    )
    conn.commit()
    with pytest.raises(Exception):
        check_deck_name(conn, folder_id, "deck")


def test_apply_quick_add_creates_card(conn, user_id):
    result = _apply_quick_add(conn, user_id, "Folder/Deck/Front/Back")
    assert result["kind"] == "card"
    assert result["card"]["status"] == "created"


def test_apply_quick_add_existing_card(conn, user_id):
    _apply_quick_add(conn, user_id, "Folder/Deck/Front/Back")
    result = _apply_quick_add(conn, user_id, "Folder/Deck/Front/Back")
    assert result["card"]["status"] == "existing"


def test_need_folder_and_own_folder(conn, user_id):
    with pytest.raises(Exception):
        need_folder(conn, user_id, 0)
    folder_id = conn.execute(
        "INSERT INTO folders(user_id,name,pos) VALUES(?,?,?)", (user_id, "Folder", 1)
    ).lastrowid
    conn.commit()
    assert own_folder(conn, user_id, folder_id) == folder_id
    with pytest.raises(Exception):
        own_folder(conn, 9999, folder_id)


def _signup(client, email="folders@example.com"):
    response = client.post(
        "/api/signup",
        data={"email": email, "password": "GoodPass123", "password2": "GoodPass123", "tz": "UTC"},
    )
    assert response.status_code == 200, response.text


def _make_folder(client, name):
    response = client.post("/api/quick-add", data={"text": name})
    assert response.status_code == 200, response.text
    return response.json()["folder"]["id"]


def test_folder_order_rejects_non_integer_ids(client):
    _signup(client)
    assert client.post("/api/folders/order", data={"ids": "abc"}).status_code == 400


def test_folder_order_rejects_duplicates(client):
    _signup(client)
    folder_id = _make_folder(client, "Folder")
    assert client.post("/api/folders/order", data={"ids": [folder_id, folder_id]}).status_code == 400


def test_folder_order_rejects_unknown_folder(client):
    _signup(client)
    assert client.post("/api/folders/order", data={"ids": 9999}).status_code == 400


def test_folder_order_applies(client):
    _signup(client)
    first = _make_folder(client, "First")
    second = _make_folder(client, "Second")

    assert client.post("/api/folders/order", data={"ids": [second, first]}).status_code == 200

    html = client.get("/").text
    assert html.index(f'data-folder="{second}"') < html.index(f'data-folder="{first}"')


def test_folder_order_accepts_a_subset(client):
    # A partial list used to collide with the other folders' positions (400).
    _signup(client)
    first = _make_folder(client, "First")
    second = _make_folder(client, "Second")
    third = _make_folder(client, "Third")

    assert client.post("/api/folders/order", data={"ids": [third, first]}).status_code == 200

    # Submitted folders fill their own slots; "Second" keeps slot 2 in between.
    html = client.get("/").text
    assert html.index(f'data-folder="{third}"') < html.index(f'data-folder="{second}"')
    assert html.index(f'data-folder="{second}"') < html.index(f'data-folder="{first}"')