"""Global single-run lock.

Only one offer-generation run may be in flight at a time. The API acquires the
lock before publishing a scrape event and it is released when the run finishes
(all dealers extracted) or when scraping fails before any dealer is dispatched.

While a run is active, further requests are rejected immediately with the name of
the offer type that is currently running, so callers know to wait and retry
instead of interrupting or queueing behind the active run.
"""

from __future__ import annotations

import threading


class RunLock:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = False
        self._offer_type: str | None = None

    def acquire(self, offer_type: str) -> tuple[bool, str | None]:
        """Try to start a run. Returns ``(True, None)`` on success, or
        ``(False, <running_offer_type>)`` if a run is already active."""
        with self._lock:
            if self._active:
                return False, self._offer_type
            self._active = True
            self._offer_type = offer_type
            return True, None

    def release(self) -> None:
        with self._lock:
            self._active = False
            self._offer_type = None

    def current(self) -> str | None:
        """The offer type of the active run, or ``None`` if idle."""
        with self._lock:
            return self._offer_type if self._active else None


run_lock = RunLock()
