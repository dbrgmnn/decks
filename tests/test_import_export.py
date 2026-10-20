import io

import pytest
from fastapi import HTTPException, UploadFile

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


def test_import_rejects_field_past_csv_size_limit():
    body = b"folder,deck,front,back,note\nF,D,f,b," + b"x" * 200000 + b"\n"
    upload = UploadFile(file=io.BytesIO(body), filename="cards.csv")
    with pytest.raises(HTTPException) as exc:
        import_export.import_cards_csv(file=upload, user={"id": 1})
    assert exc.value.status_code == 400


def test_import_accepts_semicolon_and_comma_delimiters(auth_client):
    body_semicolon = (
        "folder;deck;front;back;note\n"
        'F1;D1;"front; with semicolon";back;note, with comma\n'
    )
    res_semi = auth_client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", body_semicolon.encode(), "text/csv")},
    )
    assert res_semi.status_code == 200
    assert res_semi.json() == {"ok": True, "folders": 1, "decks": 1, "cards": 1}

    body_comma = "folder,deck,front,back,note\nF2,D2,f,b,n\n"
    res_comma = auth_client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", body_comma.encode(), "text/csv")},
    )
    assert res_comma.status_code == 200
    assert res_comma.json() == {"ok": True, "folders": 1, "decks": 1, "cards": 1}


def test_import_skips_existing_duplicate_cards(auth_client):
    body = "folder,deck,front,back,note\nF,D,front,back,note\n"
    first = auth_client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", body.encode(), "text/csv")},
    )
    assert first.json()["cards"] == 1

    second = auth_client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", body.encode(), "text/csv")},
    )
    # Folders, decks and cards are reused / skipped
    assert second.json() == {"ok": True, "folders": 0, "decks": 0, "cards": 0}


def test_export_all_folder_and_deck_scopes(auth_client, make_folder, make_deck, make_card):
    folder1 = make_folder("Folder 1")
    deck1 = make_deck(folder_id=folder1, name="Deck 1")
    make_card(deck_id=deck1, front="Front 1", back="Back 1", note="Note 1")

    folder2 = make_folder("Folder 2")
    deck2 = make_deck(folder_id=folder2, name="Deck 2")
    make_card(deck_id=deck2, front="Front 2", back="Back 2", note="Note 2")

    # Export all
    all_resp = auth_client.post("/api/export/cards.csv", data={"scope": "all"})
    assert all_resp.status_code == 200
    all_text = all_resp.text
    assert "Front 1" in all_text and "Front 2" in all_text

    # Export folder 1 only
    f_resp = auth_client.post("/api/export/cards.csv", data={"scope": "folder", "folder_id": folder1})
    assert f_resp.status_code == 200
    f_text = f_resp.text
    assert "Front 1" in f_text
    assert "Front 2" not in f_text

    # Export deck 2 only
    d_resp = auth_client.post("/api/export/cards.csv", data={"scope": "deck", "deck_id": deck2})
    assert d_resp.status_code == 200
    d_text = d_resp.text
    assert "Front 2" in d_text
    assert "Front 1" not in d_text


def test_export_requires_valid_scope_and_ownership(client, auth_client, make_folder, make_deck):
    folder_id = make_folder()
    deck_id = make_deck(folder_id=folder_id)

    # Missing ID
    assert auth_client.post("/api/export/cards.csv", data={"scope": "folder", "folder_id": 0}).status_code == 400
    assert auth_client.post("/api/export/cards.csv", data={"scope": "deck", "deck_id": 0}).status_code == 400
    assert auth_client.post("/api/export/cards.csv", data={"scope": "unknown"}).status_code == 400

    # Foreign folder / deck
    signup_user(client, email="other@example.com")
    assert client.post("/api/export/cards.csv", data={"scope": "folder", "folder_id": folder_id}).status_code == 404
    assert client.post("/api/export/cards.csv", data={"scope": "deck", "deck_id": deck_id}).status_code == 404
