# 4. The domain

## What you learn

- What an entity is, and how it keeps its own rules.
- Why the domain gets the time as an argument.
- How a pure function holds a business algorithm.
- What a port is, and why the domain defines it.

## Concepts

### Entities keep their rules

`Task` in `modules/tasks/domain/task.py` is an **entity**: it has an identity
(`id`) that stays the same while its other values change. The entity does not
let a caller put it in a state that breaks a rule:

- `Task.create()` and `rename()` strip the title and refuse an empty or long one.
- `reschedule(None)` is refused for a recurring task, because a recurring task
  must have a due date.
- Each change sets `updated_at`.

The rules are in one place. A handler, a listener and a job all go through
the same methods, so no path can skip a rule.

### The time is an argument

`Task.create(..., now)` and `task.rename(title, now)` take the time from the
caller. The domain never calls `datetime.now()`. The application layer gets
the time from the injected `Clock`. In tests, `FixedClock` gives a known time,
so a test can say "the task was created at 09:00" and be right each time.

### A pure function for an algorithm

`domain/recurrence.py` holds `RecurrenceRule` and `next_due_on(rule, after)`.
`next_due_on` is a **pure function**: the same inputs always give the same
output, and it reads no clock, no file and no network. That makes the tricky
cases easy to state and to test:

| Rule | Due on | Next |
|---|---|---|
| every month | 2026-01-31 | 2026-02-28 (the last day of a short month) |
| every 2 weeks on Monday | 2026-02-04 (a Wednesday) | 2026-02-16 |
| every year | 2028-02-29 | 2029-02-28 |

The entity uses it in `next_occurrence()`, and `UpdateTaskHandler` saves the
next task when a recurring task becomes done.

### Ports

The domain needs to store tasks and to parse repeat phrases, but it must not
know how. So it defines **ports**: abstract classes that say what it needs.

```python
class TaskRepository(ABC):
    @abstractmethod
    async def get(self, owner_id: UUID, task_id: UUID) -> Task | None: ...
```

`TaskRepository` and `RecurrenceParser` are ports. The `infra/` folder gives
the implementations (chapter 5). The methods are `async`, because an
implementation can wait for a database or a model on the network.

### Where an algorithm goes

| The algorithm | Put it in |
|---|---|
| A business rule of one module, with no I/O | `domain/`, as a pure function or a method |
| A method that you can replace, or that uses a library, a service or a model | a port in `domain/`, an adapter in `infra/` |
| Steps that read or write stored data | `application/`, with the calculation in `domain/` |
| A shared service that needs configuration, state or the clock | `platform/` |

The repeat phrase shows two of these. The rules of recurrence are pure, so
they are in `domain/recurrence.py`. Turning "every 2 weeks on Monday" into a
rule is a method that you could replace (a small grammar today, a language
model tomorrow), so it is a port with an adapter.

## Try it

1. Run the domain tests only:

   ```bash
   uv run pytest -q tests/bustan_sample/modules/tasks/domain
   ```

2. Open `tests/bustan_sample/modules/tasks/domain/test_recurrence.py`. Add a
   row to the table of `test_next_due_on`: a daily rule over the end of a
   year (`date(2026, 12, 31)` gives `date(2027, 1, 1)`). Run the tests again.

3. See that a rule has one source. In `domain/task.py`, set
   `TITLE_MAX_LENGTH = 5`, and run all the tests. Domain tests fail, and so do
   HTTP tests, because `api/task_schemas.py` reads the same constant for the
   400 answer and for the OpenAPI document. Then undo the change with
   `git checkout -- src`.

4. Search the domain for imports:

   ```bash
   grep -rn '^from\|^import' src/bustan_sample/modules/*/domain
   ```

   You see only the standard library and the domain itself.

## Why it is built this way

- **The domain imports nothing.** No bustan, no Pydantic, no database. The
  rules then run in a plain test in milliseconds, and a change of framework
  or storage does not touch them.
- **Rules in the entity, not in the handler.** A handler that checks a rule
  works only for its own path. The entity is the one place that each path
  must go through.
- **A port for each outside thing.** The domain says what it needs in its own
  words. The cost is one extra class for each dependency; the gain is that
  the dependency can change without a change to the rules.

## Check yourself

1. Why does `Task.create` take `now` and not call `datetime.now()`?
2. Is the parser of repeat phrases in the domain? Why or why not?
3. A rule says "a done task cannot change its title". Where does it go?

Next: [5. Ports, adapters and storage](05-ports-adapters-and-storage.md).
