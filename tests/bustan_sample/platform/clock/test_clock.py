from datetime import UTC

from bustan_sample.platform.clock import Clock


def test_now_is_in_utc() -> None:
    assert Clock().now().tzinfo is UTC
