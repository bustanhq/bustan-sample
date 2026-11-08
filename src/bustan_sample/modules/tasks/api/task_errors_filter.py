from bustan import (
    ExceptionFilter,
    ExecutionContext,
    HttpResponse,
    ProblemDetailsExceptionFilter,
)
from bustan.errors import BadRequestException, NotFoundException

from ..domain.errors import InvalidTaskError, TaskNotFoundError


class TaskErrorsFilter(ExceptionFilter):
    """Changes the errors of the tasks domain into RFC 9457 problem details.

    The domain raises its own errors and does not know about HTTP. This filter
    gives each error its HTTP status. The framework filter writes the body, thus
    the body has the same shape as all other errors of the application.
    """

    exception_types = (TaskNotFoundError, InvalidTaskError)

    def __init__(self) -> None:
        self._problems = ProblemDetailsExceptionFilter()

    async def catch(self, exc: Exception, context: ExecutionContext) -> HttpResponse:
        if isinstance(exc, TaskNotFoundError):
            return await self._problems.catch(NotFoundException(str(exc)), context)
        return await self._problems.catch(BadRequestException(str(exc)), context)
