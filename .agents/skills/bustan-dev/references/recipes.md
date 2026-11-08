# Recipes

Each recipe shows the form that the reference uses. The full files are in
<https://github.com/bustanhq/bustan-sample/tree/main/src/bustan_sample>.

## Command or query

```python
@dataclass(frozen=True, slots=True)
class CreateTaskCommand:
    owner_id: UUID
    title: str


@Injectable()
class CreateTaskHandler:
    def __init__(self, repository: TaskRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def execute(self, command: CreateTaskCommand) -> Task:
        task = Task.create(command.owner_id, command.title, self._clock.now())
        await self._repository.save(task)
        return task
```

A query that gives pages gets `limit + 1` items from the repository, and
returns the page and the next offset.

## Controller

```python
@UseFilters(TaskErrorsFilter())
@Controller("/tasks")
@Auth(STRATEGY)
@ApiTags("tasks")
@ApiBearerAuth()
class TasksController:
    def __init__(self, create_task: CreateTaskHandler) -> None:
        self._create_task = create_task

    @Post("/")
    @ApiOperation(summary="Add a task")
    @ApiResponse(status=201, description="The new task", schema=TaskResponse)
    @ApiResponse(status=400, description="The body is not valid")
    async def create_task(self, user: User, payload: CreateTaskRequest) -> HttpResponse:
        task = await self._create_task.execute(CreateTaskCommand(user.user_id, payload.title))
        return HttpResponse.json(
            TaskResponse.from_task(task).to_json(),
            status_code=201,
            headers={"location": f"/tasks/{task.id}"},
        )
```

- `User = Annotated[AuthenticatedUser, CurrentUser()]`.
- Schemas: `model_config = ConfigDict(extra="forbid")`. A response model has
  `from_<entity>()` and `to_json()` (`model_dump(mode="json")`).
- For PATCH, `payload.model_fields_set` tells a field set to `null` from a
  field that the client did not send.
- A list with pages adds `link: </tasks?limit=50&offset=50>; rel="next"`.

## Error filter

```python
class TaskErrorsFilter(ExceptionFilter):
    exception_types = (TaskNotFoundError, InvalidTaskError)

    def __init__(self) -> None:
        self._problems = ProblemDetailsExceptionFilter()

    async def catch(self, exc: Exception, context: ExecutionContext) -> HttpResponse:
        if isinstance(exc, TaskNotFoundError):
            return await self._problems.catch(NotFoundException(str(exc)), context)
        return await self._problems.catch(BadRequestException(str(exc)), context)
```

## Port with two adapters

```python
class TaskRepository(ABC):
    @abstractmethod
    async def save(self, task: Task) -> None: ...
    @abstractmethod
    async def get(self, owner_id: UUID, task_id: UUID) -> Task | None: ...
```

- A read or a removal takes the owner id, thus no caller can get the data of
  a different user.
- The memory adapter stores and returns copies (`dataclasses.replace`).
- The SQLite adapter:

```python
_V1 = """
CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, ...);
"""
MIGRATIONS = (Migration(1, "create the table tasks", _V1),)


@Injectable()
class SqliteTaskRepository(TaskRepository):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def on_module_init(self) -> None:
        await self._database.migrate("tasks", MIGRATIONS)
```

- `Database`: `execute()`, `fetch_one()`, `fetch_all()` (also for
  `RETURNING`), `execute_script()`, `transaction()`, `after_commit()`,
  `after_rollback()`, `migrate()`. Keep times with `to_text()` and
  `from_text()`.
- An adapter never opens a connection or takes one as an argument. In a
  transaction, each `Database` call of the same task joins it.
- Order a list by `created_at, rowid`, the same as the memory adapter.
- A unique column that a race can break: catch `sqlite3.IntegrityError` and
  raise the domain error.
- The binding in `<module>_module.py`:

```python
def _task_repository(database: Database) -> TaskRepository:
    if database.is_sqlite:
        return SqliteTaskRepository(database)
    return InMemoryTaskRepository()


FactoryProvider(provide=TaskRepository, use_factory=_task_repository, inject=(Database,))
```

## Unit of work

The writes of one command commit together, or none:

```python
async def execute(self, command: RegisterUserCommand) -> User:
    ...
    password_hash = await self._hasher.hash(command.password)  # slow work first
    user = User.create(email, password_hash, self._clock.now())
    async with self._database.transaction():
        await self._users.save(user)
        await self._events.publish(UserRegistered(user.id, user.email, user.created_at))
    return user
```

- With SQLite, the block is one `BEGIN IMMEDIATE` transaction. A nested
  `transaction()` joins the outer one.
- The repositories, the job queue and the event bus join the transaction of
  their task. A job or an event of the block starts after the commit. A
  rollback drops it.
- Do slow work (a hash, a parser, a network call) before the block. The
  block keeps the one connection of the process.
- In the block, never wait for a different task that uses the database.
  `execute_script()` and `migrate()` refuse to run in a block.
- The memory backend has no rollback. Its block only defers the events and
  the jobs.

## Event and listener

```python
@dataclass(frozen=True, slots=True)
class UserRegistered:  # domain/events.py
    user_id: UUID
    email: str
    occurred_at: datetime


@Injectable()
class OnUserRegistered:  # listeners/on_user_registered.py
    def __init__(
        self,
        events: EventBus,
        create_task: CreateTaskHandler,
        database: Database,
        keys: IdempotencyKeys,
    ) -> None:
        self._events = events
        self._create_task = create_task
        self._database = database
        self._keys = keys

    def on_module_init(self) -> None:
        self._events.subscribe(UserRegistered, self.handle)

    async def handle(self, event: UserRegistered) -> None:
        async with self._database.transaction():
            if not await self._keys.add(f"tasks.starter_task:{event.user_id}"):
                return
            await self._create_task.execute(CreateTaskCommand(event.user_id, "Add your first task"))
```

The publisher calls `await events.publish(UserRegistered(...))` in the
transaction that saves the data (see "Unit of work"). With SQLite, each
delivery is a `DeliverEvent` row in the table `jobs`, in that transaction:
the job table is the transactional outbox. Pydantic writes the event as JSON,
thus each field must be a type that pydantic knows. A delivery can run two
times: the listener gives the same result each time, or keeps a key.

## Job and schedule

```python
@dataclass(frozen=True, slots=True)
class SendWelcomeEmailJob:  # JSON fields only: str, int, float, bool
    user_id: str
    email: str


@Injectable()
class SendWelcomeEmailHandler:
    def __init__(self, jobs: JobQueue, mailer: Mailer, keys: IdempotencyKeys) -> None:
        self._jobs = jobs
        self._mailer = mailer
        self._keys = keys

    def on_module_init(self) -> None:
        self._jobs.register(SendWelcomeEmailJob, self.run, max_attempts=5)

    async def run(self, job: SendWelcomeEmailJob) -> None:
        key = f"identity.welcome_email:{job.user_id}"
        if await self._keys.contains(key):
            return
        await self._mailer.send(job.email, SUBJECT, BODY)
        await self._keys.add(key)  # after the send: a failed send leaves no key
```

For a schedule, inject `JobScheduler` too, and call
`self._scheduler.schedule("identity.purge_revoked_tokens", "*/10 * * * *", PurgeRevokedTokensJob)`
in `on_module_init`. The class name of a job is its type in the SQLite table:
keep it unique, and keep it after a release.

## Idempotency key

Import `IdempotencyModule` and inject `IdempotencyKeys` for work that must
happen one time. Name each key `<module>.<work>:<id>`.

| Work | Pattern | Result |
|---|---|---|
| In the database | In `transaction()`: `if not await keys.add(key): return`, then the work | Exactly one time. A failed work rolls back its key |
| Outside the database (email, HTTP call) | `if await keys.contains(key): return`, the work, then `await keys.add(key)` | At least one time. Two times only if the process stops between the work and `add()` |

Never keep a transaction open during a network call. A key is not
necessary for work that gives the same result each time (a set, a delete).

## External API

An adapter of a port owns one client. Import `HttpModule` in the module that
binds the port.

```python
class ResendMailer(Mailer):  # platform/mail/resend_mailer.py
    def __init__(self, http: HttpClientFactory, api_key: str, sender: str) -> None: ...

    async def on_module_init(self) -> None:
        self._client = self._http.make(
            "resend", "https://api.resend.com", headers={"Authorization": f"Bearer {self._api_key}"}
        )

    async def on_module_destroy(self) -> None:
        await self._client.aclose()

    async def send(self, to, subject, body, *, idempotency_key=None) -> None:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
        message = {"from": self._sender, "to": [to], "subject": subject, "text": body}
        response = await self._client.request("POST", "/emails", json=message, headers=headers)
        raise_for_response("resend", response)  # after the statuses with a special meaning
```

- `HttpClient.request()` sends the correlation id, writes one log record
  (service, method, path, status, duration) and changes a timeout or a
  network error into `ExternalServiceError(retryable=True)`.
- `raise_for_response()`: 408, 425, 429 and 5xx are retryable, each other
  4xx is permanent. `retry_after` comes from the `Retry-After` header.
- A call that changes something runs in a job. The client never retries.
  The job handler decides:

```python
except ExternalServiceError as exc:
    if not exc.retryable:
        raise PermanentJobError(str(exc)) from exc
    if exc.retry_after is not None:
        raise RetryJobLater(exc.retry_after, str(exc)) from exc
    raise
```

- A configuration key selects the adapter (`MAIL_BACKEND=log|resend`), with
  a `FactoryProvider`. A model validator in `app_settings.py` stops the start
  if the selected adapter has no credentials.
- Never put an external API in readiness. Never log a header, a query or a
  body.

## Auth

The identity module of the reference gives `BearerAuthenticator`, the
registry and `CurrentUser`:

```python
def _authenticators(bearer: BearerAuthenticator) -> dict[str, object]:
    return {STRATEGY: bearer}


FactoryProvider(
    provide=AUTHENTICATOR_REGISTRY, use_factory=_authenticators, inject=(BearerAuthenticator,)
)
# exports=[AUTHENTICATOR_REGISTRY]

CurrentUser = create_param_decorator(_current_user, name="CurrentUser")
# _current_user reads context.request.state.principal, which the policy guard sets.
```

A module with `@Auth("bearer")` routes imports the identity module. The
principal is an object with `id`, `roles` and `permissions`.

## Rate limit and probes

```python
ThrottlerModule.for_root(ttl=60, limit=300, storage=THROTTLER_STORAGE)
HealthModule.for_root(check_timeout=2.0)
```

`@RateLimit(limit=10, window="1m")` on a public route that a caller can
abuse (login, register). The probes are not throttled. A readiness check
goes in `platform/health`, never in liveness.
