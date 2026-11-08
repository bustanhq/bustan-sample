from abc import ABC, abstractmethod
from datetime import datetime


class ScheduleLock(ABC):
    """The port that lets only one process enqueue each run of a schedule.

    Each process that runs the scheduler computes the same run time for a
    cron expression. The first process that claims a run time enqueues the
    job, and the other processes do not.
    """

    @abstractmethod
    async def claim(self, name: str, run_at: datetime) -> bool:
        """Return True for the first claim of this run, and False for each other claim."""
