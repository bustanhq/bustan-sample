# Run the application in a container

The `Dockerfile` builds on Chainguard images: `cgr.dev/chainguard/python:latest-dev`
for the build, and `cgr.dev/chainguard/python:latest` for the runtime. The
runtime image has no shell and no package manager, and runs as the user
`nonroot` (65532). It has a volume for SQLite at `/app/var` and a health check
on `/health/live`, and it listens on port 8000.

1. Build the image:

   ```bash
   docker build -t bustan-sample .
   ```

2. Run it with the memory backend:

   ```bash
   docker run --rm -p 8000:8000 -e IDENTITY_JWT_SECRET="$(openssl rand -hex 32)" bustan-sample
   ```

3. To keep the data, run it with SQLite and a named volume:

   ```bash
   docker run --rm -p 8000:8000 \
     -e IDENTITY_JWT_SECRET="$(openssl rand -hex 32)" \
     -e DATABASE_BACKEND=sqlite \
     -v bustan-sample-data:/app/var \
     bustan-sample
   ```

Give the same `IDENTITY_JWT_SECRET` at each start. A new secret stops all
tokens.

## Probes

| Probe | Path | Use |
|---|---|---|
| Liveness | `/health/live` | Restart the container if it fails |
| Readiness | `/health/ready` | Send no traffic while it fails. With SQLite, it checks the database |

Do not connect the database check to liveness. A short database failure must
not restart a process that works.

## Notes

- `.dockerignore` keeps `.env`, `.git`, `var/`, the tests and the docs out of
  the image. Configuration reaches a container as environment variables.
- The free Chainguard images have only the tags `latest` and `latest-dev`.
  The Dockerfile pins both by digest, and Dependabot proposes new digests each
  week. Both stages must move together, because the build stage makes the
  virtual environment for the Python of the runtime stage.
- The Dockerfile copies uv from `astral/uv` on Docker Hub. It is the same
  image as `ghcr.io/astral-sh/uv`. Some Docker Desktop policies refuse
  ghcr.io.
- The runtime image has no shell, thus use `docker logs` and the probes to
  examine a container. `docker exec ... sh` does not work.
- Run one container for each SQLite volume on one host. Processes share an
  SQLite file only on one host.
