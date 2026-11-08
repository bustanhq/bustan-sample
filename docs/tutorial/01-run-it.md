# 1. Run it

## What you learn

- What this service does, and what bustan is.
- How to start the service and call it.
- Where the API is described, and how to run the tests.

## Concepts

**The service.** bustan-sample is an HTTP API for tasks. A person registers,
logs in, and gets a token. With the token, the person adds, lists, changes and
deletes their own tasks. A task can recur: "every 2 weeks on Monday" makes a
new task each time the old one is done.

**bustan.** bustan is a Python framework for APIs. It takes its design from
NestJS: you write small classes, you put them in modules, and the framework
builds the objects and connects them for you. The framework serves HTTP
through Starlette and uvicorn, which you will not touch directly.

**The application factory.** `src/bustan_sample/app_main.py` has one function
that makes the whole application: `create_asgi_app()`. The server, the tests
and the OpenAPI export all call it. Keep that in mind: there is one way to
build the application, and everything uses it.

## Try it

1. Get the code and install the dependencies:

   ```bash
   git clone https://github.com/bustanhq/bustan-sample.git
   cd bustan-sample
   uv sync
   ```

2. Make the local configuration. The service refuses to start without a
   secret for its tokens:

   ```bash
   cp .env.example .env
   uv run python -c 'import secrets; print(secrets.token_urlsafe(48))'
   ```

   Put the printed value in `.env` after `IDENTITY_JWT_SECRET=`.

3. Start the server. Keep this terminal open:

   ```bash
   uv run bustan-sample-serve --reload
   ```

   The server listens on <http://127.0.0.1:3000>. `--reload` starts it again
   after each change to a file in `src/`. If port 3000 is in use, add
   `--port 3010` and use that port below.

4. In a second terminal, register a user and log in:

   ```bash
   curl -s -X POST http://127.0.0.1:3000/identity/register \
     -H 'content-type: application/json' \
     -d '{"email":"ada@example.com","password":"correct horse battery"}'

   curl -s -X POST http://127.0.0.1:3000/identity/login \
     -H 'content-type: application/json' \
     -d '{"email":"ada@example.com","password":"correct horse battery"}'
   ```

   The second command returns `access_token`. Copy it into a variable:

   ```bash
   TOKEN='paste the access_token here'
   ```

5. List your tasks. You have one already: the service gave you a starter task
   when you registered (chapter 7 explains how):

   ```bash
   curl -s http://127.0.0.1:3000/tasks -H "authorization: Bearer $TOKEN"
   ```

6. Add a recurring task:

   ```bash
   curl -s -X POST http://127.0.0.1:3000/tasks \
     -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' \
     -d '{"title":"pay rent","due_on":"2026-01-31","repeat":"monthly"}'
   ```

7. Open <http://127.0.0.1:3000/docs/ui> in a browser. This is Swagger UI. It
   shows each route, its body and its answers. bustan makes this document from
   the code; nobody writes it by hand.

8. Stop the server with Ctrl+C, and run the tests:

   ```bash
   uv run pytest -q
   ```

   Each test that talks HTTP runs two times: once with the data in memory, and
   once with the data in SQLite. Chapter 8 explains why.

## Why it is built this way

- **One command to serve.** `bustan-sample-serve` takes `--host`, `--port` and
  `--reload`, and reads `HOST` and `PORT` from the environment. The scaffold of
  bustan makes two fixed commands, `start` and `dev`, with a fixed address. A
  container must listen on `0.0.0.0`, and two servers on one computer need two
  ports, so one flexible command replaces them.
- **No start without a secret.** A missing or short `IDENTITY_JWT_SECRET`
  stops the start. A service that starts with a weak default secret is worse
  than a service that does not start.

## Check yourself

1. Which function do the server, the tests and the OpenAPI export share?
2. Where does the API document come from?
3. What happens if you start the server with no `.env`?

Next: [2. Modules and injection](02-modules-and-injection.md).
