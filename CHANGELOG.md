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
- A job queue with retries, and cron schedules with a lock so that one process enqueues each run.
- `DATABASE_BACKEND=memory|sqlite`. With SQLite, the tasks, users, revoked tokens, jobs, event deliveries, schedule runs and rate-limit counts survive a restart and are shared by processes on one host.
- Versioned SQLite migrations for each component.
- Rate limits: 300 requests a minute for each client, and 10 a minute on login and register.
- Health probes: `GET /health/live` and `GET /health/ready`. With SQLite, readiness checks the database.
- OpenAPI document at `/docs/api`, Swagger UI at `/docs/ui`, and `openapi.yaml` from the code.
- Command `bustan-sample-serve` with `--host`, `--port` and `--reload`.
- Command `bustan-sample-openapi` to write and check `openapi.yaml`.
- Container image on Chainguard bases, with no shell, a non-root user, a volume for SQLite and a health check.
- lefthook hooks, CI, release workflow and Dependabot.
- A tutorial in ten chapters, from the first request to the trade-offs of the design.
