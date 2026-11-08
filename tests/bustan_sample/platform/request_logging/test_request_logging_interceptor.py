import json
import logging

from bustan import Controller, Get, Module
from bustan.testing import AsgiTestClient, create_test_app

from bustan_sample.platform.request_logging import RequestLoggingModule


@Controller("/probe")
class ProbeController:
    @Get("/ok")
    async def ok(self) -> dict[str, str]:
        return {"status": "ok"}

    @Get("/fail")
    async def fail(self) -> dict[str, str]:
        raise RuntimeError("the probe failed on purpose")


@Module(imports=[RequestLoggingModule], controllers=[ProbeController])
class ProbeModule:
    pass


class _RequestLogRecords(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[dict[str, object]] = []

    def emit(self, record: logging.LogRecord) -> None:
        # The framework also writes plain-text records to this logger, for
        # example for an unhandled exception. The test ignores them.
        try:
            payload = json.loads(record.getMessage())
        except ValueError:
            return
        if payload.get("context") == "RequestLogging":
            self.records.append(payload)


def _records_for(path: str) -> list[dict[str, object]]:
    handler = _RequestLogRecords()
    logger = logging.getLogger("bustan")
    logger.addHandler(handler)
    try:
        with AsgiTestClient(create_test_app(ProbeModule)) as client:
            client.get(path)
    finally:
        logger.removeHandler(handler)
    return handler.records


def test_a_handled_request_writes_one_record() -> None:
    [record] = _records_for("/probe/ok")
    assert record["method"] == "GET"
    assert record["path"] == "/probe/ok"
    assert record["handler"] == "ProbeController.ok"
    assert record["outcome"] == "ok"
    assert isinstance(record["duration_ms"], float)


def test_a_failed_handler_writes_an_error_outcome() -> None:
    [record] = _records_for("/probe/fail")
    assert record["handler"] == "ProbeController.fail"
    assert record["outcome"] == "error"
