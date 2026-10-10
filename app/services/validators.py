from fastapi import HTTPException


def clean(value, label, limit, required=True):
    value = '' if value is None else str(value)
    value = value.strip()
    if required and not value:
        raise HTTPException(400, f"{label} is required")
    if len(value) > limit:
        raise HTTPException(400, f"{label} is too long (max {limit})")
    return value
