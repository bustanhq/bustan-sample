# Tooling

Copy each file from the reference <https://github.com/bustanhq/bustan-sample> and change the
package and project names.

| File | Contents |
|---|---|
| `pyproject.toml` (tool tables) | `[tool.ruff]`: line-length 100, target py313. `[tool.ruff.lint]`: the rule sets E, F, W, B, UP, RUF, SIM, BLE and the import sort. isort: first-party `<pkg>`, local folder `support`. `[tool.pytest]`: references/testing.md |
| `lefthook.yml` | pre-commit: `uv lock --check` first, then in parallel ruff fix and format on staged `*.py` files, ruff format on staged `*.md` files, `ty check`, `scripts/check_secrets.py {staged_files}`, `<project>-openapi --check`. commit-msg: `scripts/check_commit.py {1}`. pre-push: `pytest -q` |
| `scripts/check_commit.py`, `scripts/check_secrets.py` | From `scripts/` of the reference |
| `LICENSE` | The Apache License 2.0: `gh api /licenses/apache-2.0 --jq .body > LICENSE`. In `pyproject.toml`: `license = "Apache-2.0"` and `license-files = ["LICENSE"]`. Keep the copyright line of the appendix as a template |
| `.agents/skills/<name>/` | The agent skill of the project, tracked with the code. ruff and the hooks examine its scripts and the Python blocks of its pages. For Claude Code, add the untracked symlink `.claude/skills -> ../.agents/skills` and list it in `.git/info/exclude` |
| `.github/workflows/ci.yml` | `on: push (main), pull_request, workflow_call`. Three jobs. checks: lock, ruff, ty, secrets `--all`, OpenAPI, commit range of a pull request. tests: a matrix of the Python versions. image: build, start on SQLite, read `/health/ready` |
| `.github/workflows/release.yml` | On a tag `vX.Y.Z`: CI, a tag that is `uv version --short`, the notes from CHANGELOG.md, `uv build`, the image in `ghcr.io/<owner>/<repo>`, and `gh release create` |
| `.github/dependabot.yml` | Weekly: github-actions, uv, docker |
| `CHANGELOG.md` | Keep a Changelog 1.1.0. One line in `[Unreleased]` for each change that a user sees |
| `Dockerfile`, `.dockerignore` | Below |
| `docs/` | `README.md` (index), `how-to/`, `reference/configuration.md` (Key, Meaning, Required, Default), `reference/tooling.md`, `tutorial/` (a progressive tutorial: concepts, steps, the reasons for the design) |

## Pins

- Pin each action to a commit, with the release in a comment. Read the
  commit of a tag with `gh api repos/<owner>/<repo>/git/ref/tags/<tag> --jq .object.sha`.
- Pin the uv version in the workflows (`UV_VERSION`) and in the Dockerfile.
- Validate with `actionlint` and `lefthook validate`. Install the hooks with
  `lefthook install`.

## Dockerfile

- Build stage: `cgr.dev/chainguard/python:latest-dev@sha256:...`, `USER root`,
  uv from `astral/uv:<version>` (Docker Hub), `UV_PYTHON=/usr/bin/python`,
  `UV_PYTHON_DOWNLOADS=never`. Copy `pyproject.toml`, `uv.lock`, `README.md`
  and `LICENSE` (pyproject.toml names the two last files), run
  `uv sync --frozen --no-install-project --no-dev`, then copy the source and
  run `uv sync --frozen --no-dev`.
- Runtime stage: `cgr.dev/chainguard/python:latest@sha256:...`, no shell,
  user 65532. Copy `.venv`, `src` and `var` with `--chown=65532:65532`.
  `ENV HOST=0.0.0.0 PORT=8000 DATABASE_SQLITE_PATH=/app/var/<project>.db`,
  `VOLUME ["/app/var"]`, a HEALTHCHECK in exec form with python and
  `/health/live`, `ENTRYPOINT ["<project>-serve"]`.
- The free Chainguard image has only `latest`. Pin the digests of the two
  stages from the same day, and add its Python version to the CI matrix.
- `.dockerignore`: `.env`, `.env.*` (not `.env.example`), `.venv/`, `.git/`,
  `var/`, `*.db*`, caches, `tests/`, `docs/`, `.agents/`.
- Test: build, run with `-e IDENTITY_JWT_SECRET=... -e DATABASE_BACKEND=sqlite -v <volume>:/app/var`,
  read the probes, restart, and look at `docker inspect --format '{{.State.Health.Status}}'`.

## Tutorial

`docs/tutorial/` teaches the design in chapters from novice to master. Each
chapter has: what you learn, the concepts in layers, steps to try, the
reasons for the design and its cost, and questions. Put the reason for each
deviation from a house rule (for example the module layout and the Python
floor) in the chapter that introduces that part.

## Commits and releases

- Conventional Commits, 72 characters or less in the header, ASCII, no
  attribution lines.
- Commit or push only when the user asks. Never use `--no-verify`.
- Semver tags `vX.Y.Z`, never used two times. Steps:
  `docs/how-to/cut-a-release.md` of the reference.
