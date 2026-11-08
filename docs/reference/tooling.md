# Tooling

## Commands

| Command | Result |
|---|---|
| `uv run bustan-sample-serve [--host H] [--port P] [--reload]` | Serves the application |
| `uv run bustan-sample-openapi [--output F] [--check]` | Writes `openapi.yaml` from the code, or checks it |
| `uv run pytest` | Runs the tests. Each test with the `client` fixture runs on both backends |
| `uv run ruff check .` and `uv run ruff format --check .` | Lint and format |
| `uv run ty check` | Type check |
| `uv run scripts/check_secrets.py --all` | Scans the files for tokens, private keys and `.env` files |
| `uv run scripts/check_secrets.py --history` | Scans each commit. Run it before the first push to a new remote |
| `uv run scripts/check_commit.py --range origin/main..HEAD` | Checks the commit messages |

## Git hooks

lefthook runs the hooks in `lefthook.yml`. Install them one time in each
clone:

```bash
lefthook install
```

| Hook | Checks |
|---|---|
| pre-commit | `uv lock --check`, then in parallel: ruff (fix and format of the staged files), ty, the secret scan of the staged files, and the OpenAPI check |
| commit-msg | Conventional Commits: `type(scope)!: subject`, 72 characters or less, ASCII, no attribution lines |
| pre-push | The full test suite |

Personal additions go in `lefthook-local.yml`, which git ignores. Do not
skip a hook with `--no-verify`.

## Commit messages

The types are `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore` and `revert`. A `!` after the type, or a footer
`BREAKING CHANGE: ...`, marks a breaking change.

## CI

`.github/workflows/ci.yml` runs on each push to `main`, on each pull request,
and from the release workflow:

- checks: the lockfile, ruff, ty, the secret scan, the OpenAPI check, and the
  commit messages of a pull request
- tests: Python 3.13, 3.14 and 3.15
- image: builds the container image, starts it on SQLite and reads
  `/health/ready`

The actions are pinned to a commit. Dependabot proposes updates each week for
the actions, `uv.lock` and the Docker base images. Rebase-merge each pull
request, never squash.

## Release

`.github/workflows/release.yml` runs on a tag `vX.Y.Z`. See
[Cut a release](../how-to/cut-a-release.md).
