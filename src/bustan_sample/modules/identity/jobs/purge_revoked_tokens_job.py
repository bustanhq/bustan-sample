from dataclasses import dataclass

from bustan import Injectable, Logger, LogLevel

from bustan_sample.platform.clock import Clock
from bustan_sample.platform.jobs import JobQueue, JobScheduler

from ..domain.revoked_token_repository import RevokedTokenRepository

SCHEDULE_NAME = "identity.purge_revoked_tokens"
CRON = "*/10 * * * *"


@dataclass(frozen=True, slots=True)
class PurgeRevokedTokensJob:
    pass


@Injectable()
class PurgeRevokedTokensHandler:
    """Removes the revoked token ids of expired tokens, each 10 minutes.

    An expired token fails the expiry check, thus its entry in the store has
    no more use.
    """

    def __init__(
        self,
        jobs: JobQueue,
        scheduler: JobScheduler,
        revoked: RevokedTokenRepository,
        clock: Clock,
    ) -> None:
        self._jobs = jobs
        self._scheduler = scheduler
        self._revoked = revoked
        self._clock = clock
        self._logger = Logger("PurgeRevokedTokens")

    def on_module_init(self) -> None:
        self._jobs.register(PurgeRevokedTokensJob, self.run)
        self._scheduler.schedule(SCHEDULE_NAME, CRON, PurgeRevokedTokensJob)

    async def run(self, job: PurgeRevokedTokensJob) -> None:
        removed = await self._revoked.purge(self._clock.now())
        self._logger.record(
            LogLevel.LOG, "revoked tokens purged", fields={"removed": removed}
        )
