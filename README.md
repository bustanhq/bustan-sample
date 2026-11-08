# bustan-sample

A sample API made with [bustan](https://bustan.dev) 2.0.3. Each user has
tasks, and a task can recur. The identity module gives and revokes JWT
bearer tokens. Events, background jobs and cron schedules connect the
modules. The data is in memory or in SQLite, as `DATABASE_BACKEND` selects.

The sample is the reference layout for bustan projects. The rules in this
file are the rules of that layout.

## Why bustan, not FastAPI

Select bustan for a Python service with more than one feature. It is the
better choice when persons or agents will change the service for a long
time. The structure is enforced, not only recommended:

- A module can use only its own providers and the exports of the modules
  that it imports. The bustan framework refuses to build an application that
  breaks this rule, before the first request. The error names the class, the parameter
  and the module, and it gives the fix.
- A module can export only a provider that it declares or imports.
- Each dependency comes through the constructor, by its type. A test
  replaces a provider by its type.
- `audit.py` of the bustan-dev skill examines the imports between the
  layers. The pre-commit hook and CI run it, and it gives the file and the
  line of each incorrect import.
- `bustan graph` gives the modules, their imports, providers and exports, as
  a table or as JSON.

In FastAPI, a route can depend on each function that it can import, and
these boundaries are conventions. Select FastAPI for a small service that
will stay small, or for a service that must use websockets. The page
[bustan or FastAPI](docs/explanation/bustan-or-fastapi.md) gives the full
comparison, the costs of bustan, and a section for the `AGENTS.md` of your
project.

## Run the project

Python 3.13 or a newer version and [uv](https://docs.astral.sh/uv/) are
necessary.

1. Get the code and install the dependencies:

   ```bash
   git clone https://github.com/bustanhq/bustan-sample.git
   cd bustan-sample
   uv sync
   ```

2. Copy the example configuration to `.env`:

   ```bash
   cp .env.example .env
   ```

3. Make a random secret:

   ```bash
   uv run python -c 'import secrets; print(secrets.token_urlsafe(48))'
   ```

4. Put the secret in `.env` as the value of `IDENTITY_JWT_SECRET`.

5. Install the git hooks:

   ```bash
   lefthook install
   ```

6. Start the server, with a reload after each change in `src/`:

   ```bash
   uv run bustan-sample-serve --reload
   ```

The server listens on `http://127.0.0.1:3000`. The OpenAPI document is at
`/docs/api`, Swagger UI is at `/docs/ui`, and the probes are at
`/health/live` and `/health/ready`. To use a different port, add
`--port 3010`.

To keep the data after a restart, set `DATABASE_BACKEND=sqlite` in `.env`.
The database file is `var/bustan-sample.db`, and git ignores `var/` and
`*.db`. To run the application in a container, see
[docs/how-to/run-in-a-container.md](docs/how-to/run-in-a-container.md).

| Command | Result |
|---|---|
| `uv run bustan-sample-serve` | Starts the server. `--reload` starts it again when a file in `src/` changes |
| `uv run pytest` | Runs the tests |
| `uv run ruff check .` | Lints the code |
| `uv run ruff format --check .` | Examines the format of the code |
| `uv run ty check` | Examines the types |
| `uv run bustan-sample-openapi` | Writes `openapi.yaml` from the code |
| `uv run bustan-sample-openapi --check` | Writes nothing. Exits with 1 if `openapi.yaml` does not agree with the code |

The [tutorial](docs/tutorial/README.md) teaches the design from the first
request to the trade-offs. The [docs](docs/README.md) also give the
configuration, the tooling and the how-to guides.

## Layout

```text
src/bustan_sample/
  app_main.py          # create_asgi_app() and the command bustan-sample-serve
  app_module.py        # the root module
  app_settings.py      # the configuration model
  app_openapi.py       # the OpenAPI settings
  openapi_export.py    # the command bustan-sample-openapi
  modules/             # feature modules
    <module>/
      api/             # controllers, schemas, error filters
      listeners/       # event handlers
      jobs/            # jobs and their handlers
      application/     # commands and queries
      domain/          # entities, values, rules, events, errors, ports
      infra/           # adapters for the ports
      <module>_module.py
      __init__.py      # the public names of the module
  platform/            # shared modules of providers
    clock/
    database/
    events/
    health/
    http/
    idempotency/
    jobs/
    mail/
    request_logging/
    throttling/
tests/
  conftest.py          # fixtures and the test configuration
  support/database.py  # the backends and open_sqlite() for the tests
  support/fakes.py     # test doubles and wait_until()
  bustan_sample/       # the same tree as src/bustan_sample/
```

## Rules

### Modules

1. Put each feature in its own module in `modules/<module>/`.
2. Give the public names of a module in `<module>/__init__.py`. Other
   modules import only these names.
3. Import each module that a module uses in its `@Module(imports=...)`.
   This includes the platform modules. Only `ConfigModule` is global.
4. Bind each port to an adapter in `<module>_module.py`. Use
   `ClassProvider` for one adapter, and a `FactoryProvider` if the
   configuration selects the adapter.

Example: the tasks module imports `IdentityModule`, `CurrentUser`,
`AuthenticatedUser`, `STRATEGY` and `UserRegistered` from
`bustan_sample.modules.identity`. It imports no other file of identity.

### Layers

| Folder | Contents | Can import |
|---|---|---|
| `api/` | Controllers, Pydantic schemas, error filters | `application/`, `domain/`, platform, the public names of other modules |
| `listeners/` | Event handlers | `application/`, `domain/`, `jobs/`, platform, public names |
| `jobs/` | A job and its handler in each file | `application/`, `domain/`, platform |
| `application/` | A command or a query and its handler in each file | `domain/`, platform |
| `domain/` | Entities, values, pure rules, events, errors, ports | The Python standard library only |
| `infra/` | Adapters for the ports | `domain/`, platform, external libraries |

- `api/`, `listeners/` and `jobs/` are the entry points. Each one changes a
  request, an event or a job into a command or a query. They have no
  business logic.
- `application/` never imports `api/`, `listeners/` or `jobs/`.
- `domain/` imports no bustan code, reads no clock, and uses no network,
  file or database. It gets the time as an argument, for example
  `Task.create(..., now)`.
- A port is an abstract class in `domain/`. Its methods are async if an
  adapter can wait for a network, a file or a database.

### Names

| Item | File | Classes |
|---|---|---|
| Module | `<module>_module.py` | `<Module>Module` |
| Controller | `api/<name>_controller.py` | `<Name>Controller` |
| Schemas | `api/<name>_schemas.py` | `<Name>Request`, `<Name>Response` |
| Error filter | `api/<name>_errors_filter.py` | `<Name>ErrorsFilter` |
| Command | `application/<request>_command.py` | `<Request>Command`, `<Request>Handler` |
| Query | `application/<request>_query.py` | `<Request>Query`, `<Request>Handler` |
| Event handler | `listeners/on_<event>.py` | `On<Event>` |
| Job | `jobs/<work>_job.py` | `<Work>Job`, `<Work>Handler` |
| Events | `domain/events.py` | One frozen dataclass for each event |
| Port | `domain/<name>.py` | `<Name>` |
| Adapter | `infra/<kind>_<name>.py` | `<Kind><Name>`, for example `InMemoryTaskRepository` |

Name a job by its work, not by the event that starts it. Write
`send_welcome_email_job.py`, not `user_registered_job.py`. One event can
start many jobs, and a schedule can start the same job.

### Algorithms

| The algorithm | Location |
|---|---|
| A business rule of one module, with no network, file or database | `domain/`, as pure functions or a plain class |
| A method that you can replace, or that wraps a library, a service or a model | A port in `domain/`, an adapter in `infra/` |
| An algorithm that uses stored data | The steps in `application/`. The calculation stays in `domain/` |
| Generic, and it uses DI, configuration, state or the clock | `platform/<name>/`, as a provider |

The recurrence of tasks is the example:

- `tasks/domain/recurrence.py` holds `RecurrenceRule` and the pure function
  `next_due_on()`.
- `tasks/domain/recurrence_parser.py` holds the port `RecurrenceParser`. It
  changes a repeat phrase, for example "every 2 weeks on Monday", into a
  rule.
- `tasks/infra/rule_based_recurrence_parser.py` is the default adapter. It
  uses a small grammar and no network. A model adapter can replace it
  with no change to the domain or the application.
- `UpdateTaskHandler` adds the next task when a recurring task becomes done.

### Storage

- `DATABASE_BACKEND` selects the adapter of each storage port: `memory`
  (the default) or `sqlite`.
- Each port with storage has two adapters in `infra/`, for example
  `InMemoryTaskRepository` and `SqliteTaskRepository`.
- In `<module>_module.py`, a factory function makes only the selected
  adapter. bustan calls the hooks of the instance that the factory makes:

  ```python
  def _task_repository(database: Database) -> TaskRepository:
      if database.is_sqlite:
          return SqliteTaskRepository(database)
      return InMemoryTaskRepository()
  ```

- `platform/database` has one SQLite connection for each process. It opens
  the connection in `on_module_init` and closes it in `on_module_destroy`.
- An SQLite adapter declares `MIGRATIONS` and calls
  `Database.migrate(component, MIGRATIONS)` in its own `on_module_init`. To
  change a table, add a migration with the next version. Never change a
  migration that a release contains. The adapter holds its SQL.
- Use `Database.transaction()` for statements that must all commit, or
  none. In the block, each statement of the same task joins the
  transaction: the repositories, the job queue and the event bus. Do slow
  work, for example a password hash or a network call, before the block.
- The memory backend has no rollback. Its `transaction()` only defers the
  events and the jobs of the block until the end of the block.
- Keep a time as UTC text that always has the same length (`to_text()`).
  Thus the text order is the time order.
- The two adapters of a port must give the same results. A contract test
  in `tests/.../domain/test_<port>.py` runs each test on each adapter.

### Events

- An event is a frozen dataclass in `domain/events.py`.
- An application handler publishes an event in the transaction that saves
  the data. Thus the data and the event commit together, or neither:

  ```python
  async with self._database.transaction():
      await self._users.save(user)
      await self._events.publish(UserRegistered(user.id, user.email, user.created_at))
  ```

- With SQLite, the deliveries are rows in the table `jobs`, written in the
  transaction of the publisher: the table is the transactional outbox. The
  listeners run after the commit. A rollback drops the event.
- A listener subscribes in its own `on_module_init`. Thus a new listener is
  one line in `providers`.
- Each listener runs in a background task, and the response does not wait.
  An error goes to the log. At shutdown, the bus waits for the running
  listeners.
- If the application must not lose the work, put the work in a job. Also
  use a job for work that must have retries.

### Jobs and schedules

- A job is a frozen dataclass with JSON-compatible fields: `str`, `int`,
  `float` or `bool`. Thus a durable queue can store it.
- The handler registers in its `on_module_init`:
  `jobs.register(SendWelcomeEmailJob, self.run, max_attempts=5)`.
- A scheduled job also calls `scheduler.schedule(name, cron, make_job)`. The
  cron expressions use UTC.
- A failed job runs again after `JOBS_RETRY_DELAY_SECONDS`. Each next delay
  is two times longer.
- A handler raises `PermanentJobError` when a retry cannot succeed: the job
  fails immediately. It raises `RetryJobLater(seconds)` to set the wait, for
  example after a `Retry-After` of an external service.
- The name of the job class is the type of the job in the SQLite table.
  Thus each job class has a unique name.
- With the SQLite backend, a job stays in the table until it ends. A job
  survives a restart, and all processes on the same file share the jobs.
- If a process stops during a job, a different worker starts the job again
  after `JOBS_LEASE_SECONDS`. Thus a job handler must give the same result
  if it runs two times.
- An enqueue in a transaction commits with the transaction. The job does not
  start before the commit.
- For work that must happen one time, keep an idempotency key
  (`IdempotencyKeys`). Name the key with the module and the work, for
  example `tasks.starter_task:<user id>`.
  - Database work: add the key and do the work in one transaction. Do the
    work only if `add()` returns `True`.
  - External work, for example an email: stop if `contains()` returns
    `True`. Do the work, then add the key.
- `ScheduleLock` lets only one process enqueue each run of a schedule.
  `JOBS_SCHEDULER_ENABLED=false` turns the scheduler off in a process.

### External APIs

- Each external API is an adapter of a port, for example `ResendMailer` of
  `Mailer`. The domain and the application never import `httpx2`.
- The adapter gets its client from `HttpClientFactory.make(service,
  base_url, headers=...)`. It makes the client in `on_module_init` and
  closes it in `on_module_destroy`.
- `HttpClient.request()` sends the correlation id of the request and writes
  one log record for each call. A timeout or a network error raises
  `ExternalServiceError`. `raise_for_response()` raises it for a status
  that is not 2xx. `retryable` tells if a retry can succeed.
- A call that changes something in the other system runs in a job. Only the
  job queue retries: the client never retries. The job handler changes an
  `ExternalServiceError` into `PermanentJobError` or `RetryJobLater`.
- Give the provider the idempotency key of the work, if the provider accepts
  one. Then a retry after a lost response does the work one time.
- A configuration key selects the adapter, for example `MAIL_BACKEND=log|resend`. The
  application does not start if the selected adapter has no credentials.
- Tests give `HttpClientFactory` an `httpx2.MockTransport`. No test calls
  the network.

### Platform

A platform module is a bustan module of providers, for example services,
guards, interceptors, filters and middleware. It has no controllers, and it
knows no feature module.

| Module | Providers |
|---|---|
| `clock` | `Clock`, and `FixedClock` for tests |
| `database` | `Database`: the SQLite connection, if the backend is `sqlite`, and `transaction()` with `after_commit()` and `after_rollback()` |
| `events` | `EventBus`: with SQLite, the deliveries go in the table `jobs`, in the transaction of the publisher |
| `http` | `HttpClientFactory`, `HttpClient`, `ExternalServiceError`, `raise_for_response()` |
| `idempotency` | `IdempotencyKeys` (port), `InMemoryIdempotencyKeys`, `SqliteIdempotencyKeys` |
| `jobs` | `JobQueue` (port), `InMemoryJobQueue`, `SqliteJobQueue`, `JobScheduler`, `ScheduleLock` (port), `InMemoryScheduleLock`, `SqliteScheduleLock` |
| `mail` | `Mailer` (port), `LogMailer`, `ResendMailer`. `MAIL_BACKEND` selects one |
| `health` | `DatabaseIndicator` and `HealthChecks`: the readiness check of SQLite |
| `request_logging` | A global interceptor that writes one log record for each request, except the probes |
| `throttling` | `BackendThrottlerStorage`: the rate-limit counts in memory or in SQLite |

### Configuration

- `app_settings.py` is the one model of the configuration. Each key starts
  with the name of the module that reads it, for example `DATABASE_`,
  `IDENTITY_`, `JOBS_` or `MAIL_`.
- If a value is missing or not valid, the application does not start.
- `.env` holds the local values, and git ignores it. `.env.example` gives
  each key. A value in the environment overrides the value in `.env`.

### Errors

- The domain raises its own errors, for example `TaskNotFoundError`. It does
  not know HTTP.
- An error filter in `api/` changes each domain error into an HTTP error.
  The bustan filter writes the RFC 9457 problem details. Thus all errors
  have the same shape.
- A task of a different user gives 404, the same as a task that does not
  exist.

### Tests

- `tests/bustan_sample/` has the same tree as `src/bustan_sample/`, with no
  `__init__.py` files.
- The tests use the importlib mode of pytest. Thus two modules can each
  have a test file with the same name.
- `tests/support/fakes.py` holds the test doubles `RecordingMailer` and
  `RecordingJobQueue`, and the function `wait_until()`.
- The `client` fixture gives the full application with `FixedClock`, a fast
  password hasher and `RecordingMailer`. The events and the jobs run as in
  production. Use `wait_until()` for work in the background.
- Each test that uses `client` runs two times: one time with the memory
  backend, and one time with a new SQLite file in `tmp_path`.
- A test of an application handler makes the handler directly, with the
  adapters in memory. It does not start the application.
- `conftest.py` puts the test configuration in the environment before a test
  imports the application. `ConfigModule` reads the environment at import
  time.

### API document

- Bustan makes the OpenAPI document from the routes and the Pydantic models.
  The Api decorators (`@ApiTags`, `@ApiOperation`, `@ApiResponse`,
  `@ApiBearerAuth`) add the information that a signature cannot show.
- Put `@ApiBearerAuth()` only on the routes for which a token is
  necessary.
- After a change to a route or a schema, run `uv run bustan-sample-openapi`.
  Then commit `openapi.yaml`. If the file does not agree with the code, a
  test gives an error.

## Limits

- With the memory backend, a restart loses all data. Use one process only.
- With the memory backend, events and jobs are in memory, and a
  transaction has no rollback.
- The client sends the correlation id but no `traceparent`: bustan 2.0.3
  has no public function that gives it.
- Processes can share an SQLite file only on one host. For more than one
  host, a database server is necessary, behind the same ports.
- Two applications in one process share the rate-limit storage. Run one
  application at a time in a process.
- The rule-based parser knows only English repeat phrases.

## Report a bustan issue

If bustan itself has a defect or a limit, report it to
[bustanhq/bustan](https://github.com/bustanhq/bustan), or send a fix. A coding
agent obeys the same steps:

1. Write the smallest script that shows the behavior, with the bustan version
   pinned and no code of the project. If the script does not show it, the
   cause is in the project.
2. Look for the same issue with `gh issue list --repo bustanhq/bustan --state
   all --search "<words>"`.
3. Show the draft to the user. File it only after the user agrees, with the
   template of the repository and the script.
4. Put the work-around in one place, with a comment that gives the issue
   link. Add the issue to the gaps table in chapter 10 of the tutorial.

Never report a security vulnerability in a public issue: send it to
`security@bustan.dev`. Never put a secret or private data in an issue. The
page [Report a bustan issue, or send a fix](docs/how-to/report-a-bustan-issue.md)
gives the templates, the commands and the rules for a pull request.

## Agent skill

`.agents/skills/bustan-dev/` is an agent skill for bustan projects. It gives
the rules of this repository and recipes for each kind of change. It also
has three scripts. Each script prints its usage with `--help`.

- `audit.py` examines the layout, the imports and the names of a project.
- `new_module.py` writes a feature module with its tests.
- `copy_platform.py` copies the platform modules into a new project.

Agent tools that read `.agents/skills/` find the skill there. For Claude Code,
link `.claude/skills` to `../.agents/skills`. To use the skill in other
projects, link its folder into the skill folder of your tool. Change the
skill in the same commit as the code that it describes.

## License

Apache License 2.0. See [LICENSE](LICENSE).
