# bustan-sample

A sample API made with [bustan](https://bustan.dev) 2.0.3. Each user has
tasks, and a task can recur. The identity module gives and revokes JWT
bearer tokens. Events, background jobs and cron schedules connect the
modules.

The sample is the reference layout for bustan projects. The rules in this
file are the rules of that layout.

## Run the project

Python 3.13 or a newer version and [uv](https://docs.astral.sh/uv/) are
necessary.

1. Install the dependencies:

   ```bash
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

5. Start the server:

   ```bash
   uv run dev
   ```

The server listens on `http://127.0.0.1:3000`. The OpenAPI document is at
`/docs/api`, and Swagger UI is at `/docs/ui`.

| Command | Result |
|---|---|
| `uv run dev` | Starts the server, and starts it again when a file in `src/` changes |
| `uv run start` | Starts the server with no reload |
| `uv run pytest` | Runs the tests |
| `uv run ruff check .` | Lints the code |
| `uv run ruff format --check .` | Examines the format of the code |
| `uv run ty check` | Examines the types |
| `uv run bustan-sample-openapi` | Writes `openapi.yaml` from the code |
| `uv run bustan-sample-openapi --check` | Writes nothing. Exits with 1 if `openapi.yaml` does not agree with the code |

## Layout

```text
src/bustan_sample/
  app_main.py          # entry points: create_asgi_app(), start, dev
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
    events/
    jobs/
    mail/
    request_logging/
tests/
  conftest.py          # fixtures and the test configuration
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
4. Bind each port to an adapter in `<module>_module.py`, with
   `ClassProvider`. To change an adapter, change only that line.

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

### Events

- An event is a frozen dataclass in `domain/events.py`.
- An application handler publishes an event after it saves:
  `await events.publish(UserRegistered(...))`.
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

### Platform

A platform module is a bustan module of providers, for example services,
guards, interceptors, filters and middleware. It has no controllers, and it
knows no feature module.

| Module | Providers |
|---|---|
| `clock` | `Clock`, and `FixedClock` for tests |
| `events` | `EventBus` |
| `jobs` | `JobQueue` (port), `InMemoryJobQueue`, `JobScheduler` |
| `mail` | `Mailer` (port), `LogMailer` |
| `request_logging` | A global interceptor that writes one log record for each request |

### Configuration

- `app_settings.py` is the one model of the configuration. Each key starts
  with the name of the module that reads it, for example `IDENTITY_` or
  `JOBS_`.
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

- All data is in memory: tasks, users, revoked tokens, events and jobs. A
  restart loses it.
- Each process has its own scheduler. Thus with more than one process, a
  scheduled job occurs one time in each process. Use a lock or one
  scheduler process.
- The rule-based parser knows only English repeat phrases.
