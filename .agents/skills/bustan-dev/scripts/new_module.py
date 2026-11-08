# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Write the skeleton of a feature module into a bustan project.

The skeleton has one entity with a name, the four layers, the two storage
adapters with a migration, the routes GET /<module>, GET /<module>/{id} and
POST /<module>, and the tests. The project must have the platform modules
clock and database (copy_platform.py) and the test support of the reference
(tests/conftest.py with the client fixture, tests/support/database.py).

The script never replaces a file. After it, add <Module>Module to the
imports of the root module, then run ruff, ty, pytest, audit.py and
bustan-sample-openapi (or the openapi command of the project).

Contract: standard library only. Exit codes: 0 when it wrote the files, 1
when a file exists, 2 for a usage error.

    uv run new_module.py ~/code/my-api notes note
    uv run new_module.py ~/code/my-api notes note --dry-run
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

TEMPLATES: dict[str, str] = {
    "src/{pkg}/modules/{m}/__init__.py": '''\
"""The public names of the {m} module. Other modules import only these."""

from .{m}_module import {M}Module

__all__ = ["{M}Module"]
''',
    "src/{pkg}/modules/{m}/{m}_module.py": """\
from bustan import FactoryProvider, Module

from {pkg}.platform.clock import ClockModule
from {pkg}.platform.database import Database, DatabaseModule

from .api.{m}_controller import {M}Controller
from .application.create_{e}_command import Create{E}Handler
from .application.get_{e}_query import Get{E}Handler
from .application.list_{m}_query import List{M}Handler
from .domain.{e}_repository import {E}Repository
from .infra.in_memory_{e}_repository import InMemory{E}Repository
from .infra.sqlite_{e}_repository import Sqlite{E}Repository


def _{e}_repository(database: Database) -> {E}Repository:
    if database.is_sqlite:
        return Sqlite{E}Repository(database)
    return InMemory{E}Repository()


# The module binds each port of the domain to an adapter of the infra layer.
# DATABASE_BACKEND selects the adapter. The factory makes only that adapter.
@Module(
    imports=[ClockModule, DatabaseModule],
    controllers=[{M}Controller],
    providers=[
        FactoryProvider(provide={E}Repository, use_factory=_{e}_repository, inject=(Database,)),
        Create{E}Handler,
        Get{E}Handler,
        List{M}Handler,
    ],
)
class {M}Module:
    pass
""",
    "src/{pkg}/modules/{m}/domain/__init__.py": "",
    "src/{pkg}/modules/{m}/domain/errors.py": '''\
from uuid import UUID


class {E}Error(Exception):
    """The base class of the errors of the {m} domain."""


class {E}NotFoundError({E}Error):
    def __init__(self, {e}_id: UUID) -> None:
        super().__init__(f"no {e} with id {{{e}_id}}")
        self.{e}_id = {e}_id


class Invalid{E}Error({E}Error):
    """A value does not obey a rule of the {e} entity."""
''',
    "src/{pkg}/modules/{m}/domain/{e}.py": '''\
from dataclasses import dataclass
from datetime import datetime
from typing import Self
from uuid import UUID, uuid4

from .errors import Invalid{E}Error

NAME_MAX_LENGTH = 200


@dataclass(slots=True)
class {E}:
    """The entity keeps its own rules. It knows nothing about HTTP or storage."""

    id: UUID
    name: str
    created_at: datetime

    @classmethod
    def create(cls, name: str, now: datetime) -> Self:
        return cls(id=uuid4(), name=_valid_name(name), created_at=now)

    def rename(self, name: str) -> None:
        self.name = _valid_name(name)


def _valid_name(name: str) -> str:
    name = name.strip()
    if not 1 <= len(name) <= NAME_MAX_LENGTH:
        raise Invalid{E}Error(f"the name must have 1 to {{NAME_MAX_LENGTH}} characters")
    return name
''',
    "src/{pkg}/modules/{m}/domain/{e}_repository.py": '''\
from abc import ABC, abstractmethod
from uuid import UUID

from .{e} import {E}


class {E}Repository(ABC):
    """The storage port of the {m} module. infra/ gives the adapters."""

    @abstractmethod
    async def save(self, {e}: {E}) -> None:
        """Add the {e}, or replace the stored {e} that has the same id."""

    @abstractmethod
    async def get(self, {e}_id: UUID) -> {E} | None:
        """Return the {e}, or None."""

    @abstractmethod
    async def find(self, limit: int | None = None, offset: int = 0) -> list[{E}]:
        """Return the {m} in the sequence of creation, one page if limit is given."""
''',
    "src/{pkg}/modules/{m}/infra/__init__.py": "",
    "src/{pkg}/modules/{m}/infra/in_memory_{e}_repository.py": '''\
from dataclasses import replace
from uuid import UUID

from bustan import Injectable

from ..domain.{e} import {E}
from ..domain.{e}_repository import {E}Repository


@Injectable()
class InMemory{E}Repository({E}Repository):
    """Keeps the {m} in a dict. It stores and returns copies."""

    def __init__(self) -> None:
        self._items: dict[UUID, {E}] = {{}}

    async def save(self, {e}: {E}) -> None:
        self._items[{e}.id] = replace({e})

    async def get(self, {e}_id: UUID) -> {E} | None:
        stored = self._items.get({e}_id)
        return None if stored is None else replace(stored)

    async def find(self, limit: int | None = None, offset: int = 0) -> list[{E}]:
        items = sorted(self._items.values(), key=lambda item: item.created_at)
        end = None if limit is None else offset + limit
        return [replace(item) for item in items[offset:end]]
''',
    "src/{pkg}/modules/{m}/infra/sqlite_{e}_repository.py": '''\
from uuid import UUID

import aiosqlite
from bustan import Injectable

from {pkg}.platform.database import Database, Migration, from_text, to_text

from ..domain.{e} import {E}
from ..domain.{e}_repository import {E}Repository

# Add a migration with the next version for each change. Never edit one.
_V1 = """
CREATE TABLE IF NOT EXISTS {m} (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
MIGRATIONS = (Migration(1, "create the table {m}", _V1),)


@Injectable()
class Sqlite{E}Repository({E}Repository):
    """Keeps the {m} in the table {m}. on_module_init applies the migrations."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def on_module_init(self) -> None:
        await self._database.migrate("{m}", MIGRATIONS)

    async def save(self, {e}: {E}) -> None:
        await self._database.execute(
            "INSERT INTO {m} (id, name, created_at) VALUES (?, ?, ?) "
            "ON CONFLICT (id) DO UPDATE SET name = excluded.name",
            (str({e}.id), {e}.name, to_text({e}.created_at)),
        )

    async def get(self, {e}_id: UUID) -> {E} | None:
        row = await self._database.fetch_one("SELECT * FROM {m} WHERE id = ?", (str({e}_id),))
        return None if row is None else _to_{e}(row)

    async def find(self, limit: int | None = None, offset: int = 0) -> list[{E}]:
        rows = await self._database.fetch_all(
            "SELECT * FROM {m} ORDER BY created_at, rowid LIMIT ? OFFSET ?",
            (-1 if limit is None else limit, offset),
        )
        return [_to_{e}(row) for row in rows]


def _to_{e}(row: aiosqlite.Row) -> {E}:
    return {E}(id=UUID(row["id"]), name=row["name"], created_at=from_text(row["created_at"]))
''',
    "src/{pkg}/modules/{m}/application/__init__.py": "",
    "src/{pkg}/modules/{m}/application/create_{e}_command.py": """\
from dataclasses import dataclass

from bustan import Injectable

from {pkg}.platform.clock import Clock

from ..domain.{e} import {E}
from ..domain.{e}_repository import {E}Repository


@dataclass(frozen=True, slots=True)
class Create{E}Command:
    name: str


@Injectable()
class Create{E}Handler:
    def __init__(self, repository: {E}Repository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def execute(self, command: Create{E}Command) -> {E}:
        {e} = {E}.create(command.name, self._clock.now())
        await self._repository.save({e})
        return {e}
""",
    "src/{pkg}/modules/{m}/application/get_{e}_query.py": """\
from dataclasses import dataclass
from uuid import UUID

from bustan import Injectable

from ..domain.errors import {E}NotFoundError
from ..domain.{e} import {E}
from ..domain.{e}_repository import {E}Repository


@dataclass(frozen=True, slots=True)
class Get{E}Query:
    {e}_id: UUID


@Injectable()
class Get{E}Handler:
    def __init__(self, repository: {E}Repository) -> None:
        self._repository = repository

    async def execute(self, query: Get{E}Query) -> {E}:
        {e} = await self._repository.get(query.{e}_id)
        if {e} is None:
            raise {E}NotFoundError(query.{e}_id)
        return {e}
""",
    "src/{pkg}/modules/{m}/application/list_{m}_query.py": """\
from dataclasses import dataclass

from bustan import Injectable

from ..domain.{e} import {E}
from ..domain.{e}_repository import {E}Repository

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


@dataclass(frozen=True, slots=True)
class List{M}Query:
    limit: int = DEFAULT_LIMIT
    offset: int = 0


@Injectable()
class List{M}Handler:
    def __init__(self, repository: {E}Repository) -> None:
        self._repository = repository

    async def execute(self, query: List{M}Query) -> list[{E}]:
        return await self._repository.find(query.limit, query.offset)
""",
    "src/{pkg}/modules/{m}/api/__init__.py": "",
    "src/{pkg}/modules/{m}/api/{m}_schemas.py": """\
from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from ..domain.{e} import NAME_MAX_LENGTH, {E}

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=NAME_MAX_LENGTH)
]


class Create{E}Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name


class {E}Response(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    @classmethod
    def from_{e}(cls, {e}: {E}) -> Self:
        return cls(id={e}.id, name={e}.name, created_at={e}.created_at)

    def to_json(self) -> dict[str, object]:
        return self.model_dump(mode="json")
""",
    "src/{pkg}/modules/{m}/api/{m}_errors_filter.py": '''\
from bustan import ExceptionFilter, ExecutionContext, HttpResponse, ProblemDetailsExceptionFilter
from bustan.errors import BadRequestException, NotFoundException

from ..domain.errors import Invalid{E}Error, {E}NotFoundError


class {M}ErrorsFilter(ExceptionFilter):
    """Changes the domain errors into RFC 9457 problem details."""

    exception_types = ({E}NotFoundError, Invalid{E}Error)

    def __init__(self) -> None:
        self._problems = ProblemDetailsExceptionFilter()

    async def catch(self, exc: Exception, context: ExecutionContext) -> HttpResponse:
        if isinstance(exc, {E}NotFoundError):
            return await self._problems.catch(NotFoundException(str(exc)), context)
        return await self._problems.catch(BadRequestException(str(exc)), context)
''',
    "src/{pkg}/modules/{m}/api/{m}_controller.py": '''\
from uuid import UUID

from bustan import (
    ApiOperation,
    ApiResponse,
    ApiTags,
    Controller,
    Get,
    HttpResponse,
    Post,
    UseFilters,
)
from bustan.errors import BadRequestException

from ..application.create_{e}_command import Create{E}Command, Create{E}Handler
from ..application.get_{e}_query import Get{E}Handler, Get{E}Query
from ..application.list_{m}_query import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    List{M}Handler,
    List{M}Query,
)
from .{m}_errors_filter import {M}ErrorsFilter
from .{m}_schemas import Create{E}Request, {E}Response


# The routes are public. For a token, add @Auth(STRATEGY) of the identity
# module and an argument Annotated[AuthenticatedUser, CurrentUser()].
@UseFilters({M}ErrorsFilter())
@Controller("/{m}")
@ApiTags("{m}")
class {M}Controller:
    """Maps HTTP requests to commands and queries. It has no business logic."""

    def __init__(
        self, create: Create{E}Handler, get: Get{E}Handler, list_all: List{M}Handler
    ) -> None:
        self._create = create
        self._get = get
        self._list = list_all

    @Get("/")
    @ApiOperation(summary="List the {m}")
    @ApiResponse(status=200, description="The {m}, in the sequence of creation")
    async def list_{m}(
        self, limit: int = DEFAULT_LIMIT, offset: int = 0
    ) -> list[dict[str, object]]:
        if not 1 <= limit <= MAX_LIMIT or offset < 0:
            raise BadRequestException(f"the limit must be 1 to {{MAX_LIMIT}}, the offset 0 or more")
        items = await self._list.execute(List{M}Query(limit=limit, offset=offset))
        return [{E}Response.from_{e}(item).to_json() for item in items]

    @Get("/{{{e}_id}}")
    @ApiOperation(summary="Get one {e}")
    @ApiResponse(status=200, description="The {e}", schema={E}Response)
    @ApiResponse(status=404, description="No {e} has this id")
    async def get_{e}(self, {e}_id: UUID) -> dict[str, object]:
        {e} = await self._get.execute(Get{E}Query({e}_id={e}_id))
        return {E}Response.from_{e}({e}).to_json()

    @Post("/")
    @ApiOperation(summary="Add a {e}")
    @ApiResponse(status=201, description="The new {e}", schema={E}Response)
    @ApiResponse(status=400, description="The body is not valid")
    async def create_{e}(self, payload: Create{E}Request) -> HttpResponse:
        {e} = await self._create.execute(Create{E}Command(name=payload.name))
        return HttpResponse.json(
            {E}Response.from_{e}({e}).to_json(),
            status_code=201,
            headers={{"location": f"/{m}/{{{e}.id}}"}},
        )
''',
    "src/{pkg}/modules/{m}/listeners/__init__.py": "",
    "src/{pkg}/modules/{m}/jobs/__init__.py": "",
    "tests/{pkg}/modules/{m}/domain/test_{e}.py": """\
from datetime import UTC, datetime

import pytest

from {pkg}.modules.{m}.domain.errors import Invalid{E}Error
from {pkg}.modules.{m}.domain.{e} import NAME_MAX_LENGTH, {E}

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def test_a_new_{e}_has_a_stripped_name() -> None:
    assert {E}.create("  a  ", T0).name == "a"


@pytest.mark.parametrize("name", ["", "   ", "x" * (NAME_MAX_LENGTH + 1)])
def test_an_invalid_name_is_refused(name: str) -> None:
    with pytest.raises(Invalid{E}Error):
        {E}.create(name, T0)
""",
    "tests/{pkg}/modules/{m}/domain/test_{e}_repository.py": '''\
"""The contract of the {E}Repository port. Each test runs on each adapter."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from {pkg}.modules.{m}.domain.{e} import {E}
from {pkg}.modules.{m}.domain.{e}_repository import {E}Repository
from {pkg}.modules.{m}.infra.in_memory_{e}_repository import InMemory{E}Repository
from {pkg}.modules.{m}.infra.sqlite_{e}_repository import Sqlite{E}Repository

from support.database import BACKENDS, open_sqlite

T0 = datetime(2026, 1, 1, tzinfo=UTC)

pytestmark = pytest.mark.parametrize("backend", BACKENDS)


@asynccontextmanager
async def _repository(backend: str, path: Path) -> AsyncGenerator[{E}Repository]:
    if backend == "memory":
        yield InMemory{E}Repository()
        return
    async with open_sqlite(path) as database:
        repository = Sqlite{E}Repository(database)
        await repository.on_module_init()
        yield repository


def test_a_saved_{e}_reads_back(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _repository(backend, tmp_path / "test.db") as repository:
            {e} = {E}.create("a", T0)
            await repository.save({e})
            assert await repository.get({e}.id) == {e}
            assert await repository.get(uuid4()) is None

    asyncio.run(scenario())


def test_find_gives_pages_in_the_sequence_of_creation(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _repository(backend, tmp_path / "test.db") as repository:
            for number in range(3):
                await repository.save({E}.create(f"n{{number}}", T0))
            page = await repository.find(limit=2, offset=1)
            assert [item.name for item in page] == ["n1", "n2"]

    asyncio.run(scenario())
''',
    "tests/{pkg}/modules/{m}/api/test_{m}_controller.py": """\
from bustan.testing import AsgiTestClient


def test_create_then_get_and_list(client: AsgiTestClient) -> None:
    created = client.post("/{m}", json={{"name": "a"}})
    assert created.status_code == 201
    body = created.json()
    assert created.headers["location"] == f"/{m}/{{body['id']}}"
    assert client.get(f"/{m}/{{body['id']}}").json() == body
    assert [item["name"] for item in client.get("/{m}").json()] == ["a"]


def test_errors_are_problem_details(client: AsgiTestClient) -> None:
    missing = client.get("/{m}/00000000-0000-0000-0000-000000000000")
    invalid = client.post("/{m}", json={{"name": "   "}})
    assert (missing.status_code, invalid.status_code) == (404, 400)
    assert missing.headers["content-type"].startswith("application/problem+json")
""",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="new_module.py", description=__doc__.splitlines()[0])
    parser.add_argument("project", type=Path, help="the folder with pyproject.toml")
    parser.add_argument("module", help="the module name, plural snake_case, for example notes")
    parser.add_argument("entity", help="the entity name, singular snake_case, for example note")
    parser.add_argument("--package", help="the import package (default: the only one in src/)")
    parser.add_argument("--dry-run", action="store_true", help="list the files, write nothing")
    args = parser.parse_args(argv)
    project = args.project.expanduser().resolve()
    pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    if not (pattern.match(args.module) and pattern.match(args.entity)):
        print("the module and the entity names must be snake_case", file=sys.stderr)
        return 2
    package = args.package or _only_package(project / "src")
    if package is None:
        print("give --package: src/ has no package, or more than one", file=sys.stderr)
        return 2
    for needed in ("platform/clock", "platform/database"):
        if not (project / "src" / package / needed).is_dir():
            print(f"src/{package}/{needed} is missing: run copy_platform.py first", file=sys.stderr)
            return 2
    names = {
        "pkg": package,
        "m": args.module,
        "M": _pascal(args.module),
        "e": args.entity,
        "E": _pascal(args.entity),
    }
    files = {
        project / path.format(**names): text.format(**names) for path, text in TEMPLATES.items()
    }
    existing = [path for path in files if path.exists()]
    if existing:
        for path in existing:
            print(f"exists: {path.relative_to(project)}", file=sys.stderr)
        return 1
    for path, text in files.items():
        print(f"{'would write' if args.dry_run else 'wrote'} {path.relative_to(project)}")
        if not args.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    if not args.dry_run:
        _format(project, list(files))
    print(
        f"\nNext: add {names['M']}Module from .modules.{args.module} to the imports of the "
        "root module, then run ruff, ty, pytest, audit.py and the OpenAPI export."
    )
    return 0


def _format(project: Path, paths: list[Path]) -> None:
    """Sort the imports and format the new files with the ruff of the project."""
    names = [str(path) for path in paths]
    for command in (["ruff", "check", "--fix", "-q", *names], ["ruff", "format", "-q", *names]):
        # The project has its own environment, not the one of this script.
        env = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
        result = subprocess.run(
            ["uv", "run", "--frozen", *command], cwd=project, env=env, check=False
        )
        if result.returncode != 0:
            print(f"ruff did not end clean: {' '.join(command[:2])}", file=sys.stderr)


def _only_package(src: Path) -> str | None:
    if not src.is_dir():
        return None
    packages = [p.name for p in src.iterdir() if (p / "__init__.py").exists()]
    return packages[0] if len(packages) == 1 else None


def _pascal(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


if __name__ == "__main__":
    raise SystemExit(main())
