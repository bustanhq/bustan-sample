# The image of the application, on Chainguard base images.
# Build: docker build -t bustan-sample .
# Run:   docker run --rm -p 8000:8000 -e IDENTITY_JWT_SECRET=... bustan-sample
# SQLite: add -e DATABASE_BACKEND=sqlite -v bustan-sample-data:/app/var
#
# The free Chainguard Python image has only the tags latest and latest-dev.
# The digests pin one build of each. Dependabot proposes a new digest each
# week. The two stages must have the same digest date, thus the same Python.

FROM cgr.dev/chainguard/python:latest-dev@sha256:2f28d53bc0da2b0dcaabc5fc7aab2a69730466a9da4ffaa9bcf3019c3ff9905a AS build

# The -dev image has a shell and a package manager, for the build only.
USER root
# astral/uv on Docker Hub is the same image as ghcr.io/astral-sh/uv. Some
# Docker Desktop policies allow only some registries.
COPY --from=astral/uv:0.13.6 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/bin/python

WORKDIR /app

# The dependencies first, thus a change to the source does not install them
# again. README.md and LICENSE are necessary because pyproject.toml names them.
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src ./src
RUN uv sync --frozen --no-dev && mkdir -p /app/var


# The runtime image has no shell and no package manager. It runs as the user
# nonroot (65532).
FROM cgr.dev/chainguard/python:latest@sha256:1f18c1d5b8b986ee00542f2528899b1b68484b9991a80d7c5bcb819e931ddf69

WORKDIR /app
COPY --from=build --chown=65532:65532 /app/.venv /app/.venv
COPY --from=build --chown=65532:65532 /app/src /app/src
COPY --from=build --chown=65532:65532 /app/var /app/var

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    DATABASE_SQLITE_PATH=/app/var/bustan-sample.db

USER 65532
EXPOSE 8000
VOLUME ["/app/var"]

# Liveness only: a failed database must not restart a process that works.
# The exec form, because the image has no shell.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"]

# The base image starts python. The application starts its own command.
ENTRYPOINT ["bustan-sample-serve"]
