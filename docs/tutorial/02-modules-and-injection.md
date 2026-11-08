# 2. Modules and injection

## What you learn

- What a provider is, and how constructor injection works.
- What a module is, and why its providers are private.
- How the root module puts the application together.
- When the lifecycle hooks run.

## Concepts

### Providers and injection

A **provider** is a class that bustan builds for you. You mark it with
`@Injectable()`, and you ask for what it needs in its `__init__`:

```python
@Injectable()
class CreateTaskHandler:
    def __init__(
        self, repository: TaskRepository, clock: Clock, parser: RecurrenceParser
    ) -> None: ...
```

You never write `CreateTaskHandler(...)` yourself. bustan reads the type hints,
finds a provider for each one, builds those first, and passes them in. This is
**constructor injection**. Its value is not convenience: it is that a class
never decides which implementation of a dependency it gets. A test, or a
different configuration, can give it a different one.

By default each provider is a **singleton**: one instance for the whole
application. `TasksController` and the tasks listener get the same
`CreateTaskHandler`.

### Modules

A **module** is a class with `@Module(...)` that groups providers:

```python
@Module(
    imports=[ClockModule, DatabaseModule, EventsModule, IdentityModule],
    controllers=[TasksController],
    providers=[...],
)
class TasksModule:
    pass
```

- `providers`: the classes that this module builds.
- `controllers`: the classes with HTTP routes.
- `imports`: other modules whose exported providers this module can use.
- `exports`: the providers that importing modules can use.

A provider is **private** to its module unless the module exports it. This is
what makes a module a boundary, and not only a folder. `JobsModule` exports
`JobQueue` and `JobScheduler`; it does not export `ScheduleLock`, so no
feature module can use the lock directly.

A module class is one instance in the graph. Two modules that import
`DatabaseModule` share the same `Database` provider, which is why the process
has one database connection.

A few modules are **global**: their exports are visible everywhere with no
import. `ConfigModule.for_root()` and `HealthModule.for_root()` are global,
because configuration and health are needed everywhere. Make a module global
only for that kind of reason.

### The root module

`src/bustan_sample/app_module.py` is the root. It has no providers of its
own. It only imports: the configuration, the health probes, the rate limits,
the platform modules that apply to all routes, and the two feature modules.
Read it now; it is short.

### Lifecycle hooks

A provider can have methods that bustan calls at fixed moments:

| Hook | When |
|---|---|
| `on_module_init` | At startup, first stage |
| `on_application_bootstrap` | At startup, second stage, before the first request |
| `before_application_shutdown` | At shutdown, first stage |
| `on_application_shutdown` | At shutdown, second stage |
| `on_module_destroy` | At shutdown, last stage |

Inside a stage, providers run in the order bustan built them, dependencies
first; shutdown runs in the reverse order. This project uses that order on
purpose. `Database` opens its connection in `on_module_init`, before any
adapter needs it, and closes it in `on_module_destroy`, after the job queue
has finished in `on_application_shutdown`.

## Try it

1. Open `src/bustan_sample/modules/tasks/tasks_module.py` and
   `src/bustan_sample/modules/tasks/__init__.py`. The `__init__.py` gives the
   public names of the module. Other modules import only these names.

2. Make the graph break on purpose. In `tasks_module.py`, remove
   `EventsModule` from `imports`, and run:

   ```bash
   uv run pytest -q tests/bustan_sample/test_app_module.py
   ```

   Read the error. bustan names the class, the parameter and the module that
   cannot see the provider. It refuses to build the application at startup,
   not on the first request that needs the provider.

3. Put `EventsModule` back, and run the test again.

4. Find a hook: open `src/bustan_sample/platform/jobs/in_memory_job_queue.py`.
   The workers start in `on_application_bootstrap`, and they drain and stop in
   `on_application_shutdown`.

## Why it is built this way

- **Feature modules and platform modules.** Each feature (tasks, identity) is
  a module in `src/bustan_sample/modules/`. Each shared service with no routes
  (clock, database, events, idempotency keys, jobs, mail, health, rate limits,
  request logs) is a module in `src/bustan_sample/platform/`. The platform never imports a
  feature. A feature can import the platform, and only the public names of
  another feature.
- **Explicit imports over global modules.** A feature imports `ClockModule`
  instead of a global clock. When you read a module, you see all it depends
  on. An import error then tells you that a dependency is missing, which is
  information, not noise.
- **One package.** Some house rules put each area in its own top-level
  package. bustan modules use relative imports between their parts, so one
  package `bustan_sample` holds all of them.

## Check yourself

1. Why does a module not see the providers of a module that it does not import?
2. Two modules import `ClockModule`. How many `Clock` instances exist?
3. Why must the database close after the job queue stops?

Next: [3. Follow one request](03-follow-one-request.md).
