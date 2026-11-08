# 8. Testing

## What you learn

- The kinds of tests in this project, and what each kind proves.
- Why the test configuration must be in the environment before the import.
- How one HTTP test runs on two backends.
- How to test work that happens in the background.

## Concepts

### The kinds of tests

The tests mirror `src/`: the test of `src/bustan_sample/modules/tasks/domain/task.py`
is `tests/bustan_sample/modules/tasks/domain/test_task.py`.

| Kind | Proves | Speed |
|---|---|---|
| Domain | The rules, with many cases in a table | Fastest: plain function calls |
| Port contract | Both adapters of a port behave the same | Fast: memory and a temporary SQLite file |
| Application handler | A use case with real memory adapters and fakes | Fast: no HTTP |
| Listener and job | Subscribe, register, schedule, react | Fast |
| HTTP | The routes: status, body, headers, auth, problem details | Slower: the full application |
| Module wiring | A module compiles with only its declared imports | Fast |
| OpenAPI | `openapi.yaml` agrees with the code | One export |

Most tests are at the top of the table. An HTTP test proves the wiring; it is
the wrong place to test fifty cases of a rule.

### Configuration before the import

`ConfigModule.for_root()` reads the environment when Python imports
`app_module.py`, not when the application starts. So `tests/conftest.py` sets
the test values at the top, before anything imports the application:

```python
os.environ["IDENTITY_JWT_SECRET"] = "a-test-secret-that-is-longer-than-32-characters"
os.environ["DATABASE_BACKEND"] = "memory"
os.environ["JOBS_RETRY_DELAY_SECONDS"] = "0"
```

To give one test a different configuration, the `client` fixture overrides
`ConfigService` itself instead of the environment.

### One test, two backends

The `client` fixture has `params=["memory", "sqlite"]`. For `sqlite`, it
overrides `ConfigService` with `DATABASE_BACKEND=sqlite` and a new file in
`tmp_path`. Each test that uses `client` runs two times. It also overrides:

- `Clock` with `FixedClock`, so times are known.
- The password hasher with a low-cost Argon2, so tests stay fast.
- `Mailer` with `RecordingMailer`, so a test can read the sent emails.

### Background work

A listener and a job run after the response. A test that checks their result
must wait for it, and a fixed sleep is slow and flaky. `tests/support/fakes.py`
has `wait_until(condition)`, which polls each 10 ms for 2 s:

```python
client.post("/identity/register", json=credentials)
wait_until(lambda: len(mailer.sent) == 1)
```

### Async without a plugin

The project has no async plugin for pytest. An async test runs its coroutine
itself:

```python
def test_something() -> None:
    async def scenario() -> None: ...

    asyncio.run(scenario())
```

## Try it

1. Run only the tests of one backend:

   ```bash
   uv run pytest -q -k "sqlite"
   ```

2. Write a contract test. In
   `tests/bustan_sample/modules/tasks/domain/test_task_repository.py`, add a
   test that saves two tasks of Ada and one of Bob, and checks that
   `find(ADA)` gives two. Run it, and see it pass on both adapters.

3. Write an HTTP test. In `tests/bustan_sample/modules/tasks/api/test_tasks_controller.py`,
   add a test that a task with `"repeat": "every Friday"` comes back with
   `"repeat": "every week on Friday"`. Use the `sign_up` fixture for the token.

4. Break the OpenAPI document on purpose: change the summary of a route in a
   controller, and run `uv run pytest -q tests/bustan_sample/test_openapi_export.py`.
   Then run `uv run bustan-sample-openapi` and the test again.

## Why it is built this way

- **Both backends in each HTTP test.** The memory backend is the default for
  developers; SQLite is what a deployment uses. Running both catches an
  adapter that drifts, at the price of about twice the HTTP test time, which
  is about one second here.
- **Fakes at the edges only.** The tests use the real handlers, the real
  domain and the real adapters. Only the clock, the hasher cost and the mailer
  are replaced, because they are slow, random or external.
- **The import mode.** `[tool.pytest]` uses `--import-mode=importlib`, so two
  modules can each have a file named `test_on_user_registered.py`, and
  `pythonpath = ["tests"]` makes `tests/support` importable as `support`.

## Check yourself

1. Why must `IDENTITY_JWT_SECRET` be set before the first import of the application?
2. Which tests would catch an SQLite adapter that sorts tasks differently?
3. Why is `wait_until` better than `time.sleep(1)`?

Next: [9. Operate and ship](09-operate-and-ship.md).
