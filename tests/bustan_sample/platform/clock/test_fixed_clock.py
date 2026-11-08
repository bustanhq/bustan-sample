from datetime import UTC, datetime, timedelta

from bustan_sample.platform.clock import FixedClock


def test_time_changes_only_on_advance() -> None:
    clock = FixedClock(datetime(2026, 3, 1, tzinfo=UTC))
    assert clock.now() == clock.now() == datetime(2026, 3, 1, tzinfo=UTC)
    clock.advance(timedelta(hours=2))
    assert clock.now() == datetime(2026, 3, 1, 2, tzinfo=UTC)
