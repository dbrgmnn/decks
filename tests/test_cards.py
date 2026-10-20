from tests.conftest import signup_user


def test_create_card_success(auth_client, make_deck):
    deck_id = make_deck(name="French")
    response = auth_client.post(
        "/api/cards",
        data={"deck_id": deck_id, "front": "Bonjour", "back": "Hello", "note": "greeting"},
    )
    assert response.status_code == 200
    card_id = response.json()["id"]

    cards = auth_client.get(f"/api/decks/{deck_id}/cards").json()
    assert len(cards) == 1
    assert cards[0] == {
        "id": card_id,
        "front": "Bonjour",
        "back": "Hello",
        "note": "greeting",
    }


def test_create_card_rejects_empty_required_fields(auth_client, make_deck):
    deck_id = make_deck()
    empty_front = auth_client.post(
        "/api/cards",
        data={"deck_id": deck_id, "front": "   ", "back": "Back"},
    )
    assert empty_front.status_code == 400

    empty_back = auth_client.post(
        "/api/cards",
        data={"deck_id": deck_id, "front": "Front", "back": "   "},
    )
    assert empty_back.status_code == 400


def test_create_card_rejects_too_long_fields(auth_client, make_deck):
    deck_id = make_deck()
    too_long_front = auth_client.post(
        "/api/cards",
        data={"deck_id": deck_id, "front": "a" * 201, "back": "Back"},
    )
    assert too_long_front.status_code == 400

    too_long_note = auth_client.post(
        "/api/cards",
        data={"deck_id": deck_id, "front": "Front", "back": "Back", "note": "n" * 301},
    )
    assert too_long_note.status_code == 400


def test_create_card_rejects_duplicate_in_same_deck(auth_client, make_deck):
    deck_id = make_deck()
    first = auth_client.post(
        "/api/cards",
        data={"deck_id": deck_id, "front": "Hello", "back": "World"},
    )
    assert first.status_code == 200

    duplicate = auth_client.post(
        "/api/cards",
        data={"deck_id": deck_id, "front": "hello", "back": "WORLD"},
    )
    assert duplicate.status_code == 400


def test_create_card_allows_same_text_in_different_decks(auth_client, make_deck):
    first_deck = make_deck(name="Deck1")
    second_deck = make_deck(name="Deck2")

    first = auth_client.post(
        "/api/cards",
        data={"deck_id": first_deck, "front": "Hello", "back": "World"},
    )
    second = auth_client.post(
        "/api/cards",
        data={"deck_id": second_deck, "front": "Hello", "back": "World"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] != second.json()["id"]


def test_create_card_requires_owned_deck(client, auth_client, make_deck):
    foreign_deck_id = make_deck()

    # Create a second user and try to add a card into the first user's deck
    signup_user(client, email="other@example.com")
    response = client.post(
        "/api/cards",
        data={"deck_id": foreign_deck_id, "front": "Steal", "back": "Deck"},
    )
    assert response.status_code == 404


def test_update_card_success(auth_client, make_card):
    card_id = make_card(front="Old Front", back="Old Back", note="Old Note")

    response = auth_client.put(
        f"/api/cards/{card_id}",
        data={"front": "New Front", "back": "New Back", "note": "New Note"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_update_card_allows_keeping_same_text(auth_client, make_card):
    card_id = make_card(front="Same Front", back="Same Back")

    response = auth_client.put(
        f"/api/cards/{card_id}",
        data={"front": "Same Front", "back": "Same Back", "note": "Added Note"},
    )
    assert response.status_code == 200


def test_update_card_rejects_duplicate_with_another_card_in_deck(auth_client, make_deck, make_card):
    deck_id = make_deck()
    make_card(deck_id=deck_id, front="Card 1", back="Back 1")
    second_id = make_card(deck_id=deck_id, front="Card 2", back="Back 2")

    # Trying to update second card to have the same front/back as the first
    response = auth_client.put(
        f"/api/cards/{second_id}",
        data={"front": "card 1", "back": "back 1"},
    )
    assert response.status_code == 400


def test_update_card_requires_owned_card(client, auth_client, make_card):
    foreign_card_id = make_card()

    signup_user(client, email="attacker@example.com")
    response = client.put(
        f"/api/cards/{foreign_card_id}",
        data={"front": "Hacked", "back": "Hacked"},
    )
    assert response.status_code == 404


def test_delete_card_removes_it(auth_client, make_deck, make_card):
    deck_id = make_deck()
    card_id = make_card(deck_id=deck_id)

    assert auth_client.delete(f"/api/cards/{card_id}").json() == {"ok": True}

    cards = auth_client.get(f"/api/decks/{deck_id}/cards").json()
    assert len(cards) == 0


def test_delete_card_requires_owned_card(client, auth_client, make_card):
    foreign_card_id = make_card()

    signup_user(client, email="attacker@example.com")
    assert client.delete(f"/api/cards/{foreign_card_id}").status_code == 404


def test_get_deck_cards_orders_by_id_descending(auth_client, make_deck, make_card):
    deck_id = make_deck()
    first_id = make_card(deck_id=deck_id, front="One", back="One")
    second_id = make_card(deck_id=deck_id, front="Two", back="Two")

    cards = auth_client.get(f"/api/decks/{deck_id}/cards").json()
    assert [c["id"] for c in cards] == [second_id, first_id]


def test_get_deck_cards_requires_owned_deck(client, auth_client, make_deck):
    deck_id = make_deck()

    signup_user(client, email="other@example.com")
    assert client.get(f"/api/decks/{deck_id}/cards").status_code == 404
