from datetime import date

import pytest

from bustan_sample.modules.tasks.domain.errors import InvalidTaskError
from bustan_sample.modules.tasks.domain.recurrence import (
    Frequency,
    RecurrenceRule,
    next_due_on,
)

MONDAY = 0
FRIDAY = 4


@pytest.mark.parametrize(
    ("rule", "after", "expected"),
    [
        (RecurrenceRule(Frequency.DAILY), date(2026, 2, 27), date(2026, 2, 28)),
        (RecurrenceRule(Frequency.DAILY, 3), date(2026, 2, 27), date(2026, 3, 2)),
        (RecurrenceRule(Frequency.WEEKLY), date(2026, 2, 2), date(2026, 2, 9)),
        (RecurrenceRule(Frequency.WEEKLY, 2), date(2026, 2, 2), date(2026, 2, 16)),
        # 2026-02-02 is a Monday.
        (
            RecurrenceRule(Frequency.WEEKLY, weekday=MONDAY),
            date(2026, 2, 2),
            date(2026, 2, 9),
        ),
        (
            RecurrenceRule(Frequency.WEEKLY, weekday=FRIDAY),
            date(2026, 2, 2),
            date(2026, 2, 6),
        ),
        (
            RecurrenceRule(Frequency.WEEKLY, 2, weekday=MONDAY),
            date(2026, 2, 4),
            date(2026, 2, 16),
        ),
        (RecurrenceRule(Frequency.MONTHLY), date(2026, 1, 15), date(2026, 2, 15)),
        (RecurrenceRule(Frequency.MONTHLY), date(2026, 1, 31), date(2026, 2, 28)),
        (RecurrenceRule(Frequency.MONTHLY), date(2028, 1, 31), date(2028, 2, 29)),
        (RecurrenceRule(Frequency.MONTHLY, 3), date(2026, 11, 30), date(2027, 2, 28)),
        (RecurrenceRule(Frequency.YEARLY), date(2028, 2, 29), date(2029, 2, 28)),
        (RecurrenceRule(Frequency.YEARLY, 2), date(2026, 6, 1), date(2028, 6, 1)),
    ],
)
def test_next_due_on(rule: RecurrenceRule, after: date, expected: date) -> None:
    assert next_due_on(rule, after) == expected


@pytest.mark.parametrize(
    ("rule", "text"),
    [
        (RecurrenceRule(Frequency.DAILY), "every day"),
        (RecurrenceRule(Frequency.MONTHLY, 3), "every 3 months"),
        (
            RecurrenceRule(Frequency.WEEKLY, 2, weekday=MONDAY),
            "every 2 weeks on Monday",
        ),
    ],
)
def test_describe(rule: RecurrenceRule, text: str) -> None:
    assert rule.describe() == text


@pytest.mark.parametrize(
    ("frequency", "interval", "weekday"),
    [
        (Frequency.DAILY, 0, None),
        (Frequency.DAILY, 100, None),
        (Frequency.MONTHLY, 1, MONDAY),
        (Frequency.WEEKLY, 1, 7),
    ],
)
def test_an_invalid_rule_is_refused(
    frequency: Frequency, interval: int, weekday: int | None
) -> None:
    with pytest.raises(InvalidTaskError):
        RecurrenceRule(frequency, interval, weekday)
