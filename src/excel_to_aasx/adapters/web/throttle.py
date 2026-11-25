"""Per-session limits for diagram renders (ADR 0011).

The global slots alone let one client hold every slot. Each session gets one render in
flight, a gap between renders and a budget of render time per window. Opening more
sessions to get around this costs an upload each; per-IP limits belong to the proxy.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class _Session:
    busy: bool = False
    last_start: float = float("-inf")
    spent: list[tuple[float, float]] = field(default_factory=list)  # (end, seconds)


class SessionThrottle:
    def __init__(
        self,
        min_gap_seconds: float = 2.0,
        budget_seconds: float = 60.0,
        window_seconds: float = 600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._gap = min_gap_seconds
        self._budget = budget_seconds
        self._window = window_seconds
        self._clock = clock
        self._sessions: dict[str, _Session] = {}
        self._lock = threading.Lock()

    def start(self, session_id: str) -> str | None:
        """None when a render may start now (and it is then counted), else the reason."""
        now = self._clock()
        with self._lock:
            self._prune(now)
            session = self._sessions.setdefault(session_id, _Session())
            if session.busy:
                return "a diagram of this session is still rendering"
            if now - session.last_start < self._gap:
                return "wait a moment between diagrams"
            if sum(seconds for _, seconds in session.spent) >= self._budget:
                return "this session has used its diagram time; try again in a few minutes"
            session.busy, session.last_start = True, now
            return None

    def finish(self, session_id: str) -> None:
        now = self._clock()
        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None and session.busy:
                session.busy = False
                session.spent.append((now, now - session.last_start))

    def forget(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def _prune(self, now: float) -> None:
        for session_id, session in list(self._sessions.items()):
            session.spent = [(end, s) for end, s in session.spent if now - end < self._window]
            idle = now - session.last_start >= self._window
            if not session.busy and not session.spent and idle:
                del self._sessions[session_id]
