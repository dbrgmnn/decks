from tests.conftest import signup_user


def test_login_page_renders_for_unauthenticated_user(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Decks" in response.text


def test_login_page_redirects_when_authenticated(auth_client):
    response = auth_client.get("/login", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["Location"] == "/"


def test_home_page_requires_authentication(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["Location"] == "/login"


def test_home_page_lists_all_decks(auth_client, make_deck, make_card):
    spanish = make_deck(name="Spanish")
    make_deck(name="German")
    make_card(deck_id=spanish, front="Hola", back="Hello", tags=["A1"])

    home_resp = auth_client.get("/")
    assert home_resp.status_code == 200
    assert "Spanish" in home_resp.text
    assert "German" in home_resp.text
    assert 'id="new-deck-sheet"' in home_resp.text
    assert 'data-tab="active"' in home_resp.text
    assert 'data-tab="all"' in home_resp.text
    assert 'id="tag-filter"' in home_resp.text


def test_home_page_shows_empty_state_without_decks(auth_client):
    response = auth_client.get("/")

    assert response.status_code == 200
    assert 'id="deck-empty"' in response.text
    assert 'data-tab="active"' not in response.text


def test_home_page_renders_paused_decks_for_the_all_tab(auth_client, make_deck):
    deck_id = make_deck(name="Paused")
    auth_client.post(f"/api/decks/{deck_id}/settings", data={"new_per_day": "10", "paused": 1})

    response = auth_client.get("/")

    assert 'data-name="Paused"' in response.text
    assert 'class="deck paused"' in response.text


def test_home_page_shows_a_token_confirmation_before_the_token_sheet(auth_client):
    response = auth_client.get("/", headers={"accept-language": "en"})

    assert response.status_code == 200
    assert "Generate a new API token?" in response.text
    assert response.text.index('id="token-confirm"') < response.text.index('id="token-sheet"')
