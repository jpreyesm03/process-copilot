"""Usage limits for a public demo: questions per client per hour and per day overall, so nobody can drain the key."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class UsageLimiter:
    def __init__(self, per_client_per_hour: int = 20, per_day: int = 300, clock=time.monotonic):
        self.per_client_per_hour = per_client_per_hour
        self.per_day = per_day
        self.clock = clock
        self._client: dict[str, deque[float]] = defaultdict(deque)
        self._all: deque[float] = deque()
        self._lock = threading.Lock()

    def check(self, client: str) -> str | None:
        """Record one question for `client`, or return why it is refused (nothing is recorded then)."""
        now = self.clock()
        with self._lock:
            mine = self._client[client]
            while mine and now - mine[0] >= 3600:
                mine.popleft()
            while self._all and now - self._all[0] >= 86400:
                self._all.popleft()
            if len(self._all) >= self.per_day:
                return f"The demo's daily limit of {self.per_day} questions is reached. Please try again tomorrow."
            if len(mine) >= self.per_client_per_hour:
                return f"Limit of {self.per_client_per_hour} questions per hour reached. Please try again later."
            mine.append(now)
            self._all.append(now)
            return None
