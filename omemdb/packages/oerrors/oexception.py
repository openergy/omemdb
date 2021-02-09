import abc
import inspect

NON_FIELD_KEY = "GLOBAL"


class Code:
    def __init__(self, error_code, status_code):
        self.error_code = error_code
        self.status_code = status_code


class BaseCodes:
    validation_error = Code("ValidationError", 400)
    not_found = Code("NotFound", 404)
    permission_denied = Code("PermissionDenied", 403)
    unauthorized = Code("Unauthorized", 401)
    server_error = Code("ServerError", 500)


class Levels:
    warning = "warning"
    error = "error"


class OException(Exception, abc.ABC):
    def __str__(self):
        code = self.detailed_code if self.detailed_code is not None else self.code.error_code
        msg = f"{self.level.upper()}: "
        msg += f"{code} on instance {self.instance}:\n"
        msg += f"{self.message}"
        msg += "\n" if self.extra else ""
        msg += "\n".join([f"| {key}: {value}" for key, value in self.extra.items()])
        return msg

    @staticmethod
    def json_to_pretty_str(d):
        return ("ERROR " if d["level"] == Levels.error else "WARNING ") + d["detailed_code"] + ": " + d["message"]

    def pretty_str(self):
        return self.json_to_pretty_str(self.to_dict())

    def __init__(self, code, instance, message, warning=False, extra=None):
        """
        Parameters
        ----------
        instance: str
        message: str
        extra
        """
        extra = extra if extra is not None else dict()
        self.code = code
        self.instance = instance
        self.message = message
        self.extra = extra
        self.level = Levels.warning if warning else Levels.error

        # manage detailed codes
        mro = inspect.getmro(self.__class__)
        self.detailed_code = mro[-6].__name__ if len(mro) == 6 else mro[-7].__name__

    def to_dict(self):
        """
        Returns
        -------
        dict
        """
        return dict(
            level=self.level,
            code=self.code.error_code,
            instance=self.instance,
            message=self.message,
            extra=self.extra,
            detailed_code=self.detailed_code
        )

    def prepend_chapter_to_instance(self, chapter_name, instance_separator="/"):
        self.instance = f"{instance_separator}{chapter_name}{self.instance}"
