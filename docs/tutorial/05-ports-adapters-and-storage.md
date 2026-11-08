# 5. Ports, adapters and storage

## What you learn

- How two adapters implement one port, and how the configuration selects one.
- How the SQLite backend works: one connection, a lock, WAL mode.
- How a transaction makes the writes of one use case one unit of work.
- How versioned migrations change a table safely.
- How a contract test keeps two adapters in agreement.

## Concepts

### Two adapters for each storage port

Each storage port has two adapters in `infra/`:

| Port | Memory adapter | SQLite adapter |
|---|---|---|
| `TaskRepository` | `InMemoryTaskRepository` | `SqliteTaskRepository` |
| `UserRepository` | `InMemoryUserRepository` | `SqliteUserRepository` |
| `RevokedTokenRepository` | `InMemoryRevokedTokenRepository` | `SqliteRevokedTokenRepository` |
| `JobQueue` (platform) | `InMemoryJobQueue` | `SqliteJobQueue` |
| `IdempotencyKeys` (platform) | `InMemoryIdempotencyKeys` | `SqliteIdempotencyKeys` |

The memory adapters need no setup and lose their data on a restart. The SQLite
adapters keep the data, and several processes on one host can share the file.

### Selection with a factory

`DATABASE_BACKEND` is `memory` or `sqlite`. The module binds the port with a
`FactoryProvider`, a function that bustan calls to make the value:

```python
def _task_repository(database: Database) -> TaskRepository:
    if database.is_sqlite:
        return SqliteTaskRepository(database)
    return InMemoryTaskRepository()


FactoryProvider(provide=TaskRepository, use_factory=_task_repository, inject=(Database,))
```

The factory makes only the selected adapter, and bustan still runs the hooks
of that adapter. The handlers ask for `TaskRepository` and never know which
one they get.

### The database

`platform/database/database.py` holds one aiosqlite connection for each
process:

- **One connection and a lock.** Each statement or transaction gets the
  connection for itself, so the statements of two requests never mix in one
  transaction.
- **WAL mode.** Readers continue while a writer writes. A busy timeout of
  5 s makes a writer wait for the file lock of a different process.
- **`transaction()`** starts with `BEGIN IMMEDIATE`, which takes the write
  lock at once, and rolls back if the block raises an error.
- **Time as text.** `to_text()` writes each time as UTC text with the same
  length, so the text order of a column is the time order.

### One unit of work

A use case often writes more than one row: a task and its next task, or a
user and the event that tells the other modules. These writes must commit
together, or not at all. `transaction()` makes the block one unit of work:

```python
async with self._database.transaction():
    task = await self._repository.get(command.owner_id, command.task_id)
    ...
    await self._repository.save(task)
    await self._repository.save(next_task)
```

The repositories do not get a connection or a session as an argument. Each
statement of the same asyncio task joins the open transaction: the database
keeps the transaction in a context variable of the task. A nested
`transaction()` joins the outer one. A different task, for example a job
worker, waits for the lock until the transaction ends.

Two callbacks let a component act on the result:

- `after_commit(callback)` runs the callback after the commit, or
  immediately outside a transaction. The job queue uses it to wake its
  workers, and the memory event bus to start the listeners.
- `after_rollback(callback)` runs the callback after a rollback. The memory
  adapter of the idempotency keys uses it to remove a key again.

Keep the block short. It keeps the one connection of the process, so do the
slow work before the block: `RegisterUserHandler` hashes the password first,
and `UpdateTaskHandler` parses the repeat phrase first.

The memory backend has no rollback. With it, `transaction()` only defers the
events and the jobs of the block until the end of the block, and drops them
if the block raises an error. Use SQLite when a test must prove a rollback.

### Versioned migrations

An SQLite adapter declares its schema as a list of migrations:

```python
MIGRATIONS = (Migration(1, "create the table tasks", _V1),)
```

In `on_module_init`, it calls `database.migrate("tasks", MIGRATIONS)`. The
table `schema_migrations` records each applied version, and `migrate()`
applies only the missing ones. Each migration and its record commit in one
transaction. The record goes in first: if two processes start at the same
time, the second one waits for the lock, hits the primary key, and does not
apply the migration again.

The rule: **never change a migration after a release**. To change a table,
add a migration with the next version.

### Contract tests

Two adapters of one port must behave the same, or the backend switch is a
lie. `tests/bustan_sample/modules/tasks/domain/test_task_repository.py` is a
**contract test**: each test in it runs on both adapters
(`pytestmark = pytest.mark.parametrize("backend", BACKENDS)`). If the SQLite
adapter sorts differently from the memory adapter, a test fails.

## Try it

1. Switch to SQLite. In `.env`, set:

   ```bash
   DATABASE_BACKEND=sqlite
   DATABASE_SQLITE_PATH=var/bustan-sample.db
   ```

2. Start the server, register, add a task, stop the server, start it again,
   and list your tasks. The task is still there.

3. Look into the file:

   ```bash
   sqlite3 var/bustan-sample.db '.tables'
   sqlite3 var/bustan-sample.db 'SELECT component, version, name FROM schema_migrations'
   ```

4. Write a migration. Add a `priority` column to the tasks: add
   `Migration(2, "add the column priority", "ALTER TABLE tasks ADD COLUMN priority INTEGER;")`
   to `MIGRATIONS` in `infra/sqlite_task_repository.py`, start the server, and
   read `schema_migrations` again. Then undo it (`git checkout -- src`) and
   delete `var/` before the next chapter.

5. Run the contract tests and read their ids: each one ends with `[memory]` or
   `[sqlite]`.

   ```bash
   uv run pytest -v tests/bustan_sample/modules/tasks/domain/test_task_repository.py
   ```

## Why it is built this way

- **Memory as the default.** A new developer runs the service with no setup,
  and the tests are fast. SQLite is one setting away.
- **aiosqlite with plain SQL, no ORM.** The SQL of each adapter is short and in
  one file, and you can read exactly what runs. The cost: each adapter maps
  rows to entities by hand.
- **One connection per process.** It is simple and correct. It also puts all
  statements of a process in one line, which is enough for this service and
  not for a heavy load. For more hosts or more load, the same ports can take a
  PostgreSQL adapter.
- **A context variable, not a session argument.** The repositories join the
  transaction of their task with no change to their signatures. The port
  stays free of database types, and the memory adapters ignore the
  transaction. The cost: a block must not wait for a different task that
  uses the database, or the two tasks wait for each other.
- **The owner id in each read.** `get(owner_id, task_id)` and
  `find(owner_id, ...)` make it impossible to read the task of a different
  user by mistake.

## Check yourself

1. A handler asks for `TaskRepository`. What decides which class it gets?
2. Why does the record of a migration go in before the migration itself?
3. What does a contract test protect that a test of one adapter cannot?
4. Why does `RegisterUserHandler` hash the password before the transaction?

Next: [6. Identity and security](06-identity-and-security.md).
