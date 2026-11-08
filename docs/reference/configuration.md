# Configuration

`src/bustan_sample/app_settings.py` validates each value when Python imports
the root module. If a value is missing or not valid, the application does
not start. A value in the environment overrides the value in `.env`.
`.env.example` gives each key.

| Key | Meaning | Required | Default |
|---|---|---|---|
| `DATABASE_BACKEND` | `memory` or `sqlite` | no | `memory` |
| `DATABASE_SQLITE_PATH` | The SQLite file. A relative path starts at the working folder | no | `var/bustan-sample.db` |
| `IDENTITY_JWT_SECRET` | The HS256 secret of the access tokens, 32 characters or more | yes | none |
| `IDENTITY_JWT_ISSUER` | The `iss` claim of the access tokens | no | `bustan-sample` |
| `IDENTITY_TOKEN_TTL_MINUTES` | The lifetime of an access token, 1 to 1440 | no | `15` |
| `JOBS_WORKERS` | The job workers in each process, 1 to 32 | no | `2` |
| `JOBS_RETRY_DELAY_SECONDS` | The delay before the second attempt of a failed job. Each next delay is two times longer | no | `1.0` |
| `JOBS_POLL_SECONDS` | SQLite only: the time between two looks for the jobs of other processes | no | `0.5` |
| `JOBS_LEASE_SECONDS` | SQLite only: the time after which a different worker can take a job that a stopped process did not end | no | `300` |
| `JOBS_SCHEDULER_ENABLED` | `false` turns the cron scheduler off in this process | no | `true` |
| `MAIL_BACKEND` | `log` writes a log record for each email. `resend` sends it through the Resend API | no | `log` |
| `MAIL_FROM` | The sender address, for example `bustan-sample <noreply@example.com>`. Resend accepts only a verified domain | if `MAIL_BACKEND=resend` | none |
| `MAIL_RESEND_API_KEY` | The Resend API key, with permission to send | if `MAIL_BACKEND=resend` | none |

The command `bustan-sample-serve` also reads these variables. Its options
`--host` and `--port` override them.

| Key | Meaning | Required | Default |
|---|---|---|---|
| `HOST` | The listen address. The container image sets `0.0.0.0` | no | `127.0.0.1` |
| `PORT` | The listen port. The container image sets `8000` | no | `3000` |

## Constants in the code

| Constant | Value | File |
|---|---|---|
| Global rate limit | 300 requests in 60 s for each client | `platform/throttling/throttling_module.py` |
| Login and register limit | 10 requests a minute for each client | `modules/identity/api/identity_controller.py` |
| Page size of `GET /tasks` | default 50, maximum 100 | `modules/tasks/application/list_tasks_query.py` |
| Cleanup of revoked tokens | `*/10 * * * *` | `modules/identity/jobs/purge_revoked_tokens_job.py` |
| Timeout of an external call | connect 2 s, each read, write and pool wait 10 s | `platform/http/http_client_factory.py` |
| Connections to one external API | 20, of which 10 stay open | `platform/http/http_client_factory.py` |
| Longest wait before one job retry | 3600 s | `platform/jobs/job_queue.py` |
