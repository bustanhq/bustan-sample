import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from .errors import InvalidTaskError

INTERVAL_MAX = 99
WEEKDAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


class Frequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


_UNITS = {
    Frequency.DAILY: "day",
    Frequency.WEEKLY: "week",
    Frequency.MONTHLY: "month",
    Frequency.YEARLY: "year",
}


@dataclass(frozen=True, slots=True)
class RecurrenceRule:
    """How often a task comes back. The rule is a value: it has no id.

    weekday (0 is Monday, 6 is Sunday) is only correct for a weekly rule.
    """

    frequency: Frequency
    interval: int = 1
    weekday: int | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.interval <= INTERVAL_MAX:
            raise InvalidTaskError(f"the interval must be 1 to {INTERVAL_MAX}")
        if self.weekday is None:
            return
        if self.frequency is not Frequency.WEEKLY:
            raise InvalidTaskError("only a weekly rule can have a weekday")
        if not 0 <= self.weekday <= 6:
            raise InvalidTaskError("the weekday must be 0 (Monday) to 6 (Sunday)")

    def describe(self) -> str:
        """Return the rule as a phrase, for example "every 2 weeks on Monday"."""
        unit = _UNITS[self.frequency]
        text = f"every {unit}" if self.interval == 1 else f"every {self.interval} {unit}s"
        if self.weekday is not None:
            text += f" on {WEEKDAY_NAMES[self.weekday].capitalize()}"
        return text


def next_due_on(rule: RecurrenceRule, after: date) -> date:
    """Return the next due date of a recurring task that was due on the date after.

    - Daily: interval days later.
    - Weekly with no weekday: interval weeks later.
    - Weekly with a weekday: the first such weekday after the date, plus
      interval - 1 weeks.
    - Monthly and yearly: the same day, interval months or years later. If
      that month has fewer days, the last day of the month. Thus a task due on
      31 January is due next on 28 or 29 February, and then on the 28th or
      29th of each month.

    The function is pure: it reads no clock and does no I/O.
    """
    if rule.frequency is Frequency.DAILY:
        return after + timedelta(days=rule.interval)
    if rule.frequency is Frequency.WEEKLY:
        if rule.weekday is None:
            return after + timedelta(weeks=rule.interval)
        days_ahead = (rule.weekday - after.weekday() - 1) % 7 + 1
        return after + timedelta(days=days_ahead, weeks=rule.interval - 1)
    if rule.frequency is Frequency.MONTHLY:
        return _add_months(after, rule.interval)
    return _add_months(after, 12 * rule.interval)


def _add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year, month = day.year + month_index // 12, month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))
