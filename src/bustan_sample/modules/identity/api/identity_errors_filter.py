from bustan import (
    ExceptionFilter,
    ExecutionContext,
    HttpResponse,
    ProblemDetailsExceptionFilter,
)
from bustan.errors import (
    BadRequestException,
    ConflictException,
    HttpException,
    NotFoundException,
    UnauthorizedException,
)

from ..domain.errors import (
    EmailTakenError,
    InvalidCredentialsError,
    InvalidUserError,
    UserNotFoundError,
)

_HTTP_ERRORS: dict[type[Exception], type[HttpException]] = {
    EmailTakenError: ConflictException,
    InvalidCredentialsError: UnauthorizedException,
    InvalidUserError: BadRequestException,
    UserNotFoundError: NotFoundException,
}


class IdentityErrorsFilter(ExceptionFilter):
    """Changes the errors of the identity domain into RFC 9457 problem details."""

    exception_types = tuple(_HTTP_ERRORS)

    def __init__(self) -> None:
        self._problems = ProblemDetailsExceptionFilter()

    async def catch(self, exc: Exception, context: ExecutionContext) -> HttpResponse:
        http_error = _HTTP_ERRORS[type(exc)]
        return await self._problems.catch(http_error(str(exc)), context)
