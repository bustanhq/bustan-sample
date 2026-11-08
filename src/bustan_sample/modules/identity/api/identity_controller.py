from typing import Annotated

from bustan import (
    ApiBearerAuth,
    ApiOperation,
    ApiResponse,
    ApiTags,
    Auth,
    Controller,
    Get,
    HttpResponse,
    Post,
    Public,
    UseFilters,
)

from ..application.get_current_user_query import (
    GetCurrentUserHandler,
    GetCurrentUserQuery,
)
from ..application.log_in_command import LogInCommand, LogInHandler
from ..application.log_out_command import LogOutCommand, LogOutHandler
from ..application.register_user_command import (
    RegisterUserCommand,
    RegisterUserHandler,
)
from ..domain.authenticated_user import AuthenticatedUser
from .bearer_authenticator import STRATEGY
from .current_user import CurrentUser
from .identity_errors_filter import IdentityErrorsFilter
from .identity_schemas import LogInRequest, RegisterRequest, TokenResponse, UserResponse


# All routes need a token, except the two routes with @Public(). Thus only the
# routes that need a token have @ApiBearerAuth() in the OpenAPI document.
@UseFilters(IdentityErrorsFilter())
@Controller("/identity")
@Auth(STRATEGY)
@ApiTags("identity")
class IdentityController:
    def __init__(
        self,
        register_user: RegisterUserHandler,
        log_in: LogInHandler,
        log_out: LogOutHandler,
        get_current_user: GetCurrentUserHandler,
    ) -> None:
        self._register_user = register_user
        self._log_in = log_in
        self._log_out = log_out
        self._get_current_user = get_current_user

    @Post("/register")
    @Public()
    @ApiOperation(summary="Register a user")
    @ApiResponse(status=201, description="The new user", schema=UserResponse)
    @ApiResponse(status=400, description="The email or the password is not valid")
    @ApiResponse(status=409, description="A user with this email exists")
    async def register(self, payload: RegisterRequest) -> HttpResponse:
        user = await self._register_user.execute(
            RegisterUserCommand(email=payload.email, password=payload.password)
        )
        return HttpResponse.json(
            UserResponse.from_user(user).to_json(), status_code=201
        )

    @Post("/login")
    @Public()
    @ApiOperation(summary="Log in and get an access token")
    @ApiResponse(status=200, description="A bearer token", schema=TokenResponse)
    @ApiResponse(status=401, description="The email or the password is not correct")
    async def log_in(self, payload: LogInRequest) -> dict[str, object]:
        token = await self._log_in.execute(
            LogInCommand(email=payload.email, password=payload.password)
        )
        return TokenResponse.from_token(token).to_json()

    @Post("/logout")
    @ApiBearerAuth()
    @ApiOperation(summary="Revoke the token of this request")
    @ApiResponse(status=204, description="The token is revoked")
    @ApiResponse(status=401, description="No valid token")
    async def log_out(self, user: Annotated[AuthenticatedUser, CurrentUser()]) -> None:
        # A handler that returns None answers 204 No Content.
        await self._log_out.execute(
            LogOutCommand(
                token_id=user.token_id, token_expires_at=user.token_expires_at
            )
        )

    @Get("/me")
    @ApiBearerAuth()
    @ApiOperation(summary="Get the user of the token")
    @ApiResponse(status=200, description="The user", schema=UserResponse)
    @ApiResponse(status=401, description="No valid token")
    async def me(
        self, user: Annotated[AuthenticatedUser, CurrentUser()]
    ) -> dict[str, object]:
        found = await self._get_current_user.execute(GetCurrentUserQuery(user.user_id))
        return UserResponse.from_user(found).to_json()
