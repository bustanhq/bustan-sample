# 10. Trade-offs and extensions

## What you learn

- The limits of this design, and what you would change at a larger scale.
- The gaps in bustan 2.0.3 that the code works around.
- How to build a full feature alone, with all the layers of this tutorial.

## Concepts

### The limits, and the next step for each

| Limit | Why it is acceptable here | The next step |
|---|---|---|
| SQLite on one host | One file, no server, shared by processes on one host | A PostgreSQL adapter for each storage port; the ports do not change |
| One connection for each process | Simple and correct. A transaction keeps it, so units of work are short | A connection pool in the database adapter, with the transaction kept on its connection |
| One mail provider | Resend accepts an idempotency key, thus a retry sends one email | An adapter for each other provider. A provider with no idempotency key brings back the duplicate case |
| No `traceparent` on an external call | bustan 2.0.3 has no public function that gives it. The correlation id joins the logs | Send `traceparent` when bustan exports it |
| No circuit breaker for external APIs | The job backoff and the failed jobs limit the load on a provider that is down | A breaker in `platform/http` for a call in the request path |
| The idempotency keys stay in the table | One row for each user and each kind of work | A scheduled purge of the keys that are older than the longest retry window |
| The memory backend runs one process and has no rollback | It is for development and tests. Its transaction still defers the events and the jobs | Use SQLite or a database server in each deployment |
| Two applications in one process share the rate-limit storage | The server and the tests run one at a time | A storage that bustan can inject at startup |
| No refresh token | A login each 15 minutes is acceptable for a sample | Refresh tokens with rotation, kept like the revocation list |
| English repeat phrases only | The grammar is small and testable | A model adapter behind `RecurrenceParser` |

The pattern repeats: each limit is behind a port or a platform module, so the
next step is a new adapter or a new provider, not a rewrite.

### Gaps in bustan 2.0.3

The code works around these. They are filed upstream. To file a new one, obey
[Report a bustan issue, or send a fix](../how-to/report-a-bustan-issue.md),
then add a row here:

| Issue | Gap | The work-around in this code |
|---|---|---|
| [#414](https://github.com/bustanhq/bustan/issues/414) | `create_test_module(imports=...)` does not accept a dynamic module in its type hints | Test roots are written with `@Module` |
| [#415](https://github.com/bustanhq/bustan/issues/415) | An override cannot add a provider that no module binds | Module tests import `ConfigModule.for_root(...)` in their root |
| [#416](https://github.com/bustanhq/bustan/issues/416) | The test response has no `raise_for_status()` | The export compares `status_code` |
| [#417](https://github.com/bustanhq/bustan/issues/417) | `ConfigModule.for_root()` reads the environment at import time | `conftest.py` sets the environment first; tests override `ConfigService` |
| [#418](https://github.com/bustanhq/bustan/issues/418) | An unhandled exception is logged as plain text | Log tests skip lines that are not JSON |

### Rules that you now know

- A feature is a module with `api/`, `listeners/`, `jobs/`, `application/`,
  `domain/` and `infra/`. Dependencies point inward to the domain.
- A module shows only its public names in `__init__.py`.
- Each outside thing is a port with adapters. Storage ports have a memory and
  an SQLite adapter, and a contract test.
- A listener subscribes and a job registers in its own `on_module_init`.
- An event goes out in the transaction of its data. Work that must happen one
  time keeps an idempotency key.
- A schema change is a new migration, never an edit of an old one.
- The OpenAPI document, the hooks and CI keep the code and its description in
  agreement.

## The capstone: projects

Build a `projects` module alone. A user groups tasks into projects. Use this
list; each item points to the chapter that taught it.

1. **Domain (ch. 4).** A `Project` entity with an owner, a name (1 to 100
   characters) and `created_at`. A `ProjectRepository` port with `save`, `get`,
   `find` and `remove`, each with the owner id.
2. **Adapters (ch. 5).** `InMemoryProjectRepository` and
   `SqliteProjectRepository` with migration 1. A `FactoryProvider` in
   `projects_module.py`. A contract test for both.
3. **Use cases (ch. 3).** `create_project_command.py`,
   `get_project_query.py`, `list_projects_query.py`, `delete_project_command.py`.
4. **API (ch. 3, 6).** `ProjectsController` at `/projects` with `@Auth("bearer")`,
   schemas, an error filter, and `@Api...` decorators. 404 for the projects of
   others.
5. **A link to tasks (ch. 5).** Add `project_id` to `Task`: a migration 2 of
   the tasks table, a field in the schemas, and a filter `?project_id=` on
   `GET /tasks`. The tasks module must not import the internals of projects:
   keep only the id, as tasks keeps only the owner id.
6. **An event (ch. 7).** When a project is deleted, publish `ProjectDeleted`
   in the transaction of the delete. In the tasks module, a listener removes
   the project id from its tasks. A second run of that listener changes
   nothing, so it needs no idempotency key.
7. **A schedule (ch. 7).** Each night at 02:00 UTC, a job writes the number of
   projects of each user to the log.
8. **Tests (ch. 8).** Domain, contract, handler, listener and HTTP tests, on
   both backends.
9. **Ship (ch. 9).** Run `uv run bustan-sample-openapi`, all checks, and a
   container run on SQLite. Add a line to `CHANGELOG.md` under `[Unreleased]`.

When each test passes on both backends and you can explain each file to a
colleague, you have mastered the design of this repository.

## Check yourself

1. Which file changes first if the service moves from SQLite to PostgreSQL?
2. Why does the tasks module keep only `project_id`, and not a `Project`?
3. A listener charges a card. Which pattern of chapter 7 does it need, and
   what risk remains?
