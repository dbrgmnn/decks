import pytest
from fastapi import HTTPException

from app.services.validators import clean, clean_deck_name, normalize_name_key


def test_clean_trims_and_validates_length():
    assert clean("  hello  ", "Label", 10) == "hello"


def test_clean_required_empty_raises():
    with pytest.raises(HTTPException) as exc:
        clean("", "Label", 10)
    assert exc.value.status_code == 400
    assert "required" in str(exc.value.detail).lower()


def test_clean_rejects_too_long():
    with pytest.raises(HTTPException) as exc:
        clean("x" * 11, "Label", 10)
    assert exc.value.status_code == 400
    assert "too long" in str(exc.value.detail).lower()


def test_clean_required_false_allows_empty():
    assert clean("", "Label", 10, required=False) == ""


def test_clean_accepts_exact_limit():
    assert clean("x" * 10, "Label", 10) == "x" * 10


def test_clean_deck_name_returns_valid_name():
    assert clean_deck_name("  Deck Name  ", "Deck name", 60) == "Deck Name"


def test_clean_deck_name_rejects_slash():
    with pytest.raises(HTTPException) as exc:
        clean_deck_name("a/b", "Deck name", 60)
    assert exc.value.status_code == 400
    assert "cannot contain" in str(exc.value.detail).lower()


def test_clean_deck_name_rejects_comma():
    with pytest.raises(HTTPException) as exc:
        clean_deck_name("a,b", "Deck name", 60)
    assert exc.value.status_code == 400


def test_normalize_name_key_casefolds_and_trims():
    assert normalize_name_key("  DeCk  ") == "deck"


def test_normalize_name_key_rejects_too_long():
    with pytest.raises(HTTPException):
        normalize_name_key("x" * 301)