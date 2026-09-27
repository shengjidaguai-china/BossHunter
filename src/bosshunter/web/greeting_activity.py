"""Coordinate greeting snapshots and edits within the web worker process."""

from contextlib import contextmanager
from threading import Lock


class GreetingActivityRegistry:
    def __init__(self):
        self._lock = Lock()
        self._activities: dict[str, str] = {}

    def get(self, job_id: str) -> str | None:
        with self._lock:
            return self._activities.get(str(job_id))

    @contextmanager
    def claim(self, job_id: str, activity: str):
        """Reserve one job without holding a mutex across network calls."""
        job_id = str(job_id)
        with self._lock:
            acquired = job_id not in self._activities
            if acquired:
                self._activities[job_id] = activity
        try:
            yield acquired
        finally:
            if acquired:
                with self._lock:
                    del self._activities[job_id]
