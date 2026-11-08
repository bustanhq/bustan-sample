from datetime import date
from uuid import UUID

import aiosqlite
from bustan import Injectable

from bustan_sample.platform.database import Database, Migration, from_text, to_text

from ..domain.recurrence import Frequency, RecurrenceRule
from ..domain.task import Task, TaskStatus
from ..domain.task_repository import TaskRepository

# Add a migration with the next version for each change. Never edit one.
_V1 = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    due_on TEXT,
    recurrence_frequency TEXT,
    recurrence_interval INTEGER,
    recurrence_weekday INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS tasks_by_owner ON tasks (owner_id, created_at);
"""
MIGRATIONS = (Migration(1, "create the table tasks", _V1),)
_COLUMNS = (
    "id, owner_id, title, description, status, due_on, recurrence_frequency, "
    "recurrence_interval, recurrence_weekday, created_at, updated_at"
)
_SAVE = f"""
INSERT INTO tasks ({_COLUMNS}) VALUES (
    :id, :owner_id, :title, :description, :status, :due_on, :recurrence_frequency,
    :recurrence_interval, :recurrence_weekday, :created_at, :updated_at
)
ON CONFLICT (id) DO UPDATE SET
    title = excluded.title,
    description = excluded.description,
    status = excluded.status,
    due_on = excluded.due_on,
    recurrence_frequency = excluded.recurrence_frequency,
    recurrence_interval = excluded.recurrence_interval,
    recurrence_weekday = excluded.recurrence_weekday,
    updated_at = excluded.updated_at
"""


@Injectable()
class SqliteTaskRepository(TaskRepository):
    """Keeps the tasks in the table tasks of the SQLite database.

    on_module_init makes the table if it does not exist. The sequence of
    creation is created_at, then the rowid, the same as the adapter in memory.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    async def on_module_init(self) -> None:
        await self._database.migrate("tasks", MIGRATIONS)

    async def save(self, task: Task) -> None:
        await self._database.execute(_SAVE, _to_row(task))

    async def get(self, owner_id: UUID, task_id: UUID) -> Task | None:
        row = await self._database.fetch_one(
            f"SELECT {_COLUMNS} FROM tasks WHERE id = ? AND owner_id = ?",
            (str(task_id), str(owner_id)),
        )
        return None if row is None else _to_task(row)

    async def find(
        self,
        owner_id: UUID,
        status: TaskStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        sql = f"SELECT {_COLUMNS} FROM tasks WHERE owner_id = ?"
        parameters: list[object] = [str(owner_id)]
        if status is not None:
            sql += " AND status = ?"
            parameters.append(status.value)
        # In SQLite, LIMIT -1 means no limit.
        sql += " ORDER BY created_at, rowid LIMIT ? OFFSET ?"
        parameters += [-1 if limit is None else limit, offset]
        rows = await self._database.fetch_all(sql, parameters)
        return [_to_task(row) for row in rows]

    async def remove(self, owner_id: UUID, task_id: UUID) -> bool:
        removed = await self._database.execute(
            "DELETE FROM tasks WHERE id = ? AND owner_id = ?",
            (str(task_id), str(owner_id)),
        )
        return removed > 0


def _to_row(task: Task) -> dict[str, object]:
    rule = task.recurrence
    return {
        "id": str(task.id),
        "owner_id": str(task.owner_id),
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "due_on": None if task.due_on is None else task.due_on.isoformat(),
        "recurrence_frequency": None if rule is None else rule.frequency.value,
        "recurrence_interval": None if rule is None else rule.interval,
        "recurrence_weekday": None if rule is None else rule.weekday,
        "created_at": to_text(task.created_at),
        "updated_at": to_text(task.updated_at),
    }


def _to_task(row: aiosqlite.Row) -> Task:
    recurrence = None
    if row["recurrence_frequency"] is not None:
        recurrence = RecurrenceRule(
            Frequency(row["recurrence_frequency"]),
            row["recurrence_interval"],
            row["recurrence_weekday"],
        )
    return Task(
        id=UUID(row["id"]),
        owner_id=UUID(row["owner_id"]),
        title=row["title"],
        description=row["description"],
        status=TaskStatus(row["status"]),
        due_on=None if row["due_on"] is None else date.fromisoformat(row["due_on"]),
        created_at=from_text(row["created_at"]),
        updated_at=from_text(row["updated_at"]),
        recurrence=recurrence,
    )
