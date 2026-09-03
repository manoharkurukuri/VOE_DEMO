"""Tests for the FastAPI app (app.main + app.api.offers)."""

import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import requires_gemini_key


def test_health_endpoint():
    # No lifespan (brokers not started) -> fast, no background work triggered.
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_generate_offers_returns_processing_contract(monkeypatch):
    published = []
    monkeypatch.setattr(
        "app.api.offers.scrape_broker.publish",
        lambda event: published.append(event),
    )

    client = TestClient(app)
    resp = client.get(
        "/api/v1/offers/generate", params={"excel_path": "some/path.xlsx"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "processing"
    assert body["excel_path"] == "some/path.xlsx"
    assert "message" in body
    # The endpoint published exactly one scrape event and returned immediately.
    assert published == [{"excel_path": "some/path.xlsx"}]


def test_generate_offers_uses_default_path(monkeypatch):
    published = []
    monkeypatch.setattr(
        "app.api.offers.scrape_broker.publish",
        lambda event: published.append(event),
    )
    client = TestClient(app)
    resp = client.get("/api/v1/offers/generate")
    assert resp.status_code == 200
    assert published and published[0]["excel_path"].endswith(".xlsx")


@pytest.mark.integration
@requires_gemini_key
def test_live_generate_endpoint_end_to_end(dealer_workbook, tmp_path, monkeypatch):
    """Drive the real lifespan (brokers + handlers) through the HTTP endpoint."""
    import app.events.subscriber as sub
    from app.service.offer_generation_service import OfferGenerationService

    out_dir = tmp_path / "out"
    monkeypatch.setattr(
        "app.service.offer_generation_service.settings.local_storage_dir",
        str(out_dir),
        raising=False,
    )
    monkeypatch.setattr(sub, "_service", OfferGenerationService())

    with TestClient(app) as client:  # runs lifespan: starts + subscribes brokers
        resp = client.get(
            "/api/v1/offers/generate",
            params={"excel_path": str(dealer_workbook)},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "processing"

        deadline = time.time() + 300
        while time.time() < deadline and not sub._run_tracker._finalized:
            time.sleep(1)
        assert sub._run_tracker._finalized

    assert out_dir.exists() and list(out_dir.iterdir())
