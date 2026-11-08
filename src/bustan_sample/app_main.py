"""The entry points: the application factory and the command bustan-sample-serve."""

import argparse
import asyncio
import importlib
import os

import uvicorn
from bustan import Application, create_app

from .app_module import AppModule
from .app_openapi import swagger_options

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3000


def create_asgi_app() -> Application:
    """Return the application. The application is the ASGI callable that a server runs."""
    return create_app(AppModule, swagger=swagger_options())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bustan-sample-serve", description="Serve the application over HTTP."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", DEFAULT_HOST),
        help="the address to listen on (default: $HOST or %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", DEFAULT_PORT)),
        help="the port to listen on (default: $PORT or %(default)s)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="start again when a file in src/ changes (for development)",
    )
    args = parser.parse_args(argv)
    if args.reload:
        _serve_with_reload(args.host, args.port)
    else:
        _serve(args.host, args.port)
    return 0


def _serve(host: str, port: int) -> None:
    # listen() serves on the event loop that runs it. Thus this function selects
    # the loop: uvloop if the uvicorn standard extra installed it, else asyncio.
    # importlib finds uvloop by name, because a type checker refuses an import
    # that it cannot resolve on each platform.
    try:
        loop_factory = importlib.import_module("uvloop").new_event_loop
    except ImportError:
        loop_factory = None
    asyncio.run(create_asgi_app().listen(port=port, host=host), loop_factory=loop_factory)


def _serve_with_reload(host: str, port: int) -> None:
    # For a reload, uvicorn must own the process: after each change it starts a
    # new worker that imports the application again. Thus uvicorn gets the name
    # of the factory, not an application. An application belongs to the process
    # that made it.
    uvicorn.run(
        "bustan_sample.app_main:create_asgi_app",
        factory=True,
        host=host,
        port=port,
        reload=True,
        reload_dirs=["src"],
    )


if __name__ == "__main__":
    raise SystemExit(main())
