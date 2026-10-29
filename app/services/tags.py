from ..i18n import error

MAX_TAGS = 10
MAX_TAG_LENGTH = 60
RESERVED_TAG_CHARS = ",;/"


def split_tags(value):
    """Turn a stored or submitted tag list into normalized tag strings.

    The database stores tags as a comma-separated string. Forms and CSV use the
    same separator; API clients may pass a list directly. Empty entries and
    case-insensitive duplicates are dropped.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        parts = value
    else:
        parts = str(value).replace(";", ",").split(",")

    tags = []
    seen = set()
    for part in parts:
        tag = str(part).strip()
        if not tag:
            continue
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        tags.append(tag)
    return tags


def parse_tags(value, line=None):
    """Validate tags submitted by a form, API client or CSV import."""
    tags = split_tags(value)
    suffix = "_line" if line is not None else ""
    for tag in tags:
        if any(char in tag for char in RESERVED_TAG_CHARS):
            raise error(400, f"error.tag_reserved{suffix}", tag=tag, line=line)
        if len(tag) > MAX_TAG_LENGTH:
            raise error(400, f"error.tag_too_long{suffix}", tag=tag, limit=MAX_TAG_LENGTH, line=line)
    if len(tags) > MAX_TAGS:
        raise error(400, "error.too_many_tags", limit=MAX_TAGS)
    return tags


def join_tags(tags):
    return ",".join(tags)


def tags_from_db(value):
    return split_tags(value)
