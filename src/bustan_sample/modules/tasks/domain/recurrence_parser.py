from abc import ABC, abstractmethod

from .recurrence import RecurrenceRule


class RecurrenceParser(ABC):
    """The port that changes a repeat phrase, for example "every Friday", into a rule.

    The infra layer gives the adapter. The default adapter uses a small
    grammar. A model adapter, for example a language model behind an API, can
    replace it with no change to the domain or the application layer. The
    method is async, because a model adapter calls the network.
    """

    @abstractmethod
    async def parse(self, phrase: str) -> RecurrenceRule:
        """Return the rule. Raise InvalidTaskError if the phrase is not known."""
