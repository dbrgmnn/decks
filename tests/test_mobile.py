import re


def signup(client, email="mobile@example.com", password="GoodPass123"):
    response = client.post(
        "/api/signup",
        data={"email": email, "password": password, "password2": password, "tz": "UTC"},
    )
    assert response.status_code == 200, response.text


def test_touch_feedback_module_is_wired(client):
    module = client.get("/static/modules/touch.js")
    assert module.status_code == 200
    assert "touchstart" in module.text

    assert "./modules/touch.js" in client.get("/static/app.js").text
    assert "./modules/touch.js" in client.get("/static/login.js").text


def test_haptics_are_gone(client):
    assert client.get("/static/modules/haptics.js").status_code == 404

    for script in ("/static/app.js", "/static/login.js"):
        assert "haptics" not in client.get(script).text
    for module in ("/static/modules/practice.js", "/static/modules/decks.js", "/static/modules/folders.js", "/static/modules/theme.js"):
        assert "haptic" not in client.get(module).text

    css = client.get("/static/style.css").text
    assert "haptic" not in css


def test_account_sheet_has_no_vibration_toggle(client):
    signup(client)

    assert "haptics-toggle" not in client.get("/").text


def test_stylesheet_presses_buttons_instantly(client):
    css = client.get("/static/style.css").text

    # The bevel/transform swap must not be animated, or a quick tap looks dead.
    assert "button{transition:background-color .12s linear,color .12s linear}" in css
    assert "transform .12s linear" not in css
    assert "box-shadow .12s linear" not in css


def test_stylesheet_blocks_white_flash_and_text_selection(client):
    css = client.get("/static/style.css").text

    assert "html{-webkit-text-size-adjust:100%;overscroll-behavior:none;background:var(--bg)" in css
    assert "touch-action:manipulation" in css
    assert "#words li:active" in css


def test_inputs_carry_native_keyboard_hints(client):
    signup(client)

    html = client.get("/").text
    assert 'enterkeyhint="search"' in html
    assert 'enterkeyhint="done"' in html
    assert 'autocorrect="off"' in html


def test_import_refreshes_home_and_shows_progress(client):
    source = client.get("/static/modules/account.js").text

    # A successful import must refresh the folder/deck lists, not just print a sum.
    assert "location.reload()" in source
    assert "Importing…" in source
    assert "classList.add('busy')" in source

    css = client.get("/static/style.css").text
    assert ".busy::after" in css
    assert "@keyframes busy" in css


def learn_button_attrs(html, deck_id):
    match = re.search(rf'<button class="learn" type="button" data-id="{deck_id}"([^>]*)>', html)
    assert match, f"no Study button rendered for deck {deck_id}"
    return match.group(1)


def test_deck_study_button_greys_out_when_nothing_to_study(client):
    signup(client, email="study@example.com")

    empty = client.post("/api/quick-add", data={"text": "Folder/Empty"}).json()
    full = client.post("/api/quick-add", data={"text": "Folder/Full/Front/Back"}).json()
    folder_id = empty["folder"]["id"]

    html = client.get(f"/?folder={folder_id}").text

    assert "disabled" in learn_button_attrs(html, empty["deck"]["id"])
    assert "disabled" not in learn_button_attrs(html, full["deck"]["id"])


def test_finished_session_shows_a_summary(client):
    signup(client, email="summary@example.com")

    assert 'id="summary"' in client.get("/").text

    source = client.get("/static/modules/practice.js").text
    assert "renderSummary" in source
    assert "formatDuration" in source

    css = client.get("/static/style.css").text
    assert ".summary-grid" in css
    assert ".summary-bars" in css
