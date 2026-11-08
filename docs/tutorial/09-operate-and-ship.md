# 9. Operate and ship

## What you learn

- How the configuration is validated, and where each key is described.
- What the two health probes mean, and why the database check is only in one.
- How the logs connect the records of one request.
- How the container image is built and why it has no shell.
- What the hooks, CI and the release workflow do.

## Concepts

### Configuration

`src/bustan_sample/app_settings.py` is one Pydantic model of all keys. bustan
validates the environment and `.env` against it when the root module loads; a
missing or bad value stops the start. Each key starts with the name of the
module that reads it (`DATABASE_`, `IDENTITY_`, `JOBS_`). The full table is in
[docs/reference/configuration.md](../reference/configuration.md).

### Health probes

| Probe | Question | Checks |
|---|---|---|
| `GET /health/live` | Is this process alive? | Nothing: an answer is the proof |
| `GET /health/ready` | Can this process take traffic? | The startup state, and the database with SQLite |

A failed database must take the process out of traffic (readiness), not
restart it (liveness). A restart does not repair a database, and a restart
loop makes the outage worse. During shutdown, readiness goes down first, the
running requests finish, then the hooks run.

### Logs

The bustan `Logger` writes one JSON object for each record. Each record that a
request writes has the same `correlation_id`, `trace_id` and `span_id`. Send
an `x-correlation-id` header, and the server uses your id. The request logs
skip the probes, so a probe each few seconds does not hide the real requests.

### The container image

The `Dockerfile` has two stages, both on Chainguard images:

1. **Build**, on `cgr.dev/chainguard/python:latest-dev`: uv installs the
   locked dependencies, then the project, into `/app/.venv`.
2. **Runtime**, on `cgr.dev/chainguard/python:latest`: only the virtual
   environment and the source. No shell, no package manager, user `nonroot`
   (65532), a volume at `/app/var` for SQLite, a health check on
   `/health/live`.

An image with no shell gives an attacker less to use, and has fewer packages
with known vulnerabilities. The cost: you cannot `docker exec ... sh` into a
container. Use the logs and the probes.

The free Chainguard images have only the tag `latest`. The Dockerfile pins each
stage by digest, so a build is repeatable, and Dependabot proposes a new
digest each week. The two digests must move together, because the build stage
makes the environment for the Python of the runtime stage. At the pinned
digest that Python is 3.15, so CI also tests 3.15.

### Hooks, CI and releases

- **lefthook** runs checks before each commit (lock, ruff, ty, a scan for
  secrets, the OpenAPI document), checks each commit message (Conventional
  Commits), and runs the tests before a push. Install it with
  `lefthook install`.
- **CI** (`.github/workflows/ci.yml`) runs the same checks, the tests on
  Python 3.13, 3.14 and 3.15, and builds the image, starts it on SQLite and
  reads `/health/ready`.
- **Release** (`.github/workflows/release.yml`) runs on a tag `vX.Y.Z`. It runs
  CI, checks that the tag is the version in `pyproject.toml`, takes the notes
  from `CHANGELOG.md`, pushes the image to GHCR and publishes a GitHub release.
  See [docs/how-to/cut-a-release.md](../how-to/cut-a-release.md).

## Try it

1. Build and run the image with SQLite and a volume:

   ```bash
   docker build -t bustan-sample .
   docker run --rm -p 8000:8000 \
     -e IDENTITY_JWT_SECRET="$(openssl rand -hex 32)" \
     -e DATABASE_BACKEND=sqlite -v bustan-sample-data:/app/var bustan-sample
   ```

2. Read both probes:

   ```bash
   curl -s http://127.0.0.1:8000/health/live
   curl -s http://127.0.0.1:8000/health/ready
   ```

3. Send a request with your own correlation id, and find it in the logs. The
   request has no token, so the log line is the refusal of the guard:

   ```bash
   curl -s http://127.0.0.1:8000/tasks -H 'x-correlation-id: my-trace-1'
   ```

4. Stop the container. On your computer, run two processes on one SQLite
   file, the second with the scheduler off. Use two terminals:

   ```bash
   DATABASE_BACKEND=sqlite uv run bustan-sample-serve --port 3000
   ```

   ```bash
   DATABASE_BACKEND=sqlite JOBS_SCHEDULER_ENABLED=false uv run bustan-sample-serve --port 3010
   ```

   Register on port 3000, log in on port 3010: both processes share the users,
   the tasks, the jobs and the rate-limit counts.

## Why it is built this way

- **Fail at startup.** A configuration error that waits for the first request
  is found by a user. One at startup is found by the deployment.
- **Readiness for dependencies.** It takes one process out of traffic, which is
  a recoverable state. Liveness is for faults that only a restart repairs.
- **Pinned everything.** Actions are pinned to commits, uv to a version, the
  base images to digests, and the dependencies to `uv.lock`. A build next
  month gives the same result as today, and Dependabot shows each change as a
  pull request.

## Check yourself

1. The database is down. Which probe fails, and what should the platform do?
2. Why does the runtime image have no shell?
3. What must be true before the release workflow publishes a tag?

Next: [10. Trade-offs and extensions](10-trade-offs-and-extensions.md).
