import asyncio

from bustan.testing import create_testing_module

from bustan_sample.platform.http import HttpClientFactory, HttpModule


def test_the_module_gives_one_client_factory() -> None:
    async def scenario() -> None:
        compiled = await create_testing_module(HttpModule).compile()
        try:
            assert isinstance(compiled.get(HttpClientFactory), HttpClientFactory)
        finally:
            await compiled.close()

    asyncio.run(scenario())
