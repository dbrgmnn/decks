from app import db, srs
from tests.conftest import signup_user


def test_single_deck_queue_serves_new_card_and_stops_when_quota_exhausted(auth_client, make_deck, make_card):
    # Create a deck with new_per_day=1
    deck_id = make_deck(name="Deck", new_per_day="1")
    card_id = make_card(deck_id=deck_id, front="Question", back="Answer")

    card = auth_client.get(f"/api/next/{deck_id}").json()
    assert card is not None
    assert card["id"] == card_id
    assert card["kind"] == "new"
    assert card["deck_id"] == deck_id
    assert card["front"] == "Question"
    assert card["back"] == "Answer"
    assert card["left"] == 1

    # Rating the card consumes the 1 new-card quota for today
    rate_resp = auth_client.post(f"/api/rate/{card_id}", data={"rating": 3})
    assert rate_resp.status_code == 200

    assert auth_client.get(f"/api/next/{deck_id}").json() is None


def test_rate_card_updates_state_and_records_review(auth_client, make_deck, make_card):
    deck_id = make_deck()
    card_id = make_card(deck_id=deck_id, front="Front", back="Back")

    # Before rating, state and due are NULL
    with db.conn() as c:
        row = c.execute("SELECT state, due FROM cards WHERE id=?", (card_id,)).fetchone()
        assert row["state"] is None
        assert row["due"] is None

    response = auth_client.post(f"/api/rate/{card_id}", data={"rating": 3})
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    with db.conn() as c:
        row = c.execute("SELECT state, due FROM cards WHERE id=?", (card_id,)).fetchone()
        assert row["state"] is not None
        assert row["due"] is not None

        review = c.execute("SELECT card_id, rating FROM reviews WHERE card_id=?", (card_id,)).fetchone()
        assert review is not None
        assert review["rating"] == 3


def test_rate_card_rejects_invalid_ratings(auth_client, make_card):
    card_id = make_card()
    for invalid in (0, 5, -1, "abc"):
        response = auth_client.post(f"/api/rate/{card_id}", data={"rating": invalid})
        assert response.status_code in (400, 422)


def test_rate_card_requires_owned_card(client, auth_client, make_card):
    card_id = make_card()

    signup_user(client, email="other@example.com")
    assert client.post(f"/api/rate/{card_id}", data={"rating": 3}).status_code == 404


def test_undo_card_reverts_review_and_restores_previous_state(auth_client, make_card):
    card_id = make_card()

    # Rate the card
    auth_client.post(f"/api/rate/{card_id}", data={"rating": 3})
    with db.conn() as c:
        assert c.execute("SELECT COUNT(*) FROM reviews WHERE card_id=?", (card_id,)).fetchone()[0] == 1

    # Undo the review, passing previous empty state and due
    undo_resp = auth_client.post(
        f"/api/undo/{card_id}",
        data={"prev_state": "", "prev_due": ""},
    )
    assert undo_resp.status_code == 200
    assert undo_resp.json() == {"ok": True}

    with db.conn() as c:
        assert c.execute("SELECT COUNT(*) FROM reviews WHERE card_id=?", (card_id,)).fetchone()[0] == 0
        card_row = c.execute("SELECT state, due FROM cards WHERE id=?", (card_id,)).fetchone()
        assert card_row["state"] is None
        assert card_row["due"] is None


def test_undo_card_rejects_when_nothing_to_undo(auth_client, make_card):
    card_id = make_card()

    # No rating performed yet
    response = auth_client.post(f"/api/undo/{card_id}", data={"prev_state": "", "prev_due": ""})
    assert response.status_code == 400


def test_undo_card_requires_owned_card(client, auth_client, make_card):
    card_id = make_card()
    auth_client.post(f"/api/rate/{card_id}", data={"rating": 3})

    signup_user(client, email="other@example.com")
    assert client.post(f"/api/undo/{card_id}").status_code == 404


def test_due_reviews_served_before_new_cards(auth_client, make_deck, make_card):
    deck_id = make_deck()
    # Create two cards
    first_id = make_card(deck_id=deck_id, front="Due Card", back="Back 1")
    second_id = make_card(deck_id=deck_id, front="New Card", back="Back 2")

    # Set the first card to be due in the past
    past_due = "2020-01-01T00:00:00+00:00"
    with db.conn() as c:
        c.execute("UPDATE cards SET state='{}', due=? WHERE id=?", (past_due, first_id))

    served = auth_client.get(f"/api/next/{deck_id}").json()
    assert served is not None
    assert served["id"] == first_id
    assert served["kind"] == "review"
    assert served["front"] == "Due Card"


def test_paused_deck_is_not_served(auth_client, make_deck, make_card):
    deck_id = make_deck()
    make_card(deck_id=deck_id)

    assert auth_client.get(f"/api/next/{deck_id}").json() is not None

    # Pause deck
    auth_client.post(f"/api/decks/{deck_id}/settings", data={"new_per_day": "10", "paused": 1})
    assert auth_client.get(f"/api/next/{deck_id}").json() is None


def test_active_queue_serves_across_active_decks_and_skips_paused(auth_client, make_deck, make_card):
    active_deck = make_deck(name="Active")
    paused_deck = make_deck(name="Paused")

    make_card(deck_id=active_deck, front="Active Front", back="Back")
    make_card(deck_id=paused_deck, front="Paused Front", back="Back")

    auth_client.post(f"/api/decks/{paused_deck}/settings", data={"new_per_day": "10", "paused": 1})

    served = auth_client.get("/api/next/active").json()
    assert served is not None
    assert served["deck_id"] == active_deck
    assert served["front"] == "Active Front"


def test_active_queue_returns_none_when_empty_or_all_paused(auth_client, make_deck, make_card):
    deck_id = make_deck()
    make_card(deck_id=deck_id)

    auth_client.post(f"/api/decks/{deck_id}/settings", data={"new_per_day": "10", "paused": 1})
    assert auth_client.get("/api/next/active").json() is None


def test_study_next_requires_owned_deck(client, auth_client, make_deck):
    deck_id = make_deck()

    signup_user(client, email="other@example.com")
    assert client.get(f"/api/next/{deck_id}").status_code == 404
