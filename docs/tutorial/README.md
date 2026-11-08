# The bustan-sample tutorial

This tutorial takes you from your first request to the design decisions of a
production service. Each chapter adds one layer of concepts on top of the
previous one, and each chapter uses the real code of this repository. Nothing
here is a toy example that you must forget later.

Read the chapters in sequence. Each one has the same parts:

- **What you learn**: the concepts of the chapter.
- **Concepts**: the explanation, from the simple idea to the details.
- **Try it**: steps to do on your computer. Do them; reading is not enough.
- **Why it is built this way**: the decision behind the code, and its cost.
- **Check yourself**: questions. If you cannot answer one, read the chapter again.

## The path

| Level | Chapter | You learn |
|---|---|---|
| Novice | [1. Run it](01-run-it.md) | Start the API, call it, read its document, run the tests |
| Novice | [2. Modules and injection](02-modules-and-injection.md) | How bustan builds an application from modules and providers |
| Novice | [3. Follow one request](03-follow-one-request.md) | The path of a request through the layers, validation and errors |
| Practitioner | [4. The domain](04-the-domain.md) | Entities, rules, pure functions, and why the domain imports nothing |
| Practitioner | [5. Ports, adapters and storage](05-ports-adapters-and-storage.md) | Memory and SQLite behind one port, migrations, contract tests |
| Practitioner | [6. Identity and security](06-identity-and-security.md) | Tokens, password hashes, auth on routes, ownership, rate limits |
| Advanced | [7. Events, jobs and schedules](07-events-jobs-and-schedules.md) | Decoupled modules, background work, retries, cron with a lock |
| Advanced | [8. Testing](08-testing.md) | The kinds of tests, both backends, fakes, background work |
| Advanced | [9. Operate and ship](09-operate-and-ship.md) | Configuration, probes, logs, the container image, CI and releases |
| Master | [10. Trade-offs and extensions](10-trade-offs-and-extensions.md) | The limits of the design, and a capstone feature that you build alone |

## What you need

- Python 3.13 or a newer version, and [uv](https://docs.astral.sh/uv/).
- git, and `curl` for the examples.
- Docker, for chapter 9 only.
- Basic Python: classes, `async`/`await`, type hints. You do not need to know
  bustan, NestJS or any web framework.

The repository is <https://github.com/bustanhq/bustan-sample>. The framework
is [bustan](https://github.com/bustanhq/bustan), and its own docs are at
<https://bustan.dev>.
