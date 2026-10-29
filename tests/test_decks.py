from app import db
from tests.conftest import signup_user


def test_create_deck_success(auth_client):
    response = auth_client.post("/api/decks", data={"name": "Spanish"})
    assert response.status_code == 200
    deck_id = response.json()["id"]

    with db.conn() as c:
        row = c.execute(
            "SELECT name, pos, new_per_day, paused FROM decks WHERE id=?", (deck_id,)
        ).fetchone()
        assert row["name"] == "Spanish"
        assert row["pos"] == 1
        assert row["new_per_day"] == 10
        assert row["paused"] == 0


def test_create_deck_rejects_duplicate_name(auth_client, make_deck):
    make_deck(name="Deck")

    duplicate = auth_client.post("/api/decks", data={"name": "deck"})
    assert duplicate.status_code == 400


def test_create_deck_allows_same_name_for_another_user(client, auth_client, make_deck):
    make_deck(name="Deck")

    signup_user(client, email="other@example.com")
    response = client.post("/api/decks", data={"name": "Deck"})
    assert response.status_code == 200


def test_update_deck_renames_and_changes_settings(auth_client, make_deck):
    deck_id = make_deck(name="Original")

    response = auth_client.put(
        f"/api/decks/{deck_id}",
        data={"name": "Renamed", "new_per_day": "20", "paused": 1},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    with db.conn() as c:
        row = c.execute(
            "SELECT name, new_per_day, paused FROM decks WHERE id=?", (deck_id,)
        ).fetchone()
        assert row["name"] == "Renamed"
        assert row["new_per_day"] == 20
        assert row["paused"] == 1


def test_update_deck_rejects_duplicate_name(auth_client, make_deck):
    make_deck(name="Existing")
    deck_id = make_deck(name="ToRename")

    response = auth_client.put(
        f"/api/decks/{deck_id}",
        data={"name": "existing", "new_per_day": "10", "paused": 0},
    )
    assert response.status_code == 400


def test_update_deck_rejects_disallowed_daily_limit(auth_client, make_deck):
    deck_id = make_deck()

    response = auth_client.put(
        f"/api/decks/{deck_id}",
        data={"name": "Deck", "new_per_day": "7"},
    )
    assert response.status_code == 400


def test_update_deck_requires_owned_deck(client, auth_client, make_deck):
    deck_id = make_deck()

    signup_user(client, email="other@example.com")
    response = client.put(
        f"/api/decks/{deck_id}",
        data={"name": "Hacked", "new_per_day": "10"},
    )
    assert response.status_code == 404


def test_deck_settings_update_only_the_selected_deck(auth_client, make_deck):
    first = make_deck(name="First")
    second = make_deck(name="Second")

    response = auth_client.post(
        f"/api/decks/{first}/settings",
        data={"new_per_day": "20", "paused": 1},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    with db.conn() as c:
        first_row = c.execute(
            "SELECT new_per_day, paused FROM decks WHERE id=?", (first,)
        ).fetchone()
        second_row = c.execute(
            "SELECT new_per_day, paused FROM decks WHERE id=?", (second,)
        ).fetchone()
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
    deck_id = make_deck()
    assert auth_client.post("/api/decks/order", data={"ids": "abc"}).status_code == 400
    assert auth_client.post("/api/decks/order", data={"ids": [deck_id, deck_id]}).status_code == 400
    assert auth_client.post("/api/decks/order", data={"ids": [9999]}).status_code == 400


def test_deck_order_reshuffles_only_the_submitted_subset(auth_client, make_deck):
    first = make_deck(name="First")
    second = make_deck(name="Second")
    third = make_deck(name="Third")

    # Reshuffle first and third, leaving second in the middle.
    assert auth_client.post("/api/decks/order", data={"ids": [third, first]}).status_code == 200

    with db.conn() as c:
        positions = dict(
            c.execute(
                "SELECT id, pos FROM decks WHERE id IN (?,?,?)", (first, second, third)
            ).fetchall()
        )
        assert positions[third] < positions[second] < positions[first]
