import queue
import threading
from collections.abc import Callable
from typing import Any

import logfire

from app.core.config import settings

Event = dict[str, Any]
Handler = Callable[[Event], None]

# Sentinel pushed onto the queue to unblock the worker(s) during shutdown.
_STOP = object()


class InMemoryBroker:
    """A tiny in-process publish/subscribe broker.

    The publisher drops an event on the queue and returns immediately. One or more
    background worker threads deliver each event to the registered subscriber, so
    slow work (scraping + LLM) runs off the request thread. Playwright's sync API
    needs a thread with no running asyncio loop, which these dedicated worker
    threads provide. Use ``workers > 1`` to process events concurrently.
    """

    def __init__(self, name: str = "broker", workers: int = 1) -> None:
        self.name = name
        self._workers = max(1, workers)
        self._queue: "queue.Queue[Any]" = queue.Queue()
        self._handler: Handler | None = None
        self._threads: list[threading.Thread] = []

    def subscribe(self, handler: Handler) -> None:
        self._handler = handler

    def publish(self, event: Event) -> None:
        self._queue.put(event)
        logfire.info("Event published", broker=self.name)

    def start(self) -> None:
        if self._threads and any(t.is_alive() for t in self._threads):
            return
        self._threads = []
        for i in range(self._workers):
            thread = threading.Thread(
                target=self._run, name=f"{self.name}-worker-{i}", daemon=True
            )
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        for _ in self._threads:
            self._queue.put(_STOP)
        for thread in self._threads:
            thread.join(timeout=5)

    def _run(self) -> None:
        while True:
            event = self._queue.get()
            try:
                if event is _STOP:
                    return
                if self._handler is None:
                    logfire.warn(
                        "No subscriber registered; event dropped", broker=self.name
                    )
                    continue
                self._handler(event)
            except Exception as exc:
                logfire.error(
                    "Subscriber failed to process event",
                    broker=self.name,
                    error=str(exc),
                )
            finally:
                self._queue.task_done()


# Stage B: receives an excel path, scrapes every Sales Specials URL, and fans out
# one scraped-data message per dealer to the extract broker. A single worker is
# enough because the scraping itself is parallelised inside the handler.
scrape_broker = InMemoryBroker(name="scrape", workers=1)

# Stage C: receives one dealer's scraped data, runs the LLM sequentially over that
# dealer's URLs. Multiple workers let different dealers run in parallel.
extract_broker = InMemoryBroker(
    name="extract", workers=settings.dealer_extract_workers
)

