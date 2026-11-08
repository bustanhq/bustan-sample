# Add an adapter for an external API

This guide adds an adapter that calls an HTTP API, in the same way as
`platform/mail/resend_mailer.py`.

1. Find the port. The adapter implements a port of the domain or of the
   platform, for example `Mailer`. If the port does not exist, write it as an
   ABC in `domain/`, with no HTTP type in its signature.

2. Write the adapter in `infra/` of the module, or in the platform module of
   the port. Give it the `HttpClientFactory` and its configuration values:

   ```python
   class WeatherClient(WeatherSource):
       def __init__(self, http: HttpClientFactory, api_key: str) -> None:
           self._http, self._api_key = http, api_key
           self._client: HttpClient | None = None

       async def on_module_init(self) -> None:
           self._client = self._http.make(
               "weather",
               "https://api.example.com",
               headers={"Authorization": f"Bearer {self._api_key}"},
           )

       async def on_module_destroy(self) -> None:
           if self._client is not None:
               await self._client.aclose()
   ```

3. In each method, call `self._client.request(...)`, then
   `raise_for_response(service, response)`. If the API gives a status a
   special meaning, read the status before the call to `raise_for_response`.
   Raise `ExternalServiceError` with the correct `retryable` value.

4. Add the configuration keys to `app_settings.py`: a backend selector and the
   credentials, with the module prefix. Add a model validator that stops the
   start if the selected adapter has no credentials. Add each key to
   `.env.example` and `docs/reference/configuration.md`.

5. In `<module>_module.py`, import `HttpModule`, and bind the port with a
   `FactoryProvider` that makes only the selected adapter.

6. If the call changes something in the other system, make it in a job. In
   the job handler, change `ExternalServiceError` into `PermanentJobError`
   or `RetryJobLater`. Give the API the idempotency key of the work, if the
   API accepts one. Do not retry in the adapter.

7. Write the tests with a fake API:

   ```python
   factory = HttpClientFactory(httpx2.MockTransport(handler))
   ```

   The handler receives each `httpx2.Request` and returns an
   `httpx2.Response`, or raises `httpx2.ReadTimeout` for a timeout. Examine
   the request (method, path, headers, JSON) and the retry decision for each
   status. No test calls the network.

8. Run the checks:

   ```bash
   uv run ruff check . && uv run ty check && uv run pytest -q
   ```

## Do not

- Do not put the external API in the readiness probe. A provider that is
  down must not take the service out of rotation.
- Do not log a header, a query or a body. They can contain a credential or
  personal data. `HttpClient` logs the method, the path, the status and the
  duration.
- Do not keep a database transaction open during an external call. The
  transaction keeps the database lock of the process.
