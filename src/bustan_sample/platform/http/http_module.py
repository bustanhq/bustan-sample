from bustan import FactoryProvider, Module

from .http_client_factory import HttpClientFactory


# Each module with an adapter for an external API imports this module. The
# factory makes one client for each API, and the adapter owns and closes its
# client. A test overrides HttpClientFactory with a factory that has a
# MockTransport, thus no test calls the network.
@Module(
    providers=[FactoryProvider(provide=HttpClientFactory, use_factory=HttpClientFactory)],
    exports=[HttpClientFactory],
)
class HttpModule:
    pass
