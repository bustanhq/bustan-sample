# 7. Events, jobs and schedules

## What you learn

- How an event lets one module react to another with no direct call.
- How background jobs give retries, and why a job must be idempotent.
- How cron schedules run, and how a lock stops a duplicate run.
- What changes when the backend is SQLite.

## Concepts

### Events decouple modules

When a user registers, two things must happen: a welcome email, and a starter
task. Identity must not call the tasks module: then identity would depend on
tasks, and each new reaction would change identity. So identity **publishes**
an event, and each interested module **subscribes**:

```python
# identity: application/register_user_command.py, after the save
await self._events.publish(UserRegistered(user.id, user.email, user.created_at))
```

```python
# tasks: listeners/on_user_registered.py
@Injectable()
class OnUserRegistered:
    def on_module_init(self) -> None:
        self._events.subscribe(UserRegistered, self.handle)

    async def handle(self, event: UserRegistered) -> None:
        await self._create_task.execute(CreateTaskCommand(owner_id=event.user_id, title=...))
```

The event is a frozen dataclass in `identity/domain/events.py`. Identity
exports it in its `__init__.py`; the tasks module imports only that name. A
listener subscribes in its own `on_module_init`, so a new listener is one line
in `providers` and no other file changes.

With the memory backend, `publish()` starts one background task for each
listener and returns at once. The response does not wait. A listener error
goes to the log and does not touch the other listeners.

### Jobs give retries

Sending an email can fail. A failed email must be tried again, and a listener
does not retry. So the identity listener only **enqueues a job**:

```python
await self._jobs.enqueue(SendWelcomeEmailJob(user_id=str(event.user_id), email=event.email))
```

The job handler registers in its `on_module_init`, with `max_attempts=5`. If
it raises, the queue tries again after `JOBS_RETRY_DELAY_SECONDS`, and each
next wait is two times longer. A job that fails on each attempt is kept as
failed, for a person to examine.

A job is a frozen dataclass with JSON fields (`str`, `int`, `float`, `bool`),
so a durable queue can store it. Its class name is its type in the queue.

**Idempotency.** A job can run more than one time: a process can stop after
the work and before it marks the job as done. So a handler must give the same
result if it runs two times. "Send the welcome email" is safe to repeat in
this sample; "charge the card" would need a check first.

### Schedules and the lock

`JobScheduler` enqueues a job on a cron expression, in UTC. The revoked-token
cleanup registers itself:

```python
self._scheduler.schedule("identity.purge_revoked_tokens", "*/10 * * * *", PurgeRevokedTokensJob)
```

With two processes, each one has a scheduler, and each one would enqueue the
same run. The `ScheduleLock` port stops that: before it enqueues, a scheduler
claims the run (the name and the run time). The SQLite lock is a row with a
primary key, so only one insert succeeds in all processes. You can also turn
the scheduler off in a process with `JOBS_SCHEDULER_ENABLED=false`.

### With SQLite

| Part | Memory | SQLite |
|---|---|---|
| Jobs | asyncio workers, lost on a restart | the table `jobs`, kept on a restart, shared by processes |
| Event deliveries | background tasks | one `DeliverEvent` job for each listener, with retries |
| Schedule lock | one process only | the table `schedule_runs` |

A worker claims a job with one `UPDATE ... RETURNING` statement, so two workers
never get the same job. A claim has a lease (`JOBS_LEASE_SECONDS`); if a
process stops during a job, a different worker takes the job after the lease.

## Try it

1. Register a user while you watch the server log. You see a `mail sent`
   record from `LogMailer`, with a masked address, and a `job done` record.

2. Write a listener. In the tasks module, add `listeners/on_user_registered_log.py`
   with a class that subscribes to `UserRegistered` and logs the user id with
   `Logger("Welcome").log(...)`. Add the class to `providers` in
   `tasks_module.py`. Register a new user, and find your record in the log.
   Then remove the file and the line.

3. Make a job fail. In `identity/jobs/send_welcome_email_job.py`, raise
   `ConnectionError("down")` in `run()` for the first two attempts (keep a
   counter on the handler). Register a user and watch the `job failed, retry`
   records and the final `job done`. Then undo the change.

4. Run the tests of the platform:

   ```bash
   uv run pytest -q tests/bustan_sample/platform
   ```

## Why it is built this way

- **No event bus or queue in bustan 2.0.3.** The platform modules
  `events` and `jobs` add them as ports with adapters, in the same style as
  the rest of the code.
- **Durable delivery, not an outbox.** With SQLite, a delivery survives a
  restart. But the publisher saves first and publishes after: if the process
  stops between the two, the event is lost. A transactional outbox would
  write the data and the event in one transaction; it needs one transaction
  across the repository and the bus, which this sample does not have.
- **Cron with a lock, not one scheduler process.** The lock works with no
  change to the deployment. The switch is there for a deployment that wants
  one scheduler process anyway.

## Check yourself

1. Why does the identity listener enqueue a job instead of sending the email?
2. A handler runs two times for one job. When is that a problem?
3. Two processes are due for the same cron run. What decides which one enqueues it?

Next: [8. Testing](08-testing.md).
