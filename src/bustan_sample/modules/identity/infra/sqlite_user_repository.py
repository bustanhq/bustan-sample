import sqlite3
from uuid import UUID

import aiosqlite
from bustan import Injectable

from bustan_sample.platform.database import Database, from_text, to_text

from ..domain.errors import EmailTakenError
from ..domain.user import User
from ..domain.user_repository import UserRepository

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
_SAVE = """
INSERT INTO users (id, email, password_hash, created_at)
VALUES (:id, :email, :password_hash, :created_at)
ON CONFLICT (id) DO UPDATE SET
    email = excluded.email,
    password_hash = excluded.password_hash
"""


@Injectable()
class SqliteUserRepository(UserRepository):
    """Keeps the users in the table users of the SQLite database.

    The email column is unique. If two requests register the same email at
    the same time, the second save raises EmailTakenError.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    async def on_module_init(self) -> None:
        await self._database.execute_script(_SCHEMA)

    async def save(self, user: User) -> None:
        try:
            await self._database.execute(
                _SAVE,
                {
                    "id": str(user.id),
                    "email": user.email,
                    "password_hash": user.password_hash,
                    "created_at": to_text(user.created_at),
                },
            )
        except sqlite3.IntegrityError as exc:
            raise EmailTakenError() from exc

    async def get(self, user_id: UUID) -> User | None:
        row = await self._database.fetch_one(
            "SELECT * FROM users WHERE id = ?", (str(user_id),)
        )
        return None if row is None else _to_user(row)

    async def get_by_email(self, email: str) -> User | None:
        row = await self._database.fetch_one(
            "SELECT * FROM users WHERE email = ?", (email,)
        )
        return None if row is None else _to_user(row)


def _to_user(row: aiosqlite.Row) -> User:
    return User(
        id=UUID(row["id"]),
        email=row["email"],
        password_hash=row["password_hash"],
        created_at=from_text(row["created_at"]),
    )
