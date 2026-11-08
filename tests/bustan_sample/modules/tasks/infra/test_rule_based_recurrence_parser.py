import asyncio

import pytest

from bustan_sample.modules.tasks.domain.errors import InvalidTaskError
from bustan_sample.modules.tasks.domain.recurrence import Frequency, RecurrenceRule
from bustan_sample.modules.tasks.infra.rule_based_recurrence_parser import (
    RuleBasedRecurrenceParser,
)

D, W, M, Y = Frequency.DAILY, Frequency.WEEKLY, Frequency.MONTHLY, Frequency.YEARLY


@pytest.mark.parametrize(
    ("phrase", "rule"),
    [
        ("daily", RecurrenceRule(D)),
        ("Weekly", RecurrenceRule(W)),
        ("fortnightly", RecurrenceRule(W, 2)),
        ("monthly", RecurrenceRule(M)),
        ("annually", RecurrenceRule(Y)),
        ("every day", RecurrenceRule(D)),
        ("every 3 days", RecurrenceRule(D, 3)),
        ("every other week", RecurrenceRule(W, 2)),
        ("  every   2 weeks on Monday ", RecurrenceRule(W, 2, weekday=0)),
        ("every week on fri", RecurrenceRule(W, weekday=4)),
        ("every Sunday", RecurrenceRule(W, weekday=6)),
        ("every 6 months", RecurrenceRule(M, 6)),
    ],
)
def test_a_known_phrase_gives_its_rule(phrase: str, rule: RecurrenceRule) -> None:
    assert asyncio.run(RuleBasedRecurrenceParser().parse(phrase)) == rule


@pytest.mark.parametrize(
    "phrase",
    [
        "sometimes",
        "every",
        "every 0 days",
        "every 2 months on Monday",
        "every week on someday",
        "each week",
    ],
)
def test_an_unknown_or_invalid_phrase_is_refused(phrase: str) -> None:
    with pytest.raises(InvalidTaskError):
        asyncio.run(RuleBasedRecurrenceParser().parse(phrase))
