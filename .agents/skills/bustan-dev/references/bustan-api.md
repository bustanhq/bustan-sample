# bustan API facts

Facts of bustan 2.0.3 that the recipes depend on. The supported surface is
`bustan`, `bustan.errors` and `bustan.testing`. The source and the docs are in
`~/Bustan/bustan` (`docs/reference/api.md`, `docs/tutorials/`, `docs/how-to/`).

## Providers

| Form | Use |
|---|---|
| `SomeClass` with `@Injectable()` | DI makes it from the annotations of `__init__` |
| `ClassProvider(provide=Port, use_class=Adapter)` | one adapter for a port |
| `FactoryProvider(provide=Port, use_factory=f, inject=(A, B))` | a function selects or builds the value. `inject` is a tuple, also for one token |
| `ValueProvider(provide=Token, use_value=v)` | a value made before. No hooks run on it |

A module: `@Module(imports=[...], controllers=[...], providers=[...], exports=[...])`.
A provider is private to its module unless the module exports it. A module
class is one instance in the graph, thus two importers share its providers.
`ConfigModule.for_root()` and `HealthModule.for_root()` are global.

## Lifecycle

- Hooks: `on_module_init`, `on_application_bootstrap`,
  `before_application_shutdown(signal)`, `on_application_shutdown(signal)`,
  `on_module_destroy`. Each can be async.
- `create_app()`: the hooks run in the ASGI lifespan (server start, or
  `with AsgiTestClient(app)`). `create_app_context()`: `await context.init()`
  and `await context.close()`.
- Startup builds each singleton, dependencies first. Hooks run in that order.
  Teardown runs in the reverse order.
- Hooks run only on instances that bustan made, not on `use_value`.
- Graceful shutdown: readiness goes down, requests drain (10 s), then the
  teardown hooks.

## Routing and binding

- `@Controller("/tasks")` with `@Get("/")`, `@Post("/")`, `@Patch("/{task_id}")`,
  `@Delete(...)`. `@Post("/")` is the path `/tasks`, not `/tasks/`.
- A path parameter binds by name. A scalar query parameter binds by name.
  One Pydantic model parameter binds the JSON body and is validated (400).
- Conversion is `annotation(raw)`: `UUID`, `int`, a `StrEnum` work. A
  `ValueError` gives 400.
- A `dict`, a `list` or a dataclass gives JSON 200. `None` gives 204.
  `HttpResponse.json(body, status_code=..., headers=...)` for other statuses.
- `create_param_decorator(factory, name=...)` makes an argument marker:
  `Annotated[T, Marker()]`. The factory gets `(data, context)`.

## Errors

`bustan.errors` has `BadRequestException`, `UnauthorizedException`,
`NotFoundException`, `ConflictException` and more. Each gives RFC 9457
problem details with `type`, `title`, `status`, `detail`, `instance`, `code`.
An `ExceptionFilter` with `exception_types` can delegate to
`ProblemDetailsExceptionFilter().catch(http_error, context)` (async).

## Auth

- `AUTHENTICATOR_REGISTRY`: a `dict[str, authenticator]`. An authenticator has
  `async def authenticate(context) -> principal | None`. `None` gives 401 with
  `WWW-Authenticate`.
- `@Auth(name)` on a controller or a method, `@Public()` on a method to open
  it, `@Roles(...)`, `@Permissions(...)`.
- The policy guard puts the principal on `context.request.state.principal`.
- A module with an `@Auth` route must see the registry: import the module
  that exports it.

## Configuration

`ConfigModule.for_root(env_file=".env", validation_schema=Settings)` reads
`os.environ` and the file when it is called, which is when Python imports the
root module. The environment overrides the file. The loader does not remove
quotes around a value. `ConfigService.get(key, default)` and
`get_or_throw(key)`.

## OpenAPI

`create_app(AppModule, swagger=SwaggerOptions(document_builder=DocumentBuilder()...add_bearer_auth(), path="/docs/api", swagger_ui_path="/docs/ui"))`.
Decorators: `@ApiTags`, `@ApiOperation(summary, description)`,
`@ApiResponse(status, description, schema)`, `@ApiBearerAuth()`.
`create_test_app()` does not take `swagger`: build the export with
`create_asgi_app()`.

## Testing

- `create_test_app(AppModule, provider_overrides={Token: value})`.
- `create_testing_module(Mod).override_provider(Token).use_value(v).compile()`,
  then `compiled.get(token)` from the root context, `snapshot_routes()`,
  `close()`.
- `AsgiTestClient(app)`: `get`, `post(json=...)`, `patch`, `delete`,
  `params=`, `headers=`, `follow_redirects=`. As a context manager it runs
  the lifespan on one loop in a thread, and background tasks continue
  between requests.

## Observability

- `bustan.observability.current_correlation_id()` gives the correlation id
  of the request in flight, or `None` (in a job, for example). Send it as
  `x-correlation-id` on an external call.
- bustan 2.0.3 exports no function that gives the `traceparent` of the
  request. `current_correlation()` is only in the module
  `bustan.observability.correlation`, outside `__all__`. Do not import it.
- `Logger(context).record(level, message, fields={...})` writes one JSON
  record. The framework adds the correlation id.

## Known issues (filed 2026-11-08)

To file a new issue, obey "When bustan is the problem" in SKILL.md. Then add
a row here, and remove the row when a release corrects the issue.

| Issue | Problem | Work-around |
|---|---|---|
| bustanhq/bustan#414 | `create_test_module(imports=...)` rejects `DynamicModule` in the types | Write the test root with `@Module` |
| bustanhq/bustan#415 | An override of a token that no module binds fails with a visibility error | Import the module that binds it (for example `ConfigModule.for_root`) in the test root |
| bustanhq/bustan#416 | `AsgiTestResponse` has no `raise_for_status()` | Compare `status_code` |
| bustanhq/bustan#417 | `ConfigModule.for_root()` reads the environment at import time | Set the test environment in `conftest.py` first. Override `ConfigService` for one test |
| bustanhq/bustan#418 | An unhandled exception is logged as plain text | Skip lines that are not JSON when a test parses the log |
