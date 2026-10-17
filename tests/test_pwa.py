import struct

MANIFEST = "/static/icons/site.webmanifest"


def signup(client, email="pwa@example.com", password="GoodPass123"):
    response = client.post(
        "/api/signup",
        data={"email": email, "password": password, "password2": password, "tz": "UTC"},
    )
    assert response.status_code == 200, response.text


def test_manifest_is_installable(client):
    manifest = client.get(MANIFEST).json()

    assert manifest["id"] == "/"
    assert manifest["start_url"] == "/"
    assert manifest["scope"] == "/"
    assert manifest["display"] == "standalone"
    assert manifest["orientation"] == "portrait"
    assert manifest["theme_color"] == "#f4f4f0"
    assert manifest["background_color"] == "#f4f4f0"
    assert manifest["lang"] == "en"
    assert "standalone" in manifest["display_override"]

    sizes = {(icon["sizes"], icon["purpose"]) for icon in manifest["icons"]}
    assert ("192x192", "any") in sizes
    assert ("512x512", "any") in sizes
    assert ("512x512", "maskable") in sizes


def test_manifest_icons_are_served(client):
    for icon in client.get(MANIFEST).json()["icons"]:
        response = client.get(icon["src"])
        assert response.status_code == 200, icon["src"]
        assert response.headers["content-type"] == "image/png"


def test_icons_match_their_declared_size(client):
    """A wrong pixel size is silent on the server and fatal in the browser: Chrome refuses to
    install a manifest whose 192/512 entries are not really 192 and 512."""
    for icon in client.get(MANIFEST).json()["icons"]:
        width, height = struct.unpack(">II", client.get(icon["src"]).content[16:24])  # PNG IHDR
        side = int(icon["sizes"].split("x")[0])
        assert (width, height) == (side, side), icon["src"]

    touch = client.get("/static/icons/apple-touch-icon.png").content
    assert struct.unpack(">II", touch[16:24]) == (180, 180)


def test_favicon_ico_holds_all_three_sizes(client):
    """Not a renamed PNG: real 16, 32 and 48 entries, so the tab and the bookmarks list both work."""
    raw = client.get("/static/icons/favicon.ico").content
    reserved, kind, count = struct.unpack("<HHH", raw[:6])

    assert (reserved, kind) == (0, 1)
    assert {raw[6 + i * 16] for i in range(count)} == {16, 32, 48}


def test_login_page_declares_ios_install_metadata(client):
    html = client.get("/login").text

    for name in (
        "mobile-web-app-capable",
        "apple-mobile-web-app-capable",
        "apple-mobile-web-app-status-bar-style",
        "apple-mobile-web-app-title",
        "theme-color",
        "color-scheme",
        "format-detection",
    ):
        assert f'name="{name}"' in html, name

    assert 'rel="manifest"' in html
    assert 'rel="apple-touch-icon"' in html


def test_home_page_declares_ios_install_metadata(client):
    signup(client)
    html = client.get("/").text

    assert 'name="apple-mobile-web-app-status-bar-style"' in html
    assert 'name="theme-color"' in html


def test_icons_are_the_minimal_set(client):
    html = client.get("/login").text

    # No per-device splash artwork: a short blank launch beats 250 KB of PNGs that have to be
    # redrawn by hand every time the icon changes.
    assert "apple-touch-startup-image" not in html
    assert html.count('rel="apple-touch-icon"') == 1

    favicon = client.get("/static/icons/favicon.svg")
    assert favicon.status_code == 200
    assert "image/svg+xml" in favicon.headers["content-type"]
    # The tab icon follows the system theme.
    assert "prefers-color-scheme" in favicon.text

    # Legacy fallback, checked in detail by test_favicon_ico_holds_all_three_sizes.
    assert client.get("/static/icons/favicon.ico").status_code == 200


def test_stylesheet_tames_ios_scroll_and_taps(client):
    css = client.get("/static/style.css").text

    assert "overscroll-behavior:none" in css
    assert "touch-action:manipulation" in css
    assert "html.typing .study-bar{display:none}" in css


def test_app_bundle_loads_keyboard_module(client):
    assert "./modules/keyboard.js" in client.get("/static/app.js").text

    module = client.get("/static/modules/keyboard.js")
    assert module.status_code == 200
    # The bar is hidden only while an on-screen keyboard actually shrinks the
    # viewport, never just because a field has focus - on a desktop that would
    # make the Study button vanish for no reason.
    assert "visualViewport" in module.text
    assert "focusin" not in module.text


def test_service_worker_is_served_from_root(client):
    response = client.get("/sw.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "addEventListener" in response.text


def test_service_worker_only_caches_static_assets(client):
    source = client.get("/sw.js").text

    # Cache Storage is used for /static/* only; navigations just fall back to
    # the offline page and API answers are never touched.
    assert "url.pathname.startsWith('/static/')" in source
    assert "request.mode === 'navigate'" in source
    assert "cache.put" in source
    assert "/api" not in source


def test_offline_page_and_stylesheet_are_shipped(client):
    page = client.get("/static/offline.html")
    assert page.status_code == 200
    assert "offline" in page.text
    assert client.get("/static/offline.css").status_code == 200

    source = client.get("/sw.js").text
    assert "'/static/offline.html'" in source
    assert "'/static/offline.css'" in source


def test_both_pages_register_the_service_worker(client):
    assert "./modules/pwa.js" in client.get("/static/app.js").text
    assert "./modules/pwa.js" in client.get("/static/login.js").text

    module = client.get("/static/modules/pwa.js")
    assert module.status_code == 200
    assert "isSecureContext" in module.text
