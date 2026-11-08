# Report a bustan issue, or send a fix

This guide is for a person or a coding agent that finds a defect or a limit
in bustan itself. It obeys the rules of
[bustanhq/bustan](https://github.com/bustanhq/bustan): its
[contribution guide](https://github.com/bustanhq/bustan/blob/main/CONTRIBUTING.md),
its [security policy](https://github.com/bustanhq/bustan/blob/main/SECURITY.md),
its issue templates and its pull request template.

## Rules for a coding agent

- Show each draft to your user. File an issue, fork the repository or open a
  pull request only after your user agrees. Each of these is public, and it
  is in the name of the GitHub account of your user.
- Never put private data in an issue or a pull request. Private data
  includes secrets, customer records, internal host names and the paths on
  the computer of your user. Use invented data in the reproduction.
- Do not report a security vulnerability in a public issue. Send it to
  `security@bustan.dev`, or use "Report a vulnerability" in the Security tab
  of the repository.
- Write one problem in each issue. Do not add a greeting, an apology, a
  signature or a line that names the tool that wrote the text.

## 1. Make sure that the cause is in bustan

Write the smallest script that shows the behavior. Pin the version of bustan
that your project uses, and use no code of your project:

```python
# /// script
# requires-python = ">=3.13"
# dependencies = ["bustan[starlette]==2.0.3"]
# ///
import asyncio

from bustan import Injectable, Module
from bustan.testing import create_testing_module


@Injectable()
class Service:
    pass


@Module(providers=[Service])
class AppModule:
    pass


async def main() -> None:
    compiled = await create_testing_module(AppModule).compile()
    print(type(compiled.get(Service)).__name__)
    await compiled.close()


asyncio.run(main())
```

Run it with `uv run repro.py`. If the script does not show the behavior, the
cause is in your project, not in bustan. Look again before you file an
issue.

## 2. Look for the same issue

```bash
gh issue list --repo bustanhq/bustan --state all --search "provider override"
```

If an issue gives the same problem, do not open a new one. If you have a new
fact, for example a shorter reproduction or a different version, add it as a
comment.

## 3. Write the issue

Select the template that agrees with the problem:

| Template | Title starts with | Label | Use it for |
|---|---|---|---|
| Bug report | `bug: ` | `bug` | A defect, a regression, or behavior that does not agree with the docs |
| Feature request | `feat: ` | `enhancement` | A limit: something that bustan cannot do |
| Adoption feedback | `adoption: ` | `feedback` | Friction during evaluation or onboarding |

Write the body with the headings of the template. For a bug report:

- `Summary`: one or two sentences that give the behavior.
- `Expected Behavior` and `Actual Behavior`.
- `Reproduction`: the full script of step 1, and the command.
- `Environment`: the bustan version, the Python version and the OS.
- `Additional Context`: the lines of the traceback that matter, not the
  full log. Give the work-around if you have one.

The title gives the behavior, not your opinion. For example,
"bug: ConfigModule.for_root() reads the environment at import time, not when
the application starts". Issues
[#415](https://github.com/bustanhq/bustan/issues/415) and
[#417](https://github.com/bustanhq/bustan/issues/417) are examples.

Blank issues are off in the web form, thus use the template there. With the
GitHub CLI, give the title, the label and the body file:

```bash
gh issue create --repo bustanhq/bustan --title "bug: <the behavior>" \
  --label bug --body-file issue.md
```

Only an account with write access to the repository can set a label. Without
that access, leave out `--label`: the prefix of the title gives the type.

## 4. Work around the issue in your project

- Put the work-around in one place, with a comment that gives the issue
  link.
- Add the issue to the list of known issues of your project, for example
  the table "Gaps in bustan 2.0.3" in chapter 10 of the tutorial.
- When a release corrects the issue, remove the work-around and the line.

## 5. Send a fix

Send a pull request only for a small and clear fix, or after a maintainer
agrees on the issue. For a larger change, open a feature request first, and
wait until a maintainer agrees.

```bash
gh repo fork bustanhq/bustan --clone
cd bustan
git switch -c fix/<short-name>
uv sync --group dev
uv run lefthook install
```

Make the change, and add a test that fails without it. Then run the checks of
the contribution guide:

```bash
uv run python scripts/generate_api_reference.py --check
uv run python scripts/check_markdown_links.py
uv run ruff check .
uv run ty check src tests scripts
uv run pytest
```

Obey these rules of the repository:

- Use Conventional Commits, for example
  `fix: tighten provider resolution error message`.
- Keep the change on the problem. Do not format files that you did not
  change.
- The public API is `bustan`, `bustan.errors` and `bustan.testing`. If you
  change a public docstring, run
  `uv run python scripts/generate_api_reference.py`.
- Update the docs for each change that a user sees.
- The repository supports Python 3.13 or a subsequent version. It does not
  require a CLA or a DCO sign-off.

Push the branch and open the pull request:

```bash
git push -u origin fix/<short-name>
gh pr create --repo bustanhq/bustan --title "fix: <subject>" --body-file pr.md
```

Write the body with the sections of the pull request template:

- `Closes #<issue>` on the first line.
- `What changed`: the behavior or the docs that changed.
- `Acceptance`: one ticked box for each criterion of the issue, with the
  test or the file that proves it.
- `Verification`: one line for each check, with the command and its last
  status line. Do not paste the output.
- `Decisions`: each choice that a reviewer must know.
- `Not done`: the work that you did not do, on purpose.
