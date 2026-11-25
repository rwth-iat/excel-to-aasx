from excel_to_aasx.adapters.web.throttle import SessionThrottle


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _throttle(clock: Clock) -> SessionThrottle:
    return SessionThrottle(min_gap_seconds=2, budget_seconds=10, window_seconds=60, clock=clock)


def test_one_render_in_flight_and_a_gap_per_session():
    clock = Clock()
    throttle = _throttle(clock)
    assert throttle.start("a") is None
    assert "still rendering" in (throttle.start("a") or "")
    assert throttle.start("b") is None  # other sessions are not affected
    throttle.finish("a")
    assert "wait a moment" in (throttle.start("a") or "")
    clock.now += 2
    assert throttle.start("a") is None


def test_render_time_budget_per_window():
    clock = Clock()
    throttle = _throttle(clock)
    for _ in range(2):
        assert throttle.start("a") is None
        clock.now += 5
        throttle.finish("a")
    assert "used its diagram time" in (throttle.start("a") or "")
    clock.now += 60
    assert throttle.start("a") is None


def test_idle_and_closed_sessions_are_forgotten():
    clock = Clock()
    throttle = _throttle(clock)
    throttle.start("a")
    throttle.finish("a")
    throttle.start("b")
    throttle.forget("b")
    clock.now += 61
    throttle.start("c")
    assert set(throttle._sessions) == {"c"}
