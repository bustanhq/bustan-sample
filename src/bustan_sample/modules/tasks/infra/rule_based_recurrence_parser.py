import re

from bustan import Injectable

from ..domain.errors import InvalidTaskError
from ..domain.recurrence import WEEKDAY_NAMES, Frequency, RecurrenceRule
from ..domain.recurrence_parser import RecurrenceParser

_ALIASES = {
    "daily": "every day",
    "weekly": "every week",
    "fortnightly": "every 2 weeks",
    "monthly": "every month",
    "yearly": "every year",
    "annually": "every year",
}
_UNITS = {
    "day": Frequency.DAILY,
    "week": Frequency.WEEKLY,
    "month": Frequency.MONTHLY,
    "year": Frequency.YEARLY,
}
_WEEKDAYS = {name: index for index, name in enumerate(WEEKDAY_NAMES)} | {
    name[:3]: index for index, name in enumerate(WEEKDAY_NAMES)
}
_EVERY_UNIT = re.compile(
    r"^every (?:(?P<count>\d+|other) )?(?P<unit>day|week|month|year)s?"
    r"(?: on (?P<weekday>[a-z]+))?$"
)
_EVERY_WEEKDAY = re.compile(r"^every (?P<weekday>[a-z]+)$")
EXAMPLES = '"daily", "every 3 days", "every other week", "every 2 weeks on Monday", "every Friday"'


@Injectable()
class RuleBasedRecurrenceParser(RecurrenceParser):
    """Parses English repeat phrases with a small grammar. It needs no network.

    It knows the aliases daily, weekly, fortnightly, monthly, yearly and
    annually, and the forms "every [N | other] day|week|month|year[s]
    [on <weekday>]" and "every <weekday>". The case and the spaces have no
    effect. A model adapter can replace this adapter behind the same port to
    know more phrases.
    """

    async def parse(self, phrase: str) -> RecurrenceRule:
        text = " ".join(phrase.lower().split())
        text = _ALIASES.get(text, text)
        weekday_only = _EVERY_WEEKDAY.match(text)
        if weekday_only is not None and weekday_only["weekday"] in _WEEKDAYS:
            return RecurrenceRule(Frequency.WEEKLY, weekday=_WEEKDAYS[weekday_only["weekday"]])
        match = _EVERY_UNIT.match(text)
        if match is None:
            raise InvalidTaskError(
                f"the repeat phrase {phrase!r} is not known. Examples: {EXAMPLES}"
            )
        count = match["count"]
        interval = 2 if count == "other" else int(count) if count else 1
        weekday = None
        if match["weekday"] is not None:
            if match["weekday"] not in _WEEKDAYS:
                raise InvalidTaskError(f"{match['weekday']!r} is not a weekday")
            weekday = _WEEKDAYS[match["weekday"]]
        # RecurrenceRule refuses a weekday on a rule that is not weekly.
        return RecurrenceRule(_UNITS[match["unit"]], interval, weekday)
