import pytest

from bustan_sample.platform.jobs import (
    MAX_RETRY_DELAY_SECONDS,
    PermanentJobError,
    RetryJobLater,
    next_retry_delay,
)


@pytest.mark.parametrize(
    ("error", "attempt", "max_attempts", "base", "delay"),
    [
        (ConnectionError(), 1, 3, 1.0, 1.0),
        (ConnectionError(), 2, 3, 1.0, 2.0),
        (ConnectionError(), 3, 3, 1.0, None),
        (PermanentJobError(), 1, 3, 1.0, None),
        (RetryJobLater(10), 1, 3, 1.0, 10.0),
        (RetryJobLater(0.5), 3, 5, 1.0, 4.0),
        (RetryJobLater(10), 3, 3, 1.0, None),
        (RetryJobLater(99999), 1, 3, 1.0, MAX_RETRY_DELAY_SECONDS),
        (ConnectionError(), 5, 9, 300.0, MAX_RETRY_DELAY_SECONDS),
    ],
)
def test_next_retry_delay(
    error: Exception, attempt: int, max_attempts: int, base: float, delay: float | None
) -> None:
    assert next_retry_delay(error, attempt, max_attempts, base) == delay
