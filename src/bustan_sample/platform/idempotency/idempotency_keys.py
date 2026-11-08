from abc import ABC, abstractmethod


class IdempotencyKeys(ABC):
    """The port that remembers the keys of work that must happen one time.

    A job or an event delivery can run more than one time. A key names one
    piece of work, for example "tasks.starter_task:<user id>". Start each key
    with the name of the module, thus two modules never use the same key.

    Work in the database: in Database.transaction(), add() the key, and do the
    work only if add() returns True. The key and the work commit together, or
    neither. Thus the work happens exactly one time. If the work fails, the
    key rolls back with it, and a retry can do the work.

    Work outside the database, for example an email: if contains() returns
    True, stop. Do the work, then add() the key. If the process stops between
    the work and add(), a retry does the work again. Thus the work happens at
    least one time, and two times only in that case. Do not keep a transaction
    open during a network call: the transaction keeps the database lock.
    """

    @abstractmethod
    async def add(self, key: str) -> bool:
        """Record the key and return True. If the key is recorded, return False.

        In a transaction, the key commits or rolls back with the transaction.
        """

    @abstractmethod
    async def contains(self, key: str) -> bool:
        """Return True if the key is recorded."""
