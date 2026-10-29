import unicodedata

from ..i18n import error


RESERVED_DECK_CHARS = ',/'


def clean(value, label, limit, required=True, line=None):
    value = '' if value is None else str(value)
    value = value.strip()
    suffix = '_line' if line is not None else ''
    if required and not value:
        raise error(400, f"error.field_required{suffix}", field=label, line=line)
    if len(value) > limit:
        raise error(400, f"error.field_too_long{suffix}", field=label, limit=limit, line=line)
    return value


def clean_deck_name(value, label, limit, line=None):
    value = clean(value, label, limit, line=line)
    bad = [ch for ch in RESERVED_DECK_CHARS if ch in value]
    if bad:
        suffix = '_line' if line is not None else ''
        raise error(400, f'error.field_reserved{suffix}', field=label, line=line)
    return value


def normalize_name_key(value):
    return unicodedata.normalize('NFC', clean(value, 'field.name', 300)).casefold()
