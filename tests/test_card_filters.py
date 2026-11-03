def _create(auth_client, deck_id, front, tags=None):
    response = auth_client.post(
        "/api/cards",
        json={
            "deck_id": deck_id,
            "front": front,
            "back": f"back {front}",
            "tags": tags or [],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["card"]["id"]


def test_recent_cards_returns_the_latest_fifty(auth_client, make_deck):
    deck_id = make_deck(name="Big")
    card_ids = [_create(auth_client, deck_id, f"Front {index}") for index in range(55)]

    response = auth_client.get(f"/api/decks/{deck_id}/cards", params={"recent": 1})

    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "55"
    assert [card["id"] for card in response.json()] == list(reversed(card_ids))[:50]


def test_cards_without_filters_still_return_the_whole_deck(auth_client, make_deck):
    deck_id = make_deck(name="Big")
    for index in range(55):
        _create(auth_client, deck_id, f"Front {index}")

    response = auth_client.get(f"/api/decks/{deck_id}/cards")

    assert response.headers["X-Total-Count"] == "55"
    assert len(response.json()) == 55


def test_card_search_covers_the_whole_deck(auth_client, make_deck):
    deck_id = make_deck(name="Fruit")
    for front in ["Apple", "Apricot", "Banana"]:
        _create(auth_client, deck_id, front)

    response = auth_client.get(f"/api/decks/{deck_id}/cards", params={"q": "AP"})

    assert [card["front"] for card in response.json()] == ["Apricot", "Apple"]


def test_card_search_is_case_insensitive_for_non_ascii(auth_client, make_deck):
    deck_id = make_deck()
    _create(auth_client, deck_id, "Привет")
    _create(auth_client, deck_id, "Äpfel")

    cyrillic = auth_client.get(f"/api/decks/{deck_id}/cards", params={"q": "ПРИВЕТ"}).json()
    umlaut = auth_client.get(f"/api/decks/{deck_id}/cards", params={"q": "äPFEL"}).json()

    assert [card["front"] for card in cyrillic] == ["Привет"]
    assert [card["front"] for card in umlaut] == ["Äpfel"]


def test_card_tag_filter_is_exact_and_case_insensitive(auth_client, make_deck):
    deck_id = make_deck()
    _create(auth_client, deck_id, "One", tags=["A1"])
    _create(auth_client, deck_id, "Ten", tags=["A10"])
    _create(auth_client, deck_id, "Two", tags=["a1", "B2"])
    _create(auth_client, deck_id, "Food", tags=["Еда"])

    a1 = auth_client.get(f"/api/decks/{deck_id}/cards", params={"tag": "A1"}).json()
    food = auth_client.get(f"/api/decks/{deck_id}/cards", params={"tag": "еда"}).json()

    assert {card["front"] for card in a1} == {"One", "Two"}
    assert [card["front"] for card in food] == ["Food"]


def test_search_and_tag_filter_combine(auth_client, make_deck):
    deck_id = make_deck()
    _create(auth_client, deck_id, "Apple", tags=["Fruit"])
    _create(auth_client, deck_id, "Apricot", tags=["Fruit"])
    _create(auth_client, deck_id, "Avocado", tags=["Other"])

    fruit = auth_client.get(
        f"/api/decks/{deck_id}/cards", params={"q": "ap", "tag": "Fruit"}
    ).json()
    other = auth_client.get(
        f"/api/decks/{deck_id}/cards", params={"q": "ap", "tag": "Other"}
    ).json()

    assert [card["front"] for card in fruit] == ["Apricot", "Apple"]
    assert other == []


def test_deck_tags_are_unique_and_sorted(auth_client, make_deck):
    deck_id = make_deck()
    _create(auth_client, deck_id, "One", tags=["B2", "A1"])
    _create(auth_client, deck_id, "Two", tags=["a1", "C3"])

    response = auth_client.get(f"/api/decks/{deck_id}/tags")

    assert response.status_code == 200
    assert response.json() == ["A1", "B2", "C3"]


def test_deck_tags_require_an_owned_deck(auth_client):
    assert auth_client.get("/api/decks/9999/tags").status_code == 404
