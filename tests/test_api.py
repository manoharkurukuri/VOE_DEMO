import pytest
from fastapi.testclient import TestClient

import app.api.offers as offers_module
from app.events.run_lock import run_lock
from app.main import app


@pytest.fixture
def client(monkeypatch):
    # Don't trigger real scraping when an event is published.
    monkeypatch.setattr(offers_module.scrape_broker, "publish", lambda event: None)
    # Each test starts with an idle lock (publish is mocked so a run never
    # completes to release it on its own).
    run_lock.release()
    with TestClient(app) as test_client:
        yield test_client
    run_lock.release()


def test_list_types(client):
    resp = client.get("/api/v1/offers/types")
    assert resp.status_code == 200
    body = resp.json()
    assert body["default"] == "sales_specials"
    assert "used_inventory" in body["supported"]


def test_process_defaults_to_sales_specials(client):
    resp = client.post("/api/v1/offers/process", json={"path": "x.xlsx"})
    assert resp.status_code == 200
    assert resp.json()["offer_type"] == "sales_specials"


def test_process_explicit_type(client):
    resp = client.post(
        "/api/v1/offers/process",
        json={"type": "service_specials", "path": "x.xlsx"},
    )
    assert resp.status_code == 200
    assert resp.json()["offer_type"] == "service_specials"


def test_process_invalid_type_returns_error(client):
    resp = client.post(
        "/api/v1/offers/process", json={"type": "abc", "path": "x.xlsx"}
    )
    assert resp.status_code == 400
    message = resp.json()["error"]["message"]
    assert "abc" in message
    assert "sales_specials" in message


def test_second_request_while_running_is_rejected(client):
    first = client.post(
        "/api/v1/offers/process", json={"type": "sales_specials", "path": "x.xlsx"}
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/offers/process", json={"type": "service_specials", "path": "y.xlsx"}
    )
    assert second.status_code == 409
    body = second.json()["error"]
    assert body["code"] == "offer_run_in_progress"
    # The response names the offer type that is currently running.
    assert "sales_specials" in body["message"]


def test_lock_releases_after_run_completes(client, monkeypatch):
    # Simulate a run that completes (release the lock) between requests.
    first = client.post("/api/v1/offers/process", json={"type": "sales_specials"})
    assert first.status_code == 200
    run_lock.release()  # run finished

    second = client.post("/api/v1/offers/process", json={"type": "service_specials"})
    assert second.status_code == 200
    assert second.json()["offer_type"] == "service_specials"
