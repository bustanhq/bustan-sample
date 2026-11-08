# 3. Follow one request

## What you learn

- The layers of a feature module, and what each one does.
- How bustan binds and validates a request.
- How a domain error becomes an HTTP error with one shape for the whole API.

## Concepts

### The layers

Each feature module has the same folders:

| Folder | Job |
|---|---|
| `api/` | HTTP: controllers, request and response schemas, error filters |
| `application/` | One use case in each file: a command (changes data) or a query (reads data) |
| `domain/` | The rules of the business: entities, values, errors, ports |
| `infra/` | The code that talks to the outside: storage, parsers |
| `listeners/` | Handlers of events (chapter 7) |
| `jobs/` | Background jobs (chapter 7) |

The dependencies go in one direction: `api/` calls `application/`, which
calls `domain/`. `infra/` implements what `domain/` asks for. `domain/` imports
nothing from the other folders, nothing from bustan, and no library.

### One request, step by step

Follow `POST /tasks` with the body `{"title": "pay rent"}`:

1. **Routing and policy.** bustan finds `TasksController.create_task`.
   `@Auth("bearer")` on the controller means that a guard checks the token
   first. Without a valid token, the request stops here with 401 (chapter 6).
2. **Binding.** The parameter `payload: CreateTaskRequest` is a Pydantic
   model, so bustan reads the JSON body into it and validates it. A blank
   title, an unknown field (`extra="forbid"`) or a bad date gives 400 before
   your code runs. Path and query values convert from their type hints:
   `task_id: UUID` turns `not-a-uuid` into 400.
3. **The controller.** It does no business work. It makes a
   `CreateTaskCommand` and gives it to `CreateTaskHandler`.
4. **The handler.** In `application/create_task_command.py`, it parses the
   repeat phrase, asks the domain to make a `Task`, and saves it through the
   `TaskRepository` port.
5. **The domain.** `Task.create()` strips the title, checks its length, and
   checks that a recurring task has a due date. If a rule fails, it raises
   `InvalidTaskError`.
6. **The response.** The controller turns the `Task` into a `TaskResponse`
   and returns `HttpResponse.json(..., status_code=201, headers={"location": ...})`.
   A plain `dict` would give 200; `None` would give 204.

### One shape for each error

The domain raises its own errors, such as `TaskNotFoundError`. It does not
know about HTTP. `api/task_errors_filter.py` catches those errors and turns
each into a bustan HTTP error (`NotFoundException`, `BadRequestException`).
The bustan filter then writes an RFC 9457 **problem details** body:

```json
{"type":"https://bustan.dev/problems/not-found","title":"Not Found","status":404,
 "detail":"no task with id 00000000-0000-0000-0000-000000000000",
 "instance":"/tasks/00000000-0000-0000-0000-000000000000","code":"not-found"}
```

Validation errors, auth errors and rate-limit errors have the same shape. A
client needs one error handler for the whole API.

## Try it

1. Start the server and get a token (chapter 1). Send a bad body:

   ```bash
   curl -si -X POST http://127.0.0.1:3000/tasks \
     -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' \
     -d '{"title":"   ","owner":"me"}'
   ```

   Read the `errors` array: it names each field and the problem.

2. Ask for a task that does not exist, and read the problem details:

   ```bash
   curl -si http://127.0.0.1:3000/tasks/00000000-0000-0000-0000-000000000000 \
     -H "authorization: Bearer $TOKEN"
   ```

3. Look at the server terminal. Each request writes one JSON record with the
   method, the path, the handler, the outcome, the duration and a
   `correlation_id`. That is `platform/request_logging`, an interceptor that
   wraps each handler.

4. Read the four files of the request in order:
   `api/tasks_controller.py`, `application/create_task_command.py`,
   `domain/task.py`, `infra/in_memory_task_repository.py`.

## Why it is built this way

- **Thin controllers.** A controller only translates: HTTP in, command or
  query, HTTP out. All decisions are in `application/` and `domain/`, where a
  test can reach them without HTTP.
- **One file for each use case.** `create_task_command.py` holds the command
  dataclass and its handler. You find a use case by its name, and a change to
  one use case touches one file. There is no command bus: the controller asks
  for the handler it needs, so the call is easy to follow.
- **Schemas at the edge, rules in the domain.** The Pydantic schemas give fast
  400 answers and the OpenAPI document. The domain checks its own rules again,
  because a listener or a job can call the same handler with no HTTP.

## Check yourself

1. Which layer must change if the title limit changes from 200 to 300?
2. Why does `CreateTaskHandler` not return an HTTP response?
3. What does the client see for a domain error and for a validation error?

Next: [4. The domain](04-the-domain.md).
