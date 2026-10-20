import io

import pytest
from fastapi import HTTPException, UploadFile

from app.routes import import_export


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
    # A field longer than csv's limit used to raise an unhandled csv.Error (500).
    body = b"folder,deck,front,back,note\nF,D,f,b," + b"x" * 200000 + b"\n"
    upload = UploadFile(file=io.BytesIO(body), filename="cards.csv")
    with pytest.raises(HTTPException) as exc:
        import_export.import_cards_csv(file=upload, user={"id": 1})
    assert exc.value.status_code == 400


def _signup(client):
    response = client.post(
        "/api/signup",
        data={"email": "csv@example.com", "password": "GoodPass123", "password2": "GoodPass123", "tz": "UTC"},
    )
    assert response.status_code == 200, response.text


def test_import_accepts_semicolon_delimiter(client):
    _signup(client)
    # A quoted field may contain the delimiter itself; a comma inside a
    # semicolon-separated row is just data.
    body = (
        "folder;deck;front;back;note\n"
        'F;D;"front; with semicolon";back;note, with comma\n'
    )
    response = client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", body.encode(), "text/csv")},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"ok": True, "folders": 1, "decks": 1, "cards": 1}


def test_import_still_accepts_comma_delimiter(client):
    _signup(client)
    body = "folder,deck,front,back,note\nF,D,f,b,n\n"
    response = client.post(
        "/api/import/cards.csv",
        files={"file": ("cards.csv", body.encode(), "text/csv")},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"ok": True, "folders": 1, "decks": 1, "cards": 1}


def test_export_requires_a_selected_folder_or_deck(client):
    signup = client.post(
        "/api/signup",
        data={"email": "export@example.com", "password": "GoodPass123", "password2": "GoodPass123", "tz": "UTC"},
    )
    assert signup.status_code == 200, signup.text

    # Exporting "all" is fine, but a folder/deck scope needs a real id ("0" used
    # to slip through and return an empty file with a success status).
    assert client.post("/api/export/cards.csv", data={"scope": "folder", "folder_id": 0}).status_code == 400
    assert client.post("/api/export/cards.csv", data={"scope": "deck", "deck_id": 0}).status_code == 400
    assert client.post("/api/export/cards.csv", data={"scope": "all"}).status_code == 200
