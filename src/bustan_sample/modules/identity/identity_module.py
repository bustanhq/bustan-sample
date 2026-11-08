from bustan import AUTHENTICATOR_REGISTRY, ClassProvider, FactoryProvider, Module

from bustan_sample.platform.clock import ClockModule
from bustan_sample.platform.events import EventsModule
from bustan_sample.platform.jobs import JobsModule
from bustan_sample.platform.mail import MailModule

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
from .jobs.purge_revoked_tokens_job import PurgeRevokedTokensHandler
from .jobs.send_welcome_email_job import SendWelcomeEmailHandler
from .listeners.on_user_registered import OnUserRegistered


def _authenticators(bearer: BearerAuthenticator) -> dict[str, object]:
    return {STRATEGY: bearer}


# The module binds each domain port to an infra adapter. It exports the
# authenticator registry: a module that imports IdentityModule can put
# @Auth("bearer") on its routes. JwtTokenIssuer and the job queue read
# ConfigService, which the global ConfigModule of the root module gives.
#
# The event handlers and the job handlers subscribe, register and schedule in
# their on_module_init hooks. Thus each one is only a line in providers.
@Module(
    imports=[ClockModule, EventsModule, JobsModule, MailModule],
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
        OnUserRegistered,
        SendWelcomeEmailHandler,
        PurgeRevokedTokensHandler,
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
