"""Tests for the event subscribers (app.events.subscriber).

The _RunTracker timing logic is unit-tested. The full broker->subscriber wiring
(scrape -> extract -> files on disk) is an ``integration`` test using the live
page + Gemini.
"""

import time

import pytest

from app.events.subscriber import _RunTracker
from tests.conftest import requires_gemini_key


def test_run_tracker_finalizes_when_all_dealers_done():
    tracker = _RunTracker()
    tracker.start()
    tracker.set_expected(2)
    assert not tracker._finalized
    tracker.dealer_done()
    assert not tracker._finalized
    tracker.dealer_done()
    assert tracker._finalized


def test_run_tracker_handles_late_expected():
    # Dealers can complete before the expected count is known.
    tracker = _RunTracker()
    tracker.start()
    tracker.dealer_done()
    tracker.dealer_done()
    assert not tracker._finalized
    tracker.set_expected(2)
    assert tracker._finalized


def test_run_tracker_finalizes_only_once():
    tracker = _RunTracker()
    tracker.start()
    tracker.set_expected(1)
    tracker.dealer_done()
    assert tracker._finalized
    # Extra completions must not blow up or reset state.
    tracker.dealer_done()
    assert tracker._finalized


@pytest.mark.integration
@requires_gemini_key
def test_live_broker_pipeline_produces_output(dealer_workbook, tmp_path, monkeypatch):
    """Publish an excel event and let the real scrape/extract brokers run it."""
    import app.events.subscriber as sub
    from app.events.broker import InMemoryBroker
    from app.service.offer_generation_service import OfferGenerationService

    out_dir = tmp_path / "out"
    monkeypatch.setattr(sub, "_service", None)

    # Build a service bound to the temp storage dir and inject it.
    monkeypatch.setattr(
        "app.service.offer_generation_service.settings.local_storage_dir",
        str(out_dir),
        raising=False,
    )
    service = OfferGenerationService()
    monkeypatch.setattr(sub, "_service", service)

    # Fresh brokers so the test is isolated from the app's module-level ones.
    scrape_broker = InMemoryBroker(name="test-scrape", workers=1)
    extract_broker = InMemoryBroker(name="test-extract", workers=1)
    monkeypatch.setattr("app.events.broker.extract_broker", extract_broker)
    monkeypatch.setattr(sub, "extract_broker", extract_broker)

    scrape_broker.subscribe(sub.handle_scrape_event)
    extract_broker.subscribe(sub.handle_extract_event)
    scrape_broker.start()
    extract_broker.start()
    try:
        scrape_broker.publish({"excel_path": str(dealer_workbook)})

        # Wait (up to a few minutes) for the run tracker to finalize.
        deadline = time.time() + 300
        while time.time() < deadline and not sub._run_tracker._finalized:
            time.sleep(1)
        assert sub._run_tracker._finalized, "pipeline did not finish in time"
    finally:
        scrape_broker.stop()
        extract_broker.stop()

    # At least one output artifact (zip or error file) should exist.
    assert out_dir.exists()
    produced = list(out_dir.iterdir())
    assert produced, "no output files were produced"
