# 7. Events, jobs and schedules

## What you learn

- How an event lets one module react to another with no direct call.
- How background jobs give retries, and why a job must be idempotent.
- How cron schedules run, and how a lock stops a duplicate run.
- What changes when the backend is SQLite.
- How a transactional outbox writes an event in the transaction of its data.
- How idempotency keys make work happen one time.

## Concepts

### Events decouple modules

When a user registers, two things must happen: a welcome email, and a starter
task. Identity must not call the tasks module: then identity would depend on
tasks, and each new reaction would change identity. So identity **publishes**
an event, and each interested module **subscribes**:

```python
# identity: application/register_user_command.py
async with self._database.transaction():
    await self._users.save(user)
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
listener after the commit. The response does not wait. A listener error
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
result if it runs two times. When a second run would do harm, for example a
second email or a second starter task, the handler keeps an idempotency key.
The section "Idempotency keys" below shows how.

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
| Idempotency keys | a set in the process | the table `idempotency_keys` |

A worker claims a job with one `UPDATE ... RETURNING` statement, so two workers
never get the same job. A claim has a lease (`JOBS_LEASE_SECONDS`); if a
process stops during a job, a different worker takes the job after the lease.

### The outbox: the data and the event in one transaction

Look at the order of two writes: the user, then the event. If the process
stops between them, the user exists and no module hears of it: no starter
task, no email. If the event goes first, a listener can react to a user that
never commits.

A **transactional outbox** removes the gap. The event is a row in the same
database as the data, written in the same transaction. With SQLite, that row
is a `DeliverEvent` job in the table `jobs`:

1. `RegisterUserHandler` opens `transaction()`.
2. It saves the user. The INSERT joins the transaction.
3. It publishes `UserRegistered`. The bus enqueues one `DeliverEvent` for
   each listener, and each INSERT joins the same transaction.
4. The transaction commits the user and the deliveries together, or it rolls
   back all of them.
5. After the commit, `after_commit()` wakes the job workers. A worker claims
   each delivery and calls its listener.

The table `jobs` is the outbox, and the job workers are the relay that
delivers from it. No second process reads the outbox, and a delivery gets
the retries and the lease of each job. An enqueue of a different job in the
transaction works the same way.

With the memory backend, the bus starts the listeners after the end of the
block, and drops them if the block raises an error. The memory data has no
rollback, so only SQLite gives the full guarantee.

### Idempotency keys: work that happens one time

The outbox gives **at least one** delivery: a listener can run two times for
one event. A key in `IdempotencyKeys` turns that into one result. A key
names one piece of work, and starts with the module:
`tasks.starter_task:<user id>`. The store accepts each key one time:
`add()` returns `True` the first time and `False` after that.

For work in the database, add the key and do the work in one transaction:

```python
# tasks: listeners/on_user_registered.py
async with self._database.transaction():
    if not await self._keys.add(f"tasks.starter_task:{event.user_id}"):
        return
    await self._create_task.execute(CreateTaskCommand(owner_id=event.user_id, ...))
```

The key and the task commit together. A second delivery finds the key and
stops. If the task fails, the key rolls back with it, and the retry does the
work. The work happens exactly one time.

An email is not in the database, and a transaction must not stay open
during a network call. So the email job adds the key after the send:

```python
# identity: jobs/send_welcome_email_job.py
key = f"identity.welcome_email:{job.user_id}"
if await self._keys.contains(key):
    return
await self._mailer.send(job.email, SUBJECT, BODY)
await self._keys.add(key)
```

A failed send leaves no key, so the retry sends. If the process stops after
the send and before the key, the retry sends a second email. That is the
only duplicate, and it is a rare one. For external work, exactly one time
needs the help of the other system, for example a provider that accepts an
idempotency key of its own.

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

5. See the outbox. In `tasks/listeners/on_user_registered.py`, raise
   `ConnectionError("down")` at the start of `handle()`. Start the server
   with SQLite (chapter 5) and `JOBS_RETRY_DELAY_SECONDS=0.1`, register a
   user, and read the table:

   ```bash
   sqlite3 var/bustan-sample.db 'SELECT type, status, attempt, payload FROM jobs'
   ```

   You see the `DeliverEvent` row of the tasks listener. After five
   attempts its status is `failed`, and its payload is the event as JSON.
   The delivery of the identity listener is not there: it ended, and the
   queue deleted it. Then undo the change.

6. Remove a key. In `tasks/listeners/on_user_registered.py`, remove the two
   lines of the key check, and run:

   ```bash
   uv run pytest -q tests/bustan_sample/modules/tasks/listeners
   ```

   The test that delivers one event two times fails: the user gets two
   starter tasks. Then undo the change.

## Why it is built this way

- **No event bus or queue in bustan 2.0.3.** The platform modules
  `events` and `jobs` add them as ports with adapters, in the same style as
  the rest of the code.
- **The job table is the outbox.** A separate outbox table would need its
  own relay: a loop that reads the table and publishes. The job queue is that
  loop, with retries and a lease. The cost: an event can wait for a free
  worker, and the poll interval of the other processes.
- **One transaction through a context variable.** The repositories and the
  bus join the transaction of their task with no change to their ports.
  Chapter 5 gives the details.
- **Keys that are explicit.** A handler names its key and decides where it
  goes: before the work in a transaction, or after an external call. A
  generic decorator would hide that choice, and the choice is the design.
- **Cron with a lock, not one scheduler process.** The lock works with no
  change to the deployment. The switch is there for a deployment that wants
  one scheduler process anyway.

## Check yourself

1. Why does the identity listener enqueue a job instead of sending the email?
2. A handler runs two times for one job. When is that a problem?
3. Two processes are due for the same cron run. What decides which one enqueues it?
4. The process stops after the user commits. Why is the starter task not lost?
5. Why does the email job add its key after the send, and the starter task
   before the work?

Next: [8. Testing](08-testing.md).
