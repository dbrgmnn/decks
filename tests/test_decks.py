import re


def signup(client, email="decks@example.com", password="GoodPass123"):
    response = client.post(
        "/api/signup",
        data={"email": email, "password": password, "password2": password, "tz": "UTC"},
    )
    assert response.status_code == 200, response.text


def make_folder(client, name="Folder"):
    response = client.post("/api/quick-add", data={"text": name})
    assert response.status_code == 200, response.text
    return response.json()["folder"]["id"]


def make_deck(client, folder_id, name="Deck"):
    response = client.post("/api/decks", data={"name": name, "folder_id": folder_id})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_create_deck_rejects_duplicate_name_in_folder(client):
    signup(client)
    folder_id = make_folder(client)
    make_deck(client, folder_id, "Deck")

    duplicate = client.post("/api/decks", data={"name": "deck", "folder_id": folder_id})
    assert duplicate.status_code == 400


def test_create_deck_requires_an_owned_folder(client):
    signup(client)
    missing = client.post("/api/decks", data={"name": "Deck", "folder_id": 0})
    assert missing.status_code == 400


def test_update_deck_rejects_disallowed_daily_limit(client):
    signup(client)
    folder_id = make_folder(client)
    deck_id = make_deck(client, folder_id)

    response = client.put(
        f"/api/decks/{deck_id}",
        data={"name": "Deck", "folder_id": folder_id, "new_per_day": "7"},
    )
    assert response.status_code == 400


def test_delete_deck_removes_it(client):
    signup(client)
    folder_id = make_folder(client)
    deck_id = make_deck(client, folder_id)

    assert client.delete(f"/api/decks/{deck_id}").json() == {"ok": True}
    assert client.get(f"/api/decks/{deck_id}/cards").status_code == 404


def test_deck_order_rejects_bad_input(client):
    signup(client)
    assert client.post("/api/decks/order", data={"ids": "abc"}).status_code == 400


def test_deck_order_reshuffles_only_the_submitted_subset(client):
    signup(client)
    folder_id = make_folder(client)
    first = make_deck(client, folder_id, "First")
    second = make_deck(client, folder_id, "Second")

    assert client.post("/api/decks/order", data={"ids": [second, first]}).status_code == 200

    html = client.get(f"/?folder={folder_id}").text
    ids = re.findall(r'<article class="deck[^"]*" data-id="(\d+)"', html)
    assert ids == [str(second), str(first)]


def test_deck_delete_targets_the_edited_deck(client):
    # The delete button must use the deck shown in the edit sheet, never the last
    # deck whose cards were opened, or it can delete the wrong deck.
    source = client.get("/static/modules/decks.js").text
    assert "getCurrentDeck" not in source
    assert "deckEditSheet.dataset.deckId" in source
