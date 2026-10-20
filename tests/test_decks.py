import re

from app import db
from tests.conftest import signup_user


def test_create_deck_success(auth_client, make_folder):
    folder_id = make_folder("Language")
    response = auth_client.post("/api/decks", data={"name": "Spanish", "folder_id": folder_id})
    assert response.status_code == 200
    deck_id = response.json()["id"]

    with db.conn() as c:
        row = c.execute("SELECT name, folder_id, pos, new_per_day, paused, pinned FROM decks WHERE id=?", (deck_id,)).fetchone()
        assert row["name"] == "Spanish"
        assert row["folder_id"] == folder_id
        assert row["pos"] == 1
        assert row["new_per_day"] == 10
        assert row["paused"] == 0
        assert row["pinned"] == 0


def test_create_deck_rejects_duplicate_name_in_folder(auth_client, make_folder, make_deck):
    folder_id = make_folder()
    make_deck(folder_id=folder_id, name="Deck")

    duplicate = auth_client.post("/api/decks", data={"name": "deck", "folder_id": folder_id})
    assert duplicate.status_code == 400


def test_create_deck_requires_an_owned_folder(client, auth_client, make_folder):
    folder_id = make_folder()

    signup_user(client, email="other@example.com")
    response = client.post("/api/decks", data={"name": "Deck", "folder_id": folder_id})
    assert response.status_code == 404

    # Non-existent folder
    missing = auth_client.post("/api/decks", data={"name": "Deck", "folder_id": 9999})
    assert missing.status_code == 404


def test_update_deck_and_move_to_another_folder(auth_client, make_folder, make_deck):
    folder1 = make_folder("Folder 1")
    folder2 = make_folder("Folder 2")
    deck_id = make_deck(folder_id=folder1, name="Original")

    response = auth_client.put(
        f"/api/decks/{deck_id}",
        data={"name": "Renamed", "folder_id": folder2, "new_per_day": "20", "paused": 1},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    with db.conn() as c:
        row = c.execute("SELECT name, folder_id, new_per_day, paused FROM decks WHERE id=?", (deck_id,)).fetchone()
        assert row["name"] == "Renamed"
        assert row["folder_id"] == folder2
        assert row["new_per_day"] == 20
        assert row["paused"] == 1


def test_update_deck_rejects_duplicate_name_in_target_folder(auth_client, make_folder, make_deck):
    folder1 = make_folder("Folder 1")
    folder2 = make_folder("Folder 2")
    make_deck(folder_id=folder2, name="Existing")
    deck1 = make_deck(folder_id=folder1, name="ToMove")

    response = auth_client.put(
        f"/api/decks/{deck1}",
        data={"name": "existing", "folder_id": folder2, "new_per_day": "10", "paused": 0},
    )
    assert response.status_code == 400


def test_update_deck_rejects_disallowed_daily_limit(auth_client, make_folder, make_deck):
    folder_id = make_folder()
    deck_id = make_deck(folder_id=folder_id)

    response = auth_client.put(
        f"/api/decks/{deck_id}",
        data={"name": "Deck", "folder_id": folder_id, "new_per_day": "7"},
    )
    assert response.status_code == 400


def test_update_deck_requires_owned_deck(client, auth_client, make_folder, make_deck):
    folder_id = make_folder()
    deck_id = make_deck(folder_id=folder_id)

    signup_user(client, email="other@example.com")
    response = client.put(
        f"/api/decks/{deck_id}",
        data={"name": "Hacked", "folder_id": folder_id, "new_per_day": "10"},
    )
    assert response.status_code == 404


def test_deck_settings_update_only_the_selected_deck(auth_client, make_folder, make_deck):
    folder_id = make_folder()
    first = make_deck(folder_id=folder_id, name="First")
    second = make_deck(folder_id=folder_id, name="Second")

    response = auth_client.post(
        f"/api/decks/{first}/settings",
        data={"new_per_day": "20", "paused": 1},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    with db.conn() as c:
        first_row = c.execute("SELECT new_per_day, paused FROM decks WHERE id=?", (first,)).fetchone()
        second_row = c.execute("SELECT new_per_day, paused FROM decks WHERE id=?", (second,)).fetchone()
        assert first_row["new_per_day"] == 20
        assert first_row["paused"] == 1
        assert second_row["new_per_day"] == 10
        assert second_row["paused"] == 0


def test_deck_settings_reject_a_disallowed_daily_limit(auth_client, make_deck):
    deck_id = make_deck()

    response = auth_client.post(
        f"/api/decks/{deck_id}/settings",
        data={"new_per_day": "7", "paused": 0},
    )
    assert response.status_code == 400


def test_deck_settings_require_an_owned_deck(auth_client):
    response = auth_client.post("/api/decks/9999/settings", data={"new_per_day": "10"})
    assert response.status_code == 404


def test_pin_deck_toggles_pinned_flag(auth_client, make_deck):
    deck_id = make_deck()

    pin_resp = auth_client.post(f"/api/decks/{deck_id}/pin", data={"pinned": 1})
    assert pin_resp.status_code == 200
    with db.conn() as c:
        assert c.execute("SELECT pinned FROM decks WHERE id=?", (deck_id,)).fetchone()["pinned"] == 1

    unpin_resp = auth_client.post(f"/api/decks/{deck_id}/pin", data={"pinned": 0})
    assert unpin_resp.status_code == 200
    with db.conn() as c:
        assert c.execute("SELECT pinned FROM decks WHERE id=?", (deck_id,)).fetchone()["pinned"] == 0


def test_delete_deck_removes_deck_and_cascades_cards(auth_client, make_deck, make_card):
    deck_id = make_deck()
    card_id = make_card(deck_id=deck_id)

    assert auth_client.delete(f"/api/decks/{deck_id}").json() == {"ok": True}
    assert auth_client.get(f"/api/decks/{deck_id}/cards").status_code == 404

    with db.conn() as c:
        assert c.execute("SELECT COUNT(*) FROM decks WHERE id=?", (deck_id,)).fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM cards WHERE id=?", (card_id,)).fetchone()[0] == 0


def test_delete_deck_requires_owned_deck(client, auth_client, make_deck):
    deck_id = make_deck()

    signup_user(client, email="other@example.com")
    assert client.delete(f"/api/decks/{deck_id}").status_code == 404


def test_deck_order_rejects_bad_input(auth_client, make_deck):
    make_deck()
    assert auth_client.post("/api/decks/order", data={"ids": "abc"}).status_code == 400
    assert auth_client.post("/api/decks/order", data={"ids": [1, 1]}).status_code == 400
    assert auth_client.post("/api/decks/order", data={"ids": [9999]}).status_code == 400


def test_deck_order_reshuffles_only_the_submitted_subset(auth_client, make_folder, make_deck):
    folder_id = make_folder()
    first = make_deck(folder_id=folder_id, name="First")
    second = make_deck(folder_id=folder_id, name="Second")
    third = make_deck(folder_id=folder_id, name="Third")

    # Reshuffle first and third, leaving second in the middle
    assert auth_client.post("/api/decks/order", data={"ids": [third, first]}).status_code == 200

    with db.conn() as c:
        positions = dict(c.execute("SELECT id, pos FROM decks WHERE id IN (?,?,?)", (first, second, third)).fetchall())
        assert positions[third] < positions[second] < positions[first]
