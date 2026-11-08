import time

from bustan import (
    CallHandler,
    ExecutionContext,
    Injectable,
    Interceptor,
    Logger,
    LogLevel,
)


@Injectable()
class RequestLoggingInterceptor(Interceptor):
    """Writes one log record for each request that a handler receives.

    The record gives the method, the path, the handler, the outcome and the
    duration. The framework adds the correlation id to each record.
    """

    def __init__(self) -> None:
        self._logger = Logger("RequestLogging")

    async def intercept(self, context: ExecutionContext, next: CallHandler) -> object:
        started = time.perf_counter()
        outcome = "error"
        try:
            result = await next.handle()
            outcome = "ok"
            return result
        finally:
            request = context.request
            handler = getattr(context.get_handler(), "__name__", "?")
            self._logger.record(
                LogLevel.LOG,
                "request handled",
                fields={
                    "method": request.method if request is not None else None,
                    "path": request.path if request is not None else None,
                    "handler": f"{context.get_class().__name__}.{handler}",
                    "outcome": outcome,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                },
            )
