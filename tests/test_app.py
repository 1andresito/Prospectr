import pytest

import app as app_module
from calculate import PlacesAPIError


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client


@pytest.fixture
def token():
    return app_module.APP_TOKEN


@pytest.fixture
def places_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "test-key")


# --- token guard ---------------------------------------------------------

def test_api_rejects_requests_without_a_token(client):
    response = client.get("/api/settings")
    assert response.status_code == 403


def test_api_rejects_a_wrong_token(client):
    response = client.get("/api/settings?token=not-the-token")
    assert response.status_code == 403


def test_api_accepts_the_token_as_a_query_parameter(client, token):
    assert client.get(f"/api/settings?token={token}").status_code == 200


def test_api_accepts_the_token_as_a_header(client, token):
    response = client.get("/api/settings", headers={"X-Prospectr-Token": token})
    assert response.status_code == 200


def test_state_changing_route_is_also_guarded(client):
    """A drive-by POST from another origin must not be able to stop the app."""
    assert client.post("/api/shutdown").status_code == 403
    assert client.post("/api/heartbeat").status_code == 403


def test_page_itself_does_not_require_a_token(client):
    assert client.get("/").status_code == 200


def test_page_embeds_the_token_for_the_frontend(client, token):
    body = client.get("/").get_data(as_text=True)
    assert token in body


# --- Google Places error surfacing ---------------------------------------

def test_places_failure_returns_json_not_an_html_error_page(
    client, token, places_key, monkeypatch
):
    def boom(_location):
        raise PlacesAPIError(403, "Location search failed (403): API key not valid")

    monkeypatch.setattr(app_module, "geocode_location", boom)

    response = client.get(f"/api/search?location=Denver&token={token}")

    assert response.status_code == 502
    assert response.is_json
    assert "API key not valid" in response.get_json()["error"]


def test_photo_failure_returns_json(client, token, places_key, monkeypatch):
    def boom(_name, **_kwargs):
        raise PlacesAPIError(429, "Photo request failed (429): quota exceeded")

    monkeypatch.setattr(app_module, "get_photo_uri", boom)

    response = client.get(f"/api/photo?name=places/x/photos/y&token={token}")

    assert response.status_code == 502
    assert "quota exceeded" in response.get_json()["error"]


def test_unresolvable_location_is_a_client_error(
    client, token, places_key, monkeypatch
):
    monkeypatch.setattr(app_module, "geocode_location", lambda _location: None)

    response = client.get(f"/api/search?location=nowhere&token={token}")

    assert response.status_code == 400
    assert "nowhere" in response.get_json()["error"]


def test_missing_location_is_rejected(client, token):
    response = client.get(f"/api/search?token={token}")

    assert response.status_code == 400
    assert "location" in response.get_json()["error"].lower()


def test_search_without_a_places_key_explains_itself(client, token, monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)

    response = client.get(f"/api/search?location=Denver&token={token}")

    assert response.status_code == 400
    assert "Settings" in response.get_json()["error"]
