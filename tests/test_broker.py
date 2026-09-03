"""Unit tests for the in-memory pub/sub broker (app.events.broker)."""

import threading
import time

from app.events.broker import InMemoryBroker


def _wait_for(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def test_publish_delivers_event_to_subscriber():
    broker = InMemoryBroker(name="t")
    received = []
    done = threading.Event()

    def handler(event):
        received.append(event)
        done.set()

    broker.subscribe(handler)
    broker.start()
    try:
        broker.publish({"n": 1})
        assert done.wait(timeout=5)
        assert received == [{"n": 1}]
    finally:
        broker.stop()


def test_publish_delivers_multiple_events_in_order():
    broker = InMemoryBroker(name="t", workers=1)
    received = []
    latch = threading.Event()

    def handler(event):
        received.append(event["n"])
        if event["n"] == 3:
            latch.set()

    broker.subscribe(handler)
    broker.start()
    try:
        for n in (1, 2, 3):
            broker.publish({"n": n})
        assert latch.wait(timeout=5)
        assert received == [1, 2, 3]
    finally:
        broker.stop()


def test_start_is_idempotent():
    broker = InMemoryBroker(name="t")
    broker.subscribe(lambda e: None)
    broker.start()
    try:
        first = list(broker._threads)
        broker.start()  # second call must not spawn new threads
        assert broker._threads == first
    finally:
        broker.stop()


def test_stop_joins_workers():
    broker = InMemoryBroker(name="t", workers=2)
    broker.subscribe(lambda e: None)
    broker.start()
    threads = list(broker._threads)
    broker.stop()
    assert _wait_for(lambda: all(not t.is_alive() for t in threads))


def test_handler_exception_is_swallowed_and_processing_continues():
    broker = InMemoryBroker(name="t")
    processed = []
    second = threading.Event()

    def handler(event):
        if event["n"] == 1:
            raise ValueError("boom")
        processed.append(event["n"])
        second.set()

    broker.subscribe(handler)
    broker.start()
    try:
        broker.publish({"n": 1})  # raises inside worker
        broker.publish({"n": 2})  # must still be processed
        assert second.wait(timeout=5)
        assert processed == [2]
    finally:
        broker.stop()


def test_no_subscriber_does_not_crash_worker(caplog):
    broker = InMemoryBroker(name="nosub")
    broker.start()
    try:
        broker.publish({"n": 1})
        # Give the worker a moment to consume the event.
        time.sleep(0.2)
    finally:
        broker.stop()
    # Worker survived and the queue drained without a subscriber.
    assert broker._queue.empty()
