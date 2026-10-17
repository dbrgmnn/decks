import re

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
    assert ("192x192", "maskable") in sizes
    assert ("512x512", "maskable") in sizes


def test_manifest_icons_are_served(client):
    for icon in client.get(MANIFEST).json()["icons"]:
        response = client.get(icon["src"])
        assert response.status_code == 200, icon["src"]
        assert response.headers["content-type"] == "image/png"


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
    assert 'rel="apple-touch-startup-image"' in html


def test_splash_images_are_served(client):
    html = client.get("/login").text
    hrefs = re.findall(r'<link rel="apple-touch-startup-image" href="([^"]+)"', html)

    assert len(hrefs) >= 10
    for href in hrefs:
        response = client.get(href)
        assert response.status_code == 200, href
        assert response.headers["content-type"] == "image/png"


def test_splash_media_covers_modern_iphones(client):
    html = client.get("/login").text

    assert "device-width: 390px" in html  # iPhone 12/13/14
    assert "device-width: 393px" in html  # iPhone 15/16
    assert "device-width: 430px" in html  # iPhone 15/16 Plus


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
