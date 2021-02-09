from .oexception import BaseCodes, OException


class ValidationError(OException):
    def __init__(self, instance, message, warning=False, **extra):
        """
        Parameters
        ----------
        instance: str
        message: str
        extra
        """
        super().__init__(
            BaseCodes.validation_error,
            instance,
            message,
            warning=warning,
            extra=extra
        )


class NotFoundError(OException):
    def __init__(self, instance, message, warning=False, **extra):
        """
        Parameters
        ----------
        instance: str
        message: str
        extra: dict
        """
        super().__init__(
            BaseCodes.not_found,
            instance,
            message,
            warning=warning,
            extra=extra
        )


class PermissionDeniedError(OException):
    def __init__(self, instance, message, warning=False, **extra):
        """
        Parameters
        ----------
        instance: str
        message: str
        extra: dict
        """
        super().__init__(
            BaseCodes.permission_denied,
            instance,
            message,
            warning=warning,
            extra=extra
        )


class UnauthorizedError(OException):
    def __init__(self, instance, message, warning=False, **extra):
        """
        Parameters
        ----------
        instance: str
        message: str
        extra: dict
        """
        super().__init__(
            BaseCodes.unauthorized,
            instance,
            message,
            warning=warning,
            extra=extra
        )


class ServerError(OException):
    def __init__(self, instance, message, warning=False, **extra):
        """
        Parameters
        ----------
        instance: str
        message: str
        extra: dict
        """
        super().__init__(
            BaseCodes.server_error,
            instance,
            message,
            warning=warning,
            extra=extra
        )

