import asyncio
from uuid import uuid4

from support.fakes import RecordingJobQueue

from bustan_sample.modules.identity.application.on_user_registered import (
    OnUserRegistered,
)
from bustan_sample.modules.identity.application.send_welcome_email_job import (
    SendWelcomeEmailJob,
)
from bustan_sample.modules.identity.domain.events import UserRegistered
from bustan_sample.platform.clock import FixedClock
from bustan_sample.platform.events import EventBus


def test_a_new_user_gets_a_welcome_email_job() -> None:
    async def scenario() -> None:
        events, jobs, user_id = EventBus(), RecordingJobQueue(), uuid4()
        OnUserRegistered(events, jobs).on_module_init()
        await events.publish(
            UserRegistered(user_id, "ada@example.com", FixedClock().now())
        )
        await events.drain(1)
        assert jobs.enqueued == [SendWelcomeEmailJob(str(user_id), "ada@example.com")]

    asyncio.run(scenario())
