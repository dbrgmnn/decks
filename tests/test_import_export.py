import io

import pytest
from fastapi import HTTPException, UploadFile

from app import db
from app.routes import import_export
from tests.conftest import signup_user


def test_max_csv_bytes_is_five_mb():
    assert import_export.MAX_CSV_BYTES == 5 * 1024 * 1024


def test_import_rejects_non_csv_filename():
    upload = UploadFile(file=io.BytesIO(b"a,b"), filename="cards.txt")
    with pytest.raises(HTTPException) as exc:
        import_export.import_cards_csv(file=upload, user={"id": 1})
    assert exc.value.status_code == 400


def test_import_rejects_oversized_file():
    upload = UploadFile(
        file=io.BytesIO(b"x" * (import_export.MAX_CSV_BYTES + 2)),
        filename="cards.csv",
    )
    with pytest.raises(HTTPException) as exc:
        import_export.import_cards_csv(file=upload, user={"id": 1})
    assert exc.value.status_code == 413


def test_import_rejects_invalid_csv_columns():
    upload = UploadFile(file=io.BytesIO(b"foo,bar\n1,2\n"), filename="cards.csv")
    with pytest.raises(HTTPException) as exc:
        import_export.import_cards_csv(file=upload, user={"id": 1})
    assert exc.value.status_code == 400


def test_import_rejects_unknown_columns():
    upload = UploadFile(
        file=io.BytesIO(b"extra,deck,front,back,note\nX,D,f,b,n\n"),
        filename="cards.csv",
    )
    with pytest.raises(HTTPException) as exc:
        import_export.import_cards_csv(file=upload, user={"id": 1})
    assert exc.value.status_code == 400


def test_import_rejects_field_past_csv_size_limit():
    body = b"deck,front,back,note,tags\nD,f,b,," + b"x" * 200000 + b"\n"
    upload = UploadFile(file=io.BytesIO(body), filename="cards.csv")
    with pytest.raises(HTTPException) as exc:
        import_export.import_cards_csv(file=upload, user={"id": 1})
    assert exc.value.status_code == 400


def test_import_accepts_semicolon_and_comma_delimiters(auth_client):
    body_semicolon = (
        "deck;front;back;note;tags\n"
        'D1;"front; with semicolon";back;note, with comma;A1,food\n'
    )
    res_semi = auth_client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", body_semicolon.encode(), "text/csv")},
    )
    assert res_semi.status_code == 200
    assert res_semi.json() == {"ok": True, "decks": 1, "cards": 1}

    body_comma = 'deck,front,back,note,tags\nD2,f,b,n,"A1,food"\n'
    res_comma = auth_client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", body_comma.encode(), "text/csv")},
    )
    assert res_comma.status_code == 200
    assert res_comma.json() == {"ok": True, "decks": 1, "cards": 1}


def test_import_stores_tags(auth_client):
    body = 'deck,front,back,note,tags\nD,front,back,,"A1, food"\n'
    response = auth_client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", body.encode(), "text/csv")},
    )
    assert response.status_code == 200

    with db.conn() as c:
        tags = c.execute("SELECT tags FROM cards").fetchone()["tags"]
    assert tags == "A1,food"


def test_import_skips_existing_duplicate_cards(auth_client):
    body = "deck,front,back,note,tags\nD,front,back,note,A1\n"
    first = auth_client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", body.encode(), "text/csv")},
    )
    assert first.json()["cards"] == 1

    second = auth_client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", body.encode(), "text/csv")},
    )
    # Decks and cards are reused / skipped.
    assert second.json() == {"ok": True, "decks": 0, "cards": 0}


def test_import_reuses_deck_names_case_insensitively(auth_client, make_deck):
    make_deck(name="Deck")

    body = "deck,front,back,note,tags\ndeck,front,back,,\n"
    response = auth_client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", body.encode(), "text/csv")},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "decks": 0, "cards": 1}


def test_export_all_and_deck_scopes(auth_client, make_deck, make_card):
    deck1 = make_deck(name="Deck 1")
    make_card(deck_id=deck1, front="Front 1", back="Back 1", note="Note 1", tags=["A1"])

    deck2 = make_deck(name="Deck 2")
    make_card(deck_id=deck2, front="Front 2", back="Back 2", note="Note 2", tags=["B1"])

    # Export all
    all_resp = auth_client.post("/api/export/cards.csv", data={"scope": "all"})
    assert all_resp.status_code == 200
    all_text = all_resp.text
    assert all_text.lstrip("\ufeff").startswith("deck,front,back,note,tags")
    assert "Front 1" in all_text and "Front 2" in all_text
    assert ",A1\r\n" in all_text and ",B1\r\n" in all_text

    # Export deck 2 only
    d_resp = auth_client.post("/api/export/cards.csv", data={"scope": "deck", "deck_id": deck2})
    assert d_resp.status_code == 200
    d_text = d_resp.text
    assert "Front 2" in d_text
    assert "Front 1" not in d_text


def test_export_round_trips_through_import(auth_client, make_deck, make_card):
    deck_id = make_deck(name="Round Trip")
    make_card(deck_id=deck_id, front="Front", back="Back", note="Note", tags=["A1", "food"])

    exported = auth_client.post("/api/export/cards.csv", data={"scope": "all"})
    assert exported.status_code == 200

    # A second user imports the exported file into a fresh account.
    signup_user(auth_client, email="second@example.com")
    imported = auth_client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", exported.content, "text/csv")},
    )
    assert imported.status_code == 200
    assert imported.json() == {"ok": True, "decks": 1, "cards": 1}


def test_export_requires_valid_scope_and_ownership(client, auth_client, make_deck):
    deck_id = make_deck()

    # Missing ID
    assert auth_client.post("/api/export/cards.csv", data={"scope": "deck", "deck_id": 0}).status_code == 400
    assert auth_client.post("/api/export/cards.csv", data={"scope": "unknown"}).status_code == 400

    # Foreign deck
    signup_user(client, email="other@example.com")
    assert client.post("/api/export/cards.csv", data={"scope": "deck", "deck_id": deck_id}).status_code == 404


def test_import_skips_non_ascii_duplicates(auth_client):
    body = "deck,front,back,note,tags\nDeck,Привет,Hello,,\nDeck,привет,Hello,,\n"
    response = auth_client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", body.encode(), "text/csv")},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "decks": 1, "cards": 1}
