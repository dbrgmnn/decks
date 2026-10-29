from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from .. import auth, db
from ..i18n import error
from ..services.cards import find_duplicate
from ..services.decks import get_or_create_deck
from ..services.ownership import own_card, own_deck
from ..services.tags import join_tags, parse_tags, tags_from_db
from ..services.validators import clean, clean_deck_name

router = APIRouter()


class CardCreate(BaseModel):
    deck: str | None = None
    deck_id: int | None = None
    front: str
    back: str
    note: str = ''
    # A list or a comma/semicolon separated string, so quick commands can send
    # tags without building a JSON array.
    tags: list[str] | str = Field(default_factory=list)


class CardUpdate(BaseModel):
    front: str
    back: str
    note: str = ''
    tags: list[str] | str = Field(default_factory=list)


def _card_json(card_id, front, back, note, tags, created):
    return {
        'id': card_id,
        'front': front,
        'back': back,
        'note': note,
        'tags': tags,
        'created': created,
    }


@router.post('/api/cards')
def create_card(
    payload: CardCreate,
    response: Response,
    user=Depends(auth.current_user_or_token),
):
    if (payload.deck is None) == (payload.deck_id is None):
        raise error(400, 'error.deck_choice')

    front = clean(payload.front, 'field.front', 200)
    back = clean(payload.back, 'field.back', 200)
    note = clean(payload.note, 'field.note', 300, required=False)
    tags = parse_tags(payload.tags)
    uid = user['id']

    with db.conn() as c:
        if payload.deck_id is not None:
            deck_row = own_deck(c, uid, payload.deck_id)
            deck = {'id': deck_row['id'], 'name': deck_row['name'], 'created': False}
        else:
            deck_name = clean_deck_name(payload.deck, 'field.deck_name', 60)
            deck = get_or_create_deck(c, uid, deck_name)

        existing = find_duplicate(c, deck['id'], front, back)
        if existing:
            response.status_code = 200
            return {
                'deck': deck,
                'card': _card_json(
                    existing['id'],
                    existing['front'],
                    existing['back'],
                    existing['note'],
                    tags_from_db(existing['tags']),
                    False,
                ),
            }

        card_id = c.execute(
            'INSERT INTO cards(deck_id, front, back, note, tags) VALUES(?,?,?,?,?)',
            (deck['id'], front, back, note, join_tags(tags)),
        ).lastrowid

    response.status_code = 201
    return {
        'deck': deck,
        'card': _card_json(card_id, front, back, note, tags, True),
    }


@router.put('/api/cards/{card_id}')
def update_card(
    card_id: int,
    payload: CardUpdate,
    user=Depends(auth.current_user),
):
    front = clean(payload.front, 'field.front', 200)
    back = clean(payload.back, 'field.back', 200)
    note = clean(payload.note, 'field.note', 300, required=False)
    tags = parse_tags(payload.tags)
    uid = user['id']

    with db.conn() as c:
        row = own_card(c, uid, card_id)
        # Duplicate detection stays scoped to the card's current deck.
        existing = find_duplicate(c, row['deck_id'], front, back, exclude_id=card_id)
        if existing:
            raise error(400, 'error.card_exists')
        c.execute(
            'UPDATE cards SET front=?, back=?, note=?, tags=? WHERE id=?',
            (front, back, note, join_tags(tags), card_id),
        )

    return {
        'ok': True,
        'card': {
            'id': card_id,
            'front': front,
            'back': back,
            'note': note,
            'tags': tags,
        },
    }


@router.delete('/api/cards/{card_id}')
def delete_card(card_id: int, user=Depends(auth.current_user)):
    uid = user['id']
    with db.conn() as c:
        own_card(c, uid, card_id)
        c.execute('DELETE FROM cards WHERE id=?', (card_id,))
    return {'ok': True}
