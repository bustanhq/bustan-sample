"""The public names of the identity module. Other modules import only these."""

from .api.bearer_authenticator import STRATEGY
from .api.current_user import CurrentUser
from .domain.authenticated_user import AuthenticatedUser
from .domain.events import UserRegistered
from .identity_module import IdentityModule

__all__ = [
    "STRATEGY",
    "AuthenticatedUser",
    "CurrentUser",
    "IdentityModule",
    "UserRegistered",
]
