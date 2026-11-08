from datetime import datetime

from bustan import Injectable

from .schedule_lock import ScheduleLock


@Injectable()
class InMemoryScheduleLock(ScheduleLock):
    """A lock for one process. It keeps the last claimed run time of each schedule.

    Processes do not share it. With the memory backend, each process also has
    its own data, thus a deployment has one process only.
    """

    def __init__(self) -> None:
        self._last: dict[str, datetime] = {}

    async def claim(self, name: str, run_at: datetime) -> bool:
        last = self._last.get(name)
        if last is not None and run_at <= last:
            return False
        self._last[name] = run_at
        return True
