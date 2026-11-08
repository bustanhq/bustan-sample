# Changelog

All notable changes to this project are in this file. The format is
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and the project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Task API: list, get, add, change and delete tasks. Each task belongs to one user.
- Recurring tasks: a repeat phrase, for example "every 2 weeks on Monday". When a recurring task becomes done, the next task is added.
- Pages on `GET /tasks` with `limit` and `offset`, and a `Link` header with `rel="next"`.
- Identity: register, log in with an HS256 JWT, log out with revocation before expiry, and get the current user.
- Argon2id password hashes.
- A starter task and a welcome email for each new user, through events and jobs.
- A job queue with retries, and cron schedules with a lock, thus one process only enqueues each run.
- A transactional outbox: with SQLite, an event goes into the table `jobs` in the transaction that saves its data. A registration commits the user and its events together, or neither.
- `Database.transaction()` as one unit of work: each statement of the task joins it, with `after_commit()` and `after_rollback()` callbacks. A job enqueued in a transaction starts after the commit.
- Idempotency keys (`IdempotencyKeys`, in memory or in SQLite): each user gets one starter task and one welcome email, also if a job runs two times.
- A recurring task that becomes done and its next task commit in one transaction.
- External APIs: `HttpClientFactory` and `HttpClient` on httpx2, with timeouts, connection limits, the correlation id and one log record for each call. `ExternalServiceError` tells if a retry can succeed.
- `MAIL_BACKEND=resend`: the welcome email goes through the Resend API, with the idempotency key of the job in the `Idempotency-Key` header.
- `PermanentJobError` fails a job with no retry. `RetryJobLater` sets the wait before the next attempt.
- `DATABASE_BACKEND=memory|sqlite`. With SQLite, the tasks, users, revoked tokens, jobs, event deliveries, schedule runs, idempotency keys and rate-limit counts survive a restart. Processes on one host share them.
- Versioned SQLite migrations for each component.
- Rate limits: 300 requests a minute for each client, and 10 a minute on login and register.
- Health probes: `GET /health/live` and `GET /health/ready`. With SQLite, readiness examines the database.
- OpenAPI document at `/docs/api`, Swagger UI at `/docs/ui`, and `openapi.yaml` from the code.
- Command `bustan-sample-serve` with `--host`, `--port` and `--reload`.
- Command `bustan-sample-openapi` to write and check `openapi.yaml`.
- Container image on Chainguard bases, with no shell, a non-root user, a volume for SQLite and a health check.
- lefthook hooks, CI, release workflow and Dependabot.
- A tutorial in ten chapters, from the first request to the trade-offs of the design.
