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


def test_home_page_renders_pinned_decks_and_folders(auth_client, make_folder, make_deck, make_card):
    folder_id = make_folder("Languages")
    deck_id = make_deck(folder_id=folder_id, name="Spanish")
    make_card(deck_id=deck_id, front="Hola", back="Hello")

    # Pin deck
    auth_client.post(f"/api/decks/{deck_id}/pin", data={"pinned": 1})

    home_resp = auth_client.get("/")
    assert home_resp.status_code == 200
    assert "Languages" in home_resp.text
    assert "Spanish" in home_resp.text


def test_home_page_filtered_by_folder(auth_client, make_folder, make_deck):
    f1 = make_folder("Folder 1")
    f2 = make_folder("Folder 2")
    d1 = make_deck(folder_id=f1, name="Deck In Folder 1")
    d2 = make_deck(folder_id=f2, name="Deck In Folder 2")

    response = auth_client.get(f"/?folder={f1}")
    assert response.status_code == 200
    assert "Deck In Folder 1" in response.text


def test_home_page_shows_a_token_confirmation_before_the_token_sheet(auth_client):
    response = auth_client.get("/", headers={"accept-language": "en"})

    assert response.status_code == 200
    assert "Generate a new API token?" in response.text
    assert response.text.index('id="token-confirm"') < response.text.index('id="token-sheet"')
