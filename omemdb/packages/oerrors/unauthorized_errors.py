from .base_errors import UnauthorizedError


class NotAuthenticated(UnauthorizedError):
    description = "You are not authenticated, please authenticate."


class AuthenticationFailed(UnauthorizedError):
    description = "Authentication failed, please check your credentials and try again."
