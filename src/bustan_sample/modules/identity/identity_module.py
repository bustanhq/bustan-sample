from bustan import AUTHENTICATOR_REGISTRY, ClassProvider, FactoryProvider, Module

from bustan_sample.platform.clock import ClockModule

from .api.bearer_authenticator import STRATEGY, BearerAuthenticator
from .api.identity_controller import IdentityController
from .application.authenticate_token_query import AuthenticateTokenHandler
from .application.get_current_user_query import GetCurrentUserHandler
from .application.log_in_command import LogInHandler
from .application.log_out_command import LogOutHandler
from .application.register_user_command import RegisterUserHandler
from .domain.password_hasher import PasswordHasher
from .domain.revoked_token_repository import RevokedTokenRepository
from .domain.token_issuer import TokenIssuer
from .domain.user_repository import UserRepository
from .infra.argon2_password_hasher import Argon2PasswordHasher
from .infra.in_memory_revoked_token_repository import InMemoryRevokedTokenRepository
from .infra.in_memory_user_repository import InMemoryUserRepository
from .infra.jwt_token_issuer import JwtTokenIssuer


def _authenticators(bearer: BearerAuthenticator) -> dict[str, object]:
    return {STRATEGY: bearer}


# The module binds each domain port to an infra adapter. It exports the
# authenticator registry: a module that imports IdentityModule can put
# @Auth("bearer") on its routes. JwtTokenIssuer reads ConfigService, which the
# global ConfigModule of the root module gives.
@Module(
    imports=[ClockModule],
    controllers=[IdentityController],
    providers=[
        ClassProvider(provide=UserRepository, use_class=InMemoryUserRepository),
        ClassProvider(
            provide=RevokedTokenRepository, use_class=InMemoryRevokedTokenRepository
        ),
        ClassProvider(provide=PasswordHasher, use_class=Argon2PasswordHasher),
        ClassProvider(provide=TokenIssuer, use_class=JwtTokenIssuer),
        RegisterUserHandler,
        LogInHandler,
        LogOutHandler,
        GetCurrentUserHandler,
        AuthenticateTokenHandler,
        BearerAuthenticator,
        FactoryProvider(
            provide=AUTHENTICATOR_REGISTRY,
            use_factory=_authenticators,
            inject=(BearerAuthenticator,),
        ),
    ],
    exports=[AUTHENTICATOR_REGISTRY],
)
class IdentityModule:
    pass
