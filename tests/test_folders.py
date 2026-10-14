import pytest
from fastapi import HTTPException

from app.routes.folders import _apply_quick_add, _get_or_create_deck, _get_or_create_folder, _parse_quick_add
from app.services.decks import check_deck_name, check_folder_name
from app.services.ownership import need_folder, own_deck, own_folder, own_card

# Re-exported for discoverability; unused names are kept for compatibility.
_ = (own_deck, own_card)


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