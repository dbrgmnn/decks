def signup(client, email="mobile@example.com", password="GoodPass123"):
    response = client.post(
        "/api/signup",
        data={"email": email, "password": password, "password2": password, "tz": "UTC"},
    )
    assert response.status_code == 200, response.text


def test_haptics_module_is_shipped(client):
    module = client.get("/static/modules/haptics.js")

    assert module.status_code == 200
    # Android path, plus the real-tap switch overlay for iOS.
    assert "navigator.vibrate" in module.text
    assert "input" in module.text
    assert "switch" in module.text
    assert "hapticTap" in module.text
    assert "decks.haptics" in module.text


def test_haptics_is_wired_into_the_app(client):
    assert "./modules/haptics.js" in client.get("/static/app.js").text
    assert "./haptics.js" in client.get("/static/modules/practice.js").text
    assert "./haptics.js" in client.get("/static/modules/decks.js").text


def test_rating_buttons_carry_a_tap_haptic(client):
    source = client.get("/static/modules/practice.js").text

    assert "hapticTap(button" in source
    assert ".rate button" in source


def test_touch_feedback_module_is_wired(client):
    module = client.get("/static/modules/touch.js")
    assert module.status_code == 200
    assert "touchstart" in module.text

    assert "./modules/touch.js" in client.get("/static/app.js").text
    assert "./modules/touch.js" in client.get("/static/login.js").text


def test_account_sheet_offers_a_vibration_toggle(client):
    signup(client)

    html = client.get("/").text
    assert 'id="haptics-toggle"' in html


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
    assert ".haptic-switch" in css
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


def test_rating_uses_graded_haptics(client):
    source = client.get("/static/modules/practice.js").text

    assert "RATE_HAPTIC" in source
    assert "1: 'warning'" in source
    assert "4: 'heavy'" in source
