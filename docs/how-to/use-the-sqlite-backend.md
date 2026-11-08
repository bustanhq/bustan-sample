# Use the SQLite backend

1. Set the backend in `.env`, or in the environment:

   ```bash
   DATABASE_BACKEND=sqlite
   DATABASE_SQLITE_PATH=var/bustan-sample.db
   ```

   A relative path starts at the folder in which the process starts. Git
   ignores `var/` and `*.db`.

2. Start the server:

   ```bash
   uv run bustan-sample-serve
   ```

   At startup, each SQLite adapter applies its missing migrations. The table
   `schema_migrations` records each applied version.

## What goes to SQLite

| Data | Table |
|---|---|
| Tasks | `tasks` |
| Users | `users` |
| Revoked token ids | `revoked_tokens` |
| Jobs and event deliveries (the outbox) | `jobs` |
| Claimed schedule runs | `schedule_runs` |
| Idempotency keys | `idempotency_keys` |
| Rate-limit counts | `throttle_hits` |

## More than one process

Processes on the same host can share the file. Each process claims jobs with
an atomic `UPDATE`, the schedule lock lets one process enqueue each run, and
the rate-limit counts are shared. To run the schedules in one process only,
set `JOBS_SCHEDULER_ENABLED=false` in the other processes.

## Change a table

Add a `Migration` with the next version to `MIGRATIONS` in the adapter. Never
change a migration that a release contains.

```python
MIGRATIONS = (
    Migration(1, "create the table tasks", _V1),
    Migration(2, "add the column priority", "ALTER TABLE tasks ADD COLUMN priority INTEGER;"),
)
```
