from typing import cast

from bustan import ExecutionContext, create_param_decorator

from ..domain.authenticated_user import AuthenticatedUser


def _current_user(data: object | None, context: object) -> AuthenticatedUser:
    # The policy guard puts the principal on the request after the
    # authenticator accepts the token. The binder reads it after the guard.
    request = cast(ExecutionContext, context).request
    principal = None if request is None else getattr(request.state, "principal", None)
    if not isinstance(principal, AuthenticatedUser):
        raise TypeError('CurrentUser is only correct on a route with @Auth("bearer")')
    return principal


CurrentUser = create_param_decorator(_current_user, name="CurrentUser")
"""Give the handler the AuthenticatedUser of the request.

Use it as Annotated[AuthenticatedUser, CurrentUser()] on a route that has
@Auth("bearer").
"""
