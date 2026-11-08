from collections.abc import Mapping
from importlib.metadata import PackageNotFoundError, version

import httpx2

from .http_client import HttpClient

# connect: the time to open a connection. The other limits: each read, write
# and wait for a pooled connection. A call that waits longer fails as a timeout.
DEFAULT_TIMEOUT = httpx2.Timeout(10.0, connect=2.0)
DEFAULT_LIMITS = httpx2.Limits(max_connections=20, max_keepalive_connections=10)


def _user_agent() -> str:
    try:
        return f"bustan-sample/{version('bustan-sample')}"
    except PackageNotFoundError:
        return "bustan-sample"


class HttpClientFactory:
    """Makes the HttpClient of each external API.

    Each client gets the same timeouts, connection limits, User-Agent and log
    records. One client for each API keeps the base URL, the credentials and
    the connection pool of each API apart.

    Give a transport to replace the network, for example httpx2.MockTransport
    in a test. Without a given transport, a proxy in HTTPS_PROXY or HTTP_PROXY
    applies to each client.
    """

    def __init__(self, transport: httpx2.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    def make(
        self,
        service: str,
        base_url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: httpx2.Timeout = DEFAULT_TIMEOUT,
    ) -> HttpClient:
        """Return a client for the API at base_url. The caller closes it with aclose()."""
        client = httpx2.AsyncClient(
            base_url=base_url,
            headers={"User-Agent": _user_agent(), **(headers or {})},
            timeout=timeout,
            limits=DEFAULT_LIMITS,
            transport=self._transport,
            # A given transport replaces the network. A proxy of the
            # environment must not take its requests.
            trust_env=self._transport is None,
        )
        return HttpClient(service, client)
