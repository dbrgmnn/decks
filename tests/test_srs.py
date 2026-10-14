import json
from datetime import datetime

import pytest
from fastapi import HTTPException

from app import srs


def test_review_returns_state_and_due_for_all_ratings():
    for rating in (1, 2, 3, 4):
        state_json, due = srs.review(None, rating)
        assert isinstance(state_json, str)
        json.loads(state_json)
        assert "T" in due
        datetime.fromisoformat(due.replace("Z", "+00:00"))


def test_review_accepts_existing_state():
    first_state, _ = srs.review(None, 3)
    second_state, _ = srs.review(first_state, 4)
    assert first_state != second_state


def test_review_rejects_invalid_rating():
    with pytest.raises((ValueError, HTTPException)):
        srs.review(None, 0)


def test_now_returns_parseable_utc_timestamp():
    now = srs.now()
    assert "T" in now
    datetime.fromisoformat(now.replace("Z", "+00:00"))


def test_day_start_returns_parseable_timestamp():
    for tz in ("UTC", "Europe/Berlin", "not/a-zone"):
        value = srs.day_start(tz)
        assert "T" in value
        datetime.fromisoformat(value.replace("Z", "+00:00"))