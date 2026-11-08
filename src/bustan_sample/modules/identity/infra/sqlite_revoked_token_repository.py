from datetime import datetime

from bustan import Injectable

from bustan_sample.platform.database import Database, to_text

from ..domain.revoked_token_repository import RevokedTokenRepository

_SCHEMA = """
CREATE TABLE IF NOT EXISTS revoked_tokens (
    token_id TEXT PRIMARY KEY,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS revoked_tokens_by_expiry ON revoked_tokens (expires_at);
"""


@Injectable()
class SqliteRevokedTokenRepository(RevokedTokenRepository):
    """Keeps the revoked token ids in the table revoked_tokens of the SQLite database.

    All processes on the same database file see the same revoked tokens.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    async def on_module_init(self) -> None:
        await self._database.execute_script(_SCHEMA)

    async def revoke(self, token_id: str, expires_at: datetime) -> None:
        await self._database.execute(
            "INSERT OR REPLACE INTO revoked_tokens (token_id, expires_at) VALUES (?, ?)",
            (token_id, to_text(expires_at)),
        )

    async def is_revoked(self, token_id: str) -> bool:
        row = await self._database.fetch_one(
            "SELECT 1 FROM revoked_tokens WHERE token_id = ?", (token_id,)
        )
        return row is not None

    async def purge(self, now: datetime) -> int:
        return await self._database.execute(
            "DELETE FROM revoked_tokens WHERE expires_at <= ?", (to_text(now),)
        )
