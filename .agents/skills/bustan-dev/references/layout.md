# Layout

```text
src/<pkg>/
  __init__.py          # a docstring only
  app_main.py          # create_asgi_app() and the command <project>-serve
  app_module.py        # the root module: configuration, platform, features
  app_settings.py      # the pydantic settings model
  app_openapi.py       # SwaggerOptions: /docs/api and /docs/ui
  openapi_export.py    # the command <project>-openapi [--check]
  modules/
    <module>/
      __init__.py      # the public names: the module class, events, auth types
      <module>_module.py
      api/             # controllers, Pydantic schemas, error filters, auth helpers
      listeners/       # on_<event>.py
      jobs/            # <work>_job.py
      application/     # <request>_command.py, <request>_query.py
      domain/          # entities, values, rules, events, errors, ports
      infra/           # adapters of the ports
  platform/
    clock/             # Clock, FixedClock
    database/          # Database (transaction, after_commit), Migration, to_text, from_text
    events/            # EventBus, DeliverEvent: the job table is the outbox
    idempotency/       # IdempotencyKeys, InMemoryIdempotencyKeys, SqliteIdempotencyKeys
    jobs/              # JobQueue, InMemoryJobQueue, SqliteJobQueue, JobScheduler, ScheduleLock
    http/              # HttpClientFactory, HttpClient, ExternalServiceError, raise_for_response
    mail/              # Mailer, LogMailer, ResendMailer (MAIL_BACKEND)
    health/            # DatabaseIndicator, HealthChecks
    request_logging/   # a global interceptor
    throttling/        # BackendThrottlerStorage, THROTTLER_STORAGE, ThrottlingModule
tests/
  conftest.py          # environment first, then the clock, mailer, client and sign_up fixtures
  support/             # database.py (BACKENDS, memory_database, open_sqlite), fakes.py
  <pkg>/               # the same tree as src/<pkg>/, with no __init__.py
docs/                  # README index, how-to, reference, tutorial
```

## What each layer can import

| Layer | Contents | Can import |
|---|---|---|
| `api/` | Controllers, schemas, error filters | `application/`, `domain/`, platform, public names of other modules |
| `listeners/` | Event handlers | `application/`, `domain/`, `jobs/`, platform, public names |
| `jobs/` | A job and its handler in each file | `application/`, `domain/`, platform |
| `application/` | A command or a query and its handler in each file | `domain/`, platform |
| `domain/` | Entities, values, pure rules, events, errors, ports | the standard library |
| `infra/` | Adapters | `domain/`, platform, libraries |
| `<module>_module.py`, `__init__.py` | The composition | each layer of the module |
| `platform/<name>/` | Shared providers, no controllers | other platform modules, libraries |

Inside a module, use relative imports (`from ..domain.task import Task`).
For the platform and other modules, use absolute imports
(`from <pkg>.platform.clock import Clock`, `from <pkg>.modules.identity import CurrentUser`).

## Names

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
| Events | `domain/events.py` | a frozen dataclass for each event |
| Port | `domain/<name>.py` | `<Name>` (an ABC) |
| Adapter | `infra/<kind>_<name>.py` | `<Kind><Name>`, for example `SqliteTaskRepository` |

Name a job by its work (`send_welcome_email_job.py`), not by the event that
starts it. Do not name a folder `saga` for a one-step reaction: a saga keeps
state across steps.

## Where an algorithm goes

| The algorithm | Location |
|---|---|
| A business rule of one module, with no network, file or database | `domain/`, pure functions or a plain class |
| A method that you can replace, or that wraps a library, a service or a model | a port in `domain/`, an adapter in `infra/` |
| An algorithm that uses stored data | the steps in `application/`, the calculation in `domain/` |
| Generic, with DI, configuration, state or the clock | `platform/<name>/` as a provider |
| Generic and pure | `src/<pkg>/lib/` (no bustan import, no modules or platform import) |

Example: task recurrence. `domain/recurrence.py` has `RecurrenceRule` and the
pure `next_due_on()`. `domain/recurrence_parser.py` has the port.
`infra/rule_based_recurrence_parser.py` is the adapter, and a model adapter
can replace it.
