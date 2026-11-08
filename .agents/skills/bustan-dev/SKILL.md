---
name: bustan-dev
description: Build, extend and audit Python APIs made with bustan (the NestJS-style Python framework, PyPI bustan 2.x). Feature modules are in src/<pkg>/modules/<module>/ with the layers api, listeners, jobs, application, domain and infra. Shared provider modules are in src/<pkg>/platform/. Each storage port has a memory adapter and an SQLite adapter, and DATABASE_BACKEND selects one. Use this skill for each task on a bustan project, also when the user does not name the skill. Examples are a new project, module, entity, route, port, adapter or migration. Other examples are an event, a listener, a job, a cron schedule, auth, a rate limit, a health check or the OpenAPI document. Tests, hooks, CI, a release and the container image are also examples. Also use it when the user names bustan, bustan init, AsgiTestClient, create_test_app or FactoryProvider.
compatibility: uv 0.13 or a subsequent version, Python 3.13 or a subsequent version, git and lefthook. The container image needs Docker. The scripts run with uv (standard library only).
metadata:
  version: "1.3"
  reference: https://github.com/bustanhq/bustan-sample (main), the public sample that holds this skill in .agents/skills/bustan-dev/, 2026-11-08
  bustan: "2.0.3"
---

# bustan projects

bustan composes an application from modules with constructor injection, in
the same way as NestJS. This skill gives the layout, the rules and the
recipes for each bustan project. The reference project
<https://github.com/bustanhq/bustan-sample> obeys each rule. When a recipe is not clear, read the same part of
the reference there. Its tutorial (`docs/tutorial/`) gives the cause of each part of
the design. This skill is a part of that repository, in
`.agents/skills/bustan-dev/`. Change the skill there, in the same commit as
the change of the reference that it describes.

## The rules

1. **uv makes the project.** `uv init --package --python 3.13 <dir>`, then
   `uv add bustan` and `uv run bustan init`. Never write `pyproject.toml` by
   hand. Never use pip or venv.
2. **Layout.** A feature is a module in `src/<pkg>/modules/<module>/` with
   `api/`, `listeners/`, `jobs/`, `application/`, `domain/`, `infra/`,
   `<module>_module.py` and `__init__.py`. A shared module of providers with
   no controllers is in `src/<pkg>/platform/<name>/`. The root module and the
   entry points are in `src/<pkg>/app_*.py`. See
   [references/layout.md](references/layout.md).
3. **Imports go in one direction.** `api/`, `listeners/` and `jobs/` are the
   entry points and call `application/`. `application/` calls `domain/` and
   the platform. `infra/` implements the ports of `domain/`. `domain/` imports
   only the standard library. A different module imports only the names in
   `<module>/__init__.py`. The platform never imports a feature module.
   `scripts/audit.py` examines these rules.
4. **Names.** `<request>_command.py`, `<request>_query.py`,
   `listeners/on_<event>.py`, `jobs/<work>_job.py` (named by the work),
   `api/<name>_controller.py`, `<name>_schemas.py`, `<name>_errors_filter.py`,
   `infra/<kind>_<name>.py`.
5. **Ports and adapters.** Each port is an ABC in `domain/` with async
   methods. Each storage port has a memory adapter and an SQLite adapter. A
   `FactoryProvider` in `<module>_module.py` makes only the adapter that
   `DATABASE_BACKEND` selects. An SQLite adapter declares `MIGRATIONS` and
   calls `Database.migrate()` in `on_module_init`.
6. **Errors.** The domain raises its own errors. An error filter in `api/`
   changes them into `bustan.errors` exceptions, and the bustan filter writes
   RFC 9457 problem details. A resource of a different user gives 404.
7. **Events and jobs.** A handler publishes an event in the
   `Database.transaction()` that saves its data (the outbox). A listener
   subscribes and a job handler registers in its own `on_module_init`. A job
   is a frozen dataclass with JSON fields. A listener or a job handler gives
   the same result if it runs two times, or keeps an idempotency key.
8. **Configuration.** One pydantic model in `app_settings.py` validates the
   configuration, through
   `ConfigModule.for_root(env_file=".env", validation_schema=...)`. Each key
   starts with the module name. A missing secret stops the start.
9. **Tests mirror src/.** Each HTTP test runs on the two backends through the
   `client` fixture. A contract test of each port runs on each adapter. See
   [references/testing.md](references/testing.md).
10. **The repository is clean.** It has lefthook hooks and Conventional
    Commits with no attribution lines. It has one CI workflow, a release
    workflow on `vX.Y.Z` and Dependabot. It has a `LICENSE`, a changelog, and
    a tutorial, how-to guides and a reference in `docs/`. It has a container
    image on Chainguard bases, and its agent skill in `.agents/skills/`. See
    [references/tooling.md](references/tooling.md).

## Workflow A: start a project

```text
- [ ] 1. Settle the open decisions with the user: name, purpose, auth, storage
- [ ] 2. uv init --package --python 3.13 <dir>; uv add bustan; uv run bustan init
- [ ] 3. Delete the greeting of the scaffold (app_controller, app_service, their tests)
- [ ] 4. uv run <skill>/scripts/copy_platform.py <dir>, then do the steps it prints
- [ ] 5. Copy from the reference: app_settings.py, app_main.py (serve command),
         app_openapi.py, openapi_export.py, tests/conftest.py, .env.example
- [ ] 6. Add the tooling: references/tooling.md
- [ ] 7. uv run ruff check . ; uv run ty check ; uv run pytest ; uv run <skill>/scripts/audit.py <dir>
- [ ] 8. git commit -m "feat: add the project layout"
```

## Workflow B: add a feature module

1. Run `uv run <skill>/scripts/new_module.py <dir> <module> <entity>`. It
   writes the four layers, the two adapters with a migration, three routes
   and the tests. It never replaces a file.
2. Add `<Module>Module` to the imports of the root module.
3. Change the entity, the commands and the queries to the real feature.
4. Run the OpenAPI export, the checks and `audit.py`.

## Workflow C: change a module

| Task | Do this |
|---|---|
| Add a route | A method on the controller with `@Get`/`@Post`/... and `@ApiOperation`/`@ApiResponse`. It calls one command or query handler. Then the OpenAPI export |
| Add a command or a query | `application/<request>_command.py`: a frozen dataclass and an `@Injectable` handler with `execute()`. Add the handler to `providers` |
| Add a rule | A pure function or a method in `domain/`. It gets the time as an argument |
| Add a port | An ABC in `domain/`, a memory and an SQLite adapter in `infra/`, a `FactoryProvider`, a contract test in `tests/.../domain/test_<port>.py` |
| Change a table | A new `Migration(next_version, name, sql)` at the end of `MIGRATIONS`. Never change a released one |
| Write more than one row | `async with self._database.transaction():` around the saves. Slow work before the block |
| Add an event | A frozen dataclass in `domain/events.py`. The handler publishes in the transaction that saves the data. Export the event in `__init__.py` if other modules handle it |
| Call an external API | An adapter of the port with a client from `HttpClientFactory` (import `HttpModule`). A call that changes something runs in a job: the job changes `ExternalServiceError` into `PermanentJobError` or `RetryJobLater`. Give the provider the idempotency key. See the recipe "External API" |
| Do work one time | Import `IdempotencyModule`, inject `IdempotencyKeys`. Database work: `add()` the key in the transaction of the work. External work: `contains()`, the work, then `add()` |
| Add a listener | `listeners/on_<event>.py`: an `@Injectable` class with `on_module_init` that subscribes `self.handle`. Add it to `providers` |
| Add a job | `jobs/<work>_job.py`: the job dataclass and an `@Injectable` handler that registers in `on_module_init`, with `max_attempts` |
| Add a schedule | In the job handler, `scheduler.schedule(name, cron, JobClass)` in `on_module_init`. UTC |
| Protect a route | `@Auth(STRATEGY)` on the controller, `@Public()` on an open route, `Annotated[AuthenticatedUser, CurrentUser()]` as an argument, `@ApiBearerAuth()` |
| Limit a route | `@RateLimit(limit=..., window="1m")` |
| Add a configuration key | A field in `app_settings.py` with the module prefix, a line in `.env.example` and in `docs/reference/configuration.md` |

The recipes and the code of each item are in
[references/recipes.md](references/recipes.md).

## Gotchas

- `ConfigModule.for_root()` reads the environment when Python imports the
  root module (bustan issue #417). Set test values in `tests/conftest.py`
  before the first import of the application. To give a test a different
  configuration, override `ConfigService` in `create_test_app`.
- `ThrottlerModule.for_root()` takes its storage at import time. Give it one
  `BackendThrottlerStorage`, and let `ThrottlingModule` bind it at startup.
- An override cannot add a provider that no module binds (bustan #415). A
  module test must have a root with `ConfigModule.for_root(...)`. Write the
  root with `@Module`, not with `create_test_module` (bustan #414).
- `AsgiTestClient(app)` as a context manager runs the lifespan (hooks,
  workers). Without `with`, it runs no lifespan, which the OpenAPI export
  wants. `AsgiTestResponse` has no `raise_for_status()` (bustan #416).
- A provider hook runs only on an instance that bustan made (a class,
  `use_class` or `use_factory`), never on a `use_value`.
- Startup: `on_module_init` for all, then `on_application_bootstrap`.
  Providers run in construction order, dependencies first. Shutdown runs the
  reverse: `before_application_shutdown`, `on_application_shutdown`,
  `on_module_destroy`.
- A path or query value converts with `annotation(raw)`. A `ValueError` gives
  400. Examine the limits of a value (limit, offset) in the controller.
- A handler that returns `None` answers 204. For a status or headers, return
  `HttpResponse.json(body, status_code=..., headers=...)`.
- The framework writes an unhandled exception as plain text beside the JSON
  records (bustan #418). A test that parses the `bustan` logger must skip
  lines that are not JSON.
- For background work in a test, call `wait_until()` of
  `tests/support/fakes.py`. Never sleep for a constant time.
- In `transaction()`, never wait for a different task that uses the
  database. That task waits for the lock, thus the two tasks wait for each
  other. A task that the block starts does not join the transaction.
- Use httpx2, not httpx. The last stable httpx is 0.28.1 (December 2024).
  Pydantic maintains httpx2, with the same API.
- Only one layer retries an external call: the job queue. A retry in the
  client multiplies with the retries of the queue.
- A test gives `HttpClientFactory` a `MockTransport`. The factory then turns
  off the proxies of the environment, thus no test request goes out of the
  process.
- The memory backend has no rollback. Do the test of a rollback on SQLite.
  In a test, give the handler, the bus and the adapters the same `Database`.
- A different server can listen on port 3000. Run a live test with
  `uv run <pkg>-serve --port 3010`, and never stop a process that you did not
  start.
- Docker Desktop can refuse ghcr.io. The Dockerfile copies uv from
  `astral/uv` on Docker Hub. The free Chainguard Python image has only
  `latest`: pin it by digest, and test that Python in CI.
- `ruff format --check .` also examines the Python blocks of Markdown files.
  The pre-commit hook must format staged `*.md` files too, or CI fails on a
  tutorial block.
- In zsh, an unquoted variable does not split into words. Use `xargs` or an
  array for a list of files.

## Scripts

Run them with `uv run <skill>/scripts/<name>.py`. Each one prints its usage
with `--help`.

| Script | Purpose |
|---|---|
| `audit.py <dir>` | Examines the layout, the imports and the names. Exit 1 on a FAIL |
| `new_module.py <dir> <module> <entity> [--dry-run]` | Writes a feature module with its tests |
| `copy_platform.py <dir> [--only a,b] [--dry-run]` | Copies the platform modules and the test support of the reference |

## References

| File | Read it when |
|---|---|
| [references/layout.md](references/layout.md) | You add a file, a folder or an import, or place an algorithm |
| [references/recipes.md](references/recipes.md) | You write a controller, a port, an adapter, a migration, a listener, a job, auth or a rate limit |
| [references/bustan-api.md](references/bustan-api.md) | You use a bustan API: providers, lifecycle, auth, binding, errors, OpenAPI, testing |
| [references/testing.md](references/testing.md) | You write or change a test |
| [references/tooling.md](references/tooling.md) | You change hooks, CI, the release, Dependabot, the Dockerfile or the docs |
