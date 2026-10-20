import pytest
from fastapi import HTTPException

from app import db
from app.routes.folders import _apply_quick_add, _get_or_create_deck, _get_or_create_folder, _parse_quick_add
from app.services.decks import check_deck_name, check_folder_name
from app.services.ownership import need_folder, own_folder
from tests.conftest import signup_user


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
    assert exc.value.status_code == 400


def test_parse_quick_add_rejects_empty_part():
    with pytest.raises(HTTPException) as exc:
        _parse_quick_add("Folder/")
    assert exc.value.status_code == 400


def test_parse_quick_add_rejects_three_parts():
    with pytest.raises(HTTPException) as exc:
        _parse_quick_add("Folder/Deck/Front")
    assert exc.value.status_code == 400


def test_parse_quick_add_rejects_too_many_parts():
    with pytest.raises(HTTPException) as exc:
        _parse_quick_add("a,b,c,d,e,f")
    assert exc.value.status_code == 400


def test_get_or_create_folder_creates_and_reuses(conn, user_id):
    first = _get_or_create_folder(conn, user_id, "Folder")
    second = _get_or_create_folder(conn, user_id, "folder")
    assert first["status"] == "created"
    assert second["status"] == "existing"
    assert first["id"] == second["id"]


def test_get_or_create_deck_creates_and_reuses(conn, user_id):
    folder_id = conn.execute(
        "INSERT INTO folders(user_id, name, pos) VALUES(?,?,?)", (user_id, "Folder", 1)
    ).lastrowid
    conn.commit()

    first = _get_or_create_deck(conn, user_id, folder_id, "Deck")
    second = _get_or_create_deck(conn, user_id, folder_id, "deck")
    assert first["status"] == "created"
    assert second["status"] == "existing"
    assert first["id"] == second["id"]


def test_check_folder_name_rejects_duplicate(conn, user_id):
    conn.execute("INSERT INTO folders(user_id, name, pos) VALUES(?,?,?)", (user_id, "Folder", 1))
    conn.commit()
    with pytest.raises(HTTPException):
        check_folder_name(conn, user_id, "folder")


def test_check_deck_name_rejects_duplicate(conn, user_id):
    folder_id = conn.execute(
        "INSERT INTO folders(user_id, name, pos) VALUES(?,?,?)", (user_id, "Folder", 1)
    ).lastrowid
    conn.execute(
        "INSERT INTO decks(user_id, folder_id, name, pos) VALUES(?,?,?,?)",
        (user_id, folder_id, "Deck", 1),
    )
    conn.commit()
    with pytest.raises(HTTPException):
        check_deck_name(conn, folder_id, "deck")


def test_apply_quick_add_creates_and_reuses_card(conn, user_id):
    first = _apply_quick_add(conn, user_id, "Folder/Deck/Front/Back")
    assert first["kind"] == "card"
    assert first["card"]["status"] == "created"

    second = _apply_quick_add(conn, user_id, "Folder/Deck/Front/Back")
    assert second["card"]["status"] == "existing"
    assert first["card"]["id"] == second["card"]["id"]


def test_need_folder_and_own_folder(conn, user_id):
    with pytest.raises(HTTPException):
        need_folder(conn, user_id, 0)

    folder_id = conn.execute(
        "INSERT INTO folders(user_id, name, pos) VALUES(?,?,?)", (user_id, "Folder", 1)
    ).lastrowid
    conn.commit()
    assert own_folder(conn, user_id, folder_id) == folder_id

    with pytest.raises(HTTPException):
        own_folder(conn, 9999, folder_id)


def test_update_folder_renames_successfully(auth_client, make_folder):
    folder_id = make_folder("OldName")

    response = auth_client.put(f"/api/folders/{folder_id}", data={"name": "NewName"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    with db.conn() as c:
        row = c.execute("SELECT name FROM folders WHERE id=?", (folder_id,)).fetchone()
        assert row["name"] == "NewName"


def test_update_folder_rejects_duplicate_name(auth_client, make_folder):
    make_folder("First")
    second = make_folder("Second")

    response = auth_client.put(f"/api/folders/{second}", data={"name": "first"})
    assert response.status_code == 400


def test_update_folder_requires_owned_folder(client, auth_client, make_folder):
    folder_id = make_folder()

    signup_user(client, email="other@example.com")
    assert client.put(f"/api/folders/{folder_id}", data={"name": "Hacked"}).status_code == 404


def test_delete_folder_cascades_decks_and_cards(auth_client, make_folder, make_deck, make_card):
    folder_id = make_folder()
    deck_id = make_deck(folder_id=folder_id)
    card_id = make_card(deck_id=deck_id)

    response = auth_client.delete(f"/api/folders/{folder_id}")
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    with db.conn() as c:
        assert c.execute("SELECT COUNT(*) FROM folders WHERE id=?", (folder_id,)).fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM decks WHERE id=?", (deck_id,)).fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM cards WHERE id=?", (card_id,)).fetchone()[0] == 0


def test_delete_folder_requires_owned_folder(client, auth_client, make_folder):
    folder_id = make_folder()

    signup_user(client, email="other@example.com")
    assert client.delete(f"/api/folders/{folder_id}").status_code == 404


def test_folder_order_validation(auth_client, make_folder):
    folder_id = make_folder("Folder")
    assert auth_client.post("/api/folders/order", data={"ids": "abc"}).status_code == 400
    assert auth_client.post("/api/folders/order", data={"ids": [folder_id, folder_id]}).status_code == 400
    assert auth_client.post("/api/folders/order", data={"ids": [9999]}).status_code == 400


def test_folder_order_applies_and_preserves_unsubmitted_subset(auth_client, make_folder):
    first = make_folder("First")
    second = make_folder("Second")
    third = make_folder("Third")

    # Reshuffle third and first, second remains in slot 2
    assert auth_client.post("/api/folders/order", data={"ids": [third, first]}).status_code == 200

    with db.conn() as c:
        positions = dict(c.execute("SELECT id, pos FROM folders WHERE id IN (?,?,?)", (first, second, third)).fetchall())
        assert positions[third] < positions[second] < positions[first]