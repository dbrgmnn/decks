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
