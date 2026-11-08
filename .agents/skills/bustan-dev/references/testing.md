# Testing

## Settings in pyproject.toml

```toml
[tool.pytest]
testpaths = ["tests"]
pythonpath = ["tests"]                 # tests/support is importable as support
addopts = ["--import-mode=importlib"]  # two modules can have test files with one name
```

The test folders mirror `src/<pkg>/` and have no `__init__.py`.
`tests/support/` is a package.

## conftest.py

1. Set the environment first, before an import of the application:
   `os.environ["IDENTITY_JWT_SECRET"] = "a-test-secret-..."`,
   `DATABASE_BACKEND=memory`, `JOBS_RETRY_DELAY_SECONDS=0`,
   `JOBS_POLL_SECONDS=0.01`. Import the root module inside the fixture.
2. Fixtures: `clock` (`FixedClock`), `mailer` (`RecordingMailer`), `client`,
   `sign_up`.
3. `client` has `params=BACKENDS` (`["memory", "sqlite"]`). It overrides
   `Clock`, the password hasher (`Argon2PasswordHasher.with_low_cost()`) and
   `Mailer`. For `sqlite`, it overrides `ConfigService` with the validated
   configuration and `DATABASE_SQLITE_PATH=tmp_path / "app.db"`.
4. `sign_up(email)` registers, logs in, waits for the background work of the
   registration, and returns the auth header.

## Kinds of tests

| Kind | Where | How |
|---|---|---|
| Domain | `tests/<pkg>/modules/<m>/domain/test_<entity>.py` | Pure calls with constant times. Many cases with `parametrize` |
| Port contract | `tests/<pkg>/modules/<m>/domain/test_<port>.py` | `pytestmark = pytest.mark.parametrize("backend", BACKENDS)` and a context manager that gives the memory adapter or the SQLite adapter on `open_sqlite(tmp_path / "test.db")` |
| SQLite adapter | `tests/<pkg>/modules/<m>/infra/test_sqlite_<port>.py` | The behavior of SQLite only: data after a reopen, unique columns, two connections on one file |
| Application handler | `tests/<pkg>/modules/<m>/application/test_<request>_<kind>.py` | Make the handler directly with the memory adapters, `FixedClock` and fakes |
| Listener or job | `tests/<pkg>/modules/<m>/listeners/`, `.../jobs/` | Call `on_module_init()`, then publish or call `run()`. Use `memory_event_bus(database)` and `RecordingJobQueue`. For an idempotency key, call `handle()` or `run()` two times and count the result, on each backend |
| External API adapter | `tests/<pkg>/.../test_<name>_<adapter>.py` | `HttpClientFactory(httpx2.MockTransport(handler))`. Examine the request (method, URL, headers, JSON) and the retry decision for each status and for `httpx2.ReadTimeout`. No test calls the network |
| Rollback | The test of the handler or the adapter | On SQLite only: the memory backend has no rollback. Raise in the block, then examine that no row and no job stays |
| HTTP | `tests/<pkg>/modules/<m>/api/test_<name>_controller.py` | The `client` fixture. Status, body, headers, problem details, 401 for each protected route, 404 for the data of a different user |
| Module wiring | `tests/<pkg>/modules/<m>/test_<m>_module.py` | A test root with `@Module(imports=[ConfigModule.for_root(ignore_env_file=True, validation_schema=Settings), Mod])`, then `snapshot_routes()` |
| OpenAPI | `tests/<pkg>/test_openapi_export.py` | `main(["--check", ...]) == 0` |

## Async without a plugin

```python
def test_something() -> None:
    async def scenario() -> None: ...

    asyncio.run(scenario())
```

## Background work

Use `wait_until(lambda: condition)` from `tests/support/fakes.py`. It polls
each 10 ms for 2 s. Never sleep for a constant time. A worker of the SQLite queue
starts immediately on an enqueue in the same process, or after the commit of
the transaction of the enqueue.

Give the handler, the bus and the adapters one `Database`
(`memory_database()` or `open_sqlite()`). A bus with a different `Database`
does not see the transaction, and delivers before the commit.

## Logs

The bustan `Logger` writes one JSON object for each record to the logger
`bustan`. To examine a record, add a `logging.Handler` to
`logging.getLogger("bustan")` or use `caplog`, and skip the lines that are
not JSON.
