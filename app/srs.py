from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fsrs import Scheduler, Card, Rating

_sched = Scheduler()

def review(state_json, rating):
    """rating 1..4 = Again/Hard/Good/Easy -> (new_state_json, due_iso)"""
    card = Card.from_json(state_json) if state_json else Card()
    card, _ = _sched.review_card(card, Rating(rating))
    return card.to_json(), card.due.astimezone(timezone.utc).isoformat()

def now():
    return datetime.now(timezone.utc).isoformat()

def day_start(tz):
    """Start of the user's current local day, as a UTC ISO string (comparable with stored timestamps)."""
    try:
        zone = ZoneInfo(tz or "UTC")
    except Exception:
        zone = timezone.utc
    local = datetime.now(zone).replace(hour=0, minute=0, second=0, microsecond=0)
    return local.astimezone(timezone.utc).isoformat()
