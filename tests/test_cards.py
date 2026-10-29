from tests.conftest import signup_user


def test_create_card_success(auth_client, make_deck):
    deck_id = make_deck(name="French")
    response = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "Bonjour", "back": "Hello", "note": "greeting"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["deck"] == {"id": deck_id, "name": "French", "created": False}
    assert data["card"]["created"] is True
    card_id = data["card"]["id"]

    cards = auth_client.get(f"/api/decks/{deck_id}/cards").json()
    assert len(cards) == 1
    assert cards[0] == {
        "id": card_id,
        "front": "Bonjour",
        "back": "Hello",
        "note": "greeting",
        "tags": [],
    }


def test_create_card_by_deck_name_creates_deck(auth_client):
    response = auth_client.post(
        "/api/cards",
        json={"deck": "French", "front": "Bonjour", "back": "Hello"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["deck"]["created"] is True
    assert data["card"]["created"] is True

    deck_id = data["deck"]["id"]
    cards = auth_client.get(f"/api/decks/{deck_id}/cards").json()
    assert cards[0]["front"] == "Bonjour"


def test_create_card_reuses_existing_deck_by_name(auth_client, make_deck):
    deck_id = make_deck(name="French")

    response = auth_client.post(
        "/api/cards",
        json={"deck": "french", "front": "Bonjour", "back": "Hello"},
    )
    assert response.status_code == 201
    assert response.json()["deck"] == {"id": deck_id, "name": "French", "created": False}


def test_create_card_requires_deck_or_id(auth_client):
    response = auth_client.post(
        "/api/cards",
        json={"front": "Bonjour", "back": "Hello"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "deck_choice"


def test_create_card_rejects_both_deck_and_id(auth_client, make_deck):
    deck_id = make_deck(name="French")

    response = auth_client.post(
        "/api/cards",
        json={"deck": "French", "deck_id": deck_id, "front": "Bonjour", "back": "Hello"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "deck_choice"


def test_create_card_stores_tags(auth_client, make_deck):
    deck_id = make_deck(name="French")
    response = auth_client.post(
        "/api/cards",
        json={
            "deck_id": deck_id,
            "front": "Bonjour",
            "back": "Hello",
            "tags": ["A1", "greeting"],
        },
    )
    assert response.status_code == 201
    assert response.json()["card"]["tags"] == ["A1", "greeting"]

    cards = auth_client.get(f"/api/decks/{deck_id}/cards").json()
    assert cards[0]["tags"] == ["A1", "greeting"]


def test_create_card_drops_duplicate_tags_case_insensitively(auth_client, make_deck):
    deck_id = make_deck()
    auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "Front", "back": "Back", "tags": ["Food", "food", "FOOD"]},
    )

    cards = auth_client.get(f"/api/decks/{deck_id}/cards").json()
    assert cards[0]["tags"] == ["Food"]


def test_create_card_rejects_reserved_tag_character(auth_client, make_deck):
    deck_id = make_deck()
    response = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "Front", "back": "Back", "tags": ["food/drink"]},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "tag_reserved"


def test_create_card_rejects_too_many_tags(auth_client, make_deck):
    deck_id = make_deck()
    response = auth_client.post(
        "/api/cards",
        json={
            "deck_id": deck_id,
            "front": "Front",
            "back": "Back",
            "tags": [f"tag{i}" for i in range(11)],
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "too_many_tags"


def test_create_card_rejects_too_long_tag(auth_client, make_deck):
    deck_id = make_deck()
    response = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "Front", "back": "Back", "tags": ["t" * 61]},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "tag_too_long"


def test_create_card_rejects_empty_required_fields(auth_client, make_deck):
    deck_id = make_deck()
    empty_front = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "   ", "back": "Back"},
    )
    assert empty_front.status_code == 400
    assert empty_front.json()["code"] == "field_required"
    assert empty_front.json()["field"] == "front"

    empty_back = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "Front", "back": "   "},
    )
    assert empty_back.status_code == 400
    assert empty_back.json()["code"] == "field_required"
    assert empty_back.json()["field"] == "back"


def test_create_card_rejects_too_long_fields(auth_client, make_deck):
    deck_id = make_deck()
    too_long_front = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "a" * 201, "back": "Back"},
    )
    assert too_long_front.status_code == 400
    assert too_long_front.json()["code"] == "field_too_long"

    too_long_note = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "Front", "back": "Back", "note": "n" * 301},
    )
    assert too_long_note.status_code == 400
    assert too_long_note.json()["code"] == "field_too_long"


def test_create_card_rejects_duplicate_in_same_deck(auth_client, make_deck):
    deck_id = make_deck()
    first = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "Hello", "back": "World"},
    )
    assert first.status_code == 201

    duplicate = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "hello", "back": "WORLD"},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["card"]["created"] is False
    assert duplicate.json()["card"]["id"] == first.json()["card"]["id"]


def test_create_card_detects_non_ascii_duplicates(auth_client, make_deck):
    deck_id = make_deck()

    first = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "Привет", "back": "Hello"},
    )
    duplicate = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "привет", "back": "Hello"},
    )
    assert first.status_code == 201
    assert duplicate.status_code == 200
    assert duplicate.json()["card"]["id"] == first.json()["card"]["id"]

    umlaut = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "Äpfel", "back": "Apples"},
    )
    umlaut_duplicate = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "äpfel", "back": "Apples"},
    )
    assert umlaut.status_code == 201
    assert umlaut_duplicate.status_code == 200
    assert umlaut_duplicate.json()["card"]["id"] == umlaut.json()["card"]["id"]


def test_create_card_allows_same_text_in_different_decks(auth_client, make_deck):
    first_deck = make_deck(name="Deck1")
    second_deck = make_deck(name="Deck2")

    first = auth_client.post(
        "/api/cards",
        json={"deck_id": first_deck, "front": "Hello", "back": "World"},
    )
    second = auth_client.post(
        "/api/cards",
        json={"deck_id": second_deck, "front": "Hello", "back": "World"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["card"]["id"] != second.json()["card"]["id"]


def test_create_card_requires_owned_deck(client, auth_client, make_deck):
    foreign_deck_id = make_deck()

    # Create a second user and try to add a card into the first user's deck
    signup_user(client, email="other@example.com")
    response = client.post(
        "/api/cards",
        json={"deck_id": foreign_deck_id, "front": "Steal", "back": "Deck"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "deck_not_found"


def test_create_card_rejects_invalid_deck_name(auth_client):
    response = auth_client.post(
        "/api/cards",
        json={"deck": "a/b", "front": "Bonjour", "back": "Hello"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "field_reserved"


def test_create_card_rejects_invalid_json(auth_client):
    response = auth_client.post(
        "/api/cards",
        content="not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
    assert isinstance(response.json()["detail"], str)


def test_create_card_rejects_wrong_types(auth_client, make_deck):
    deck_id = make_deck()
    response = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": 123, "back": "Back"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_create_card_accepts_tags_as_string(auth_client, make_deck):
    deck_id = make_deck()
    response = auth_client.post(
        "/api/cards",
        json={"deck_id": deck_id, "front": "Front", "back": "Back", "tags": "A1, B1; A2"},
    )
    assert response.status_code == 201
    assert response.json()["card"]["tags"] == ["A1", "B1", "A2"]

    cards = auth_client.get(f"/api/decks/{deck_id}/cards").json()
    assert cards[0]["tags"] == ["A1", "B1", "A2"]


def test_update_card_success(auth_client, make_card):
    card_id = make_card(front="Old Front", back="Old Back", note="Old Note")

    response = auth_client.put(
        f"/api/cards/{card_id}",
        json={"front": "New Front", "back": "New Back", "note": "New Note", "tags": ["A2"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["card"] == {
        "id": card_id,
        "front": "New Front",
        "back": "New Back",
        "note": "New Note",
        "tags": ["A2"],
    }


def test_update_card_replaces_tags(auth_client, make_deck, make_card):
    deck_id = make_deck()
    card_id = make_card(deck_id=deck_id, tags=["A1", "old"])

    response = auth_client.put(
        f"/api/cards/{card_id}",
        json={"front": "front", "back": "back", "tags": ["B1"]},
    )
    assert response.status_code == 200

    cards = auth_client.get(f"/api/decks/{deck_id}/cards").json()
    assert cards[0]["tags"] == ["B1"]


def test_update_card_accepts_tags_as_string(auth_client, make_deck, make_card):
    deck_id = make_deck()
    card_id = make_card(deck_id=deck_id, tags=["A1"])

    response = auth_client.put(
        f"/api/cards/{card_id}",
        json={"front": "front", "back": "back", "tags": "B1, B2"},
    )
    assert response.status_code == 200
    assert response.json()["card"]["tags"] == ["B1", "B2"]

    cards = auth_client.get(f"/api/decks/{deck_id}/cards").json()
    assert cards[0]["tags"] == ["B1", "B2"]


def test_update_card_allows_keeping_same_text(auth_client, make_card):
    card_id = make_card(front="Same Front", back="Same Back")

    response = auth_client.put(
        f"/api/cards/{card_id}",
        json={"front": "Same Front", "back": "Same Back", "note": "Added Note"},
    )
    assert response.status_code == 200


def test_update_card_rejects_duplicate_with_another_card_in_deck(auth_client, make_deck, make_card):
    deck_id = make_deck()
    make_card(deck_id=deck_id, front="Card 1", back="Back 1")
    second_id = make_card(deck_id=deck_id, front="Card 2", back="Back 2")

    # Trying to update second card to have the same front/back as the first
    response = auth_client.put(
        f"/api/cards/{second_id}",
        json={"front": "card 1", "back": "back 1"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "card_exists"


def test_update_card_requires_owned_card(client, auth_client, make_card):
    foreign_card_id = make_card()

    signup_user(client, email="attacker@example.com")
    response = client.put(
        f"/api/cards/{foreign_card_id}",
        json={"front": "Hacked", "back": "Hacked"},
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
