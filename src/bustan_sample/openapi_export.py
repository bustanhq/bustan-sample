"""The command bustan-sample-openapi: write openapi.yaml, or examine it."""

import argparse
import os
import sys
from pathlib import Path

import yaml

DEFAULT_OUTPUT = Path("openapi.yaml")
# The document does not use the settings, but the import of the root module
# validates them. The export never serves requests, thus a placeholder secret
# is safe here. A secret in the environment or in .env has priority.
_PLACEHOLDER_SECRET = "a-placeholder-for-the-openapi-export-only"


def render() -> str:
    """Return the OpenAPI document of the application as YAML text."""
    os.environ.setdefault("IDENTITY_JWT_SECRET", _PLACEHOLDER_SECRET)
    from bustan.testing import AsgiTestClient

    from .app_main import create_asgi_app
    from .app_openapi import DOCUMENT_PATH

    # A client that is not a context manager runs no lifespan. Thus the export
    # starts no job worker and no scheduler.
    response = AsgiTestClient(create_asgi_app()).get(DOCUMENT_PATH)
    if response.status_code != 200:
        raise RuntimeError(f"GET {DOCUMENT_PATH} gave {response.status_code}")
    return yaml.safe_dump(response.json(), sort_keys=False, allow_unicode=False, width=100)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bustan-sample-openapi",
        description="Write the OpenAPI document of the application to a YAML file.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="default: %(default)s")
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit 1 if the file is different from the code",
    )
    args = parser.parse_args(argv)
    text = render()
    if args.check:
        current = args.output.read_text() if args.output.exists() else None
        if current != text:
            print(
                f"{args.output} does not agree with the code. Run: uv run bustan-sample-openapi",
                file=sys.stderr,
            )
            return 1
        print(f"{args.output} agrees with the code")
        return 0
    args.output.write_text(text)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
