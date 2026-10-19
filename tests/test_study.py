def signup(client, email="study@example.com", password="GoodPass123"):
    response = client.post(
        "/api/signup",
        data={"email": email, "password": password, "password2": password, "tz": "UTC"},
    )
    assert response.status_code == 200, response.text


def add_card(client, text):
    return client.post("/api/quick-add", data={"text": text}).json()


def test_single_deck_queue_serves_then_stops(client):
    signup(client)
    result = add_card(client, "F/D/front/back")
    deck_id = result["deck"]["id"]

    first = client.get(f"/api/next/{deck_id}").json()
    assert first["kind"] == "new"
    assert first["deck_id"] == deck_id
    assert first["front"] == "front"
    assert first["left"] == 1

    assert client.post(f"/api/rate/{first['id']}", data={"rating": 3}).status_code == 200
    # The card is now scheduled ahead, and the quota is spent for today.
    assert client.get(f"/api/next/{deck_id}").json() is None


def test_paused_deck_is_not_served_by_the_api(client):
    signup(client)
    result = add_card(client, "F/D/front/back")
    deck_id = result["deck"]["id"]
    folder_id = result["folder"]["id"]

    assert client.get(f"/api/next/{deck_id}").json() is not None

    paused = client.put(
        f"/api/decks/{deck_id}",
        data={"name": "D", "folder_id": folder_id, "new_per_day": "5", "paused": 1},
    )
    assert paused.status_code == 200
    assert client.get(f"/api/next/{deck_id}").json() is None


def test_active_queue_skips_paused_decks(client):
    signup(client)
    paused = add_card(client, "F/Paused/front/back")
    active = add_card(client, "F/Active/other/back")

    client.put(
        f"/api/decks/{paused['deck']['id']}",
        data={"name": "Paused", "folder_id": paused["folder"]["id"], "new_per_day": "5", "paused": 1},
    )

    served = client.get("/api/next/active").json()
    assert served is not None
    assert served["deck_id"] == active["deck"]["id"]
    assert served["front"] == "other"
    assert served["left"] == 1
