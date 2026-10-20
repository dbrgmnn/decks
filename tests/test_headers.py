import re


def test_docs_and_openapi_are_disabled(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_pages_send_csp_with_a_matching_nonce(client):
    response = client.get("/login")

    csp = response.headers["content-security-policy"]
    nonce = re.search(r"'nonce-([^']+)'", csp).group(1)
    assert f'nonce="{nonce}"' in response.text
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_security_headers_and_no_store_are_set(client):
    response = client.get("/login")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "same-origin"
    assert response.headers["cache-control"] == "no-store"


def test_static_assets_are_excluded_from_csp(client):
    response = client.get("/static/app.js")

    assert "content-security-policy" not in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"


def test_pages_version_internal_es_module_imports(client):
    # Modules import each other with bare ./foo.js specifiers. The import map
    # gives those URLs the same ?v= cache-buster as the entry script.
    html = client.get("/login").text

    assert 'type="importmap"' in html
    assert '"/static/modules/i18n.js": "/static/modules/i18n.js?v=' in html


def test_static_assets_must_be_revalidated(client):
    # Entry points use ?v=mtime, but their internal ES-module imports do not.
    # Without this header browsers (especially mobile Safari) may keep an old
    # module and its old UI for hours.
    response = client.get("/static/modules/account.js")

    assert response.headers["cache-control"] == "no-cache"
