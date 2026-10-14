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