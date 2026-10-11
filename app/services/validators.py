from fastapi import HTTPException


RESERVED_QUICK_ADD_CHARS = ',/'


def clean(value, label, limit, required=True):
    value = '' if value is None else str(value)
    value = value.strip()
    if required and not value:
        raise HTTPException(400, f"{label} is required")
    if len(value) > limit:
        raise HTTPException(400, f"{label} is too long (max {limit})")
    return value


def clean_quick_add_name(value, label, limit):
    value = clean(value, label, limit)
    bad = [ch for ch in RESERVED_QUICK_ADD_CHARS if ch in value]
    if bad:
        raise HTTPException(400, f"{label} cannot contain / or ,")
    return value
