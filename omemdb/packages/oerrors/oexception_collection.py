import contextlib
import itertools
import warnings
import textwrap

from .oexception import OException, Levels, NON_FIELD_KEY
from .base_errors import ValidationError
from .conf import CONF


class OExceptionCollection(Exception):
    def __init__(self, exceptions_l=None, instance_separator="/", **extra):
        self.exceptions = dict()  # {instance: [errors, ...], ...
        super().__init__()
        if exceptions_l is not None:
            self.extend(exceptions_l)
        self.instance_separator = instance_separator
        self.extra = extra

    def __str__(self):
        msg = "\n"
        msg += "\n".join((f"|{key}: {value}" for key, value in self.extra.items())) + "\n" if self.extra else ""
        msg += "\n".join([
            f"{key}:\n    " + "\n    ".join([str(v).replace("\n", "\n    ") for v in value])
            for key, value in self.exceptions.items()
        ])
        return msg

    def __len__(self):
        return len(self.exceptions)

    def __iter__(self):
        return itertools.chain.from_iterable(self.exceptions.values())

    def __contains__(self, item):
        if not isinstance(item, OException):
            return False
        if item.instance not in self.exceptions:
            return False
        return item in self.exceptions[item.instance]

    @property
    def level(self):
        if Levels.error in [e.level for e in self]:
            return Levels.error
        return Levels.warning

    @property
    def error(self):
        return self.level == Levels.error

    @staticmethod
    def json_to_pretty_str(d):
        errors = d["errors"].copy()
        ret = ""
        if NON_FIELD_KEY in errors:
            for exc in errors.pop(NON_FIELD_KEY):
                ret += OException.json_to_pretty_str(exc) + "\n"
        for key, value in errors.items():
            ret += " ⟶ ".join(key.strip("/").split("/")) + ":"
            for exc in value:
                ret += "\n" + textwrap.indent(OException.json_to_pretty_str(exc), "  ")
            ret += "\n"
        return ret

    def pretty_str(self):
        return self.json_to_pretty_str(self.to_dict())

    def append(self, exc):
        """
        Parameters
        ----------
        exc: typing.Union[OException, OExceptionCollection]

        Will only be appended if exception is not there yet.
        """
        if isinstance(exc, OException):
            # add to exceptions
            if exc.instance not in self.exceptions:
                self.exceptions[exc.instance] = []
            if exc not in self.exceptions[exc.instance]:
                self.exceptions[exc.instance].append(exc)
        elif isinstance(exc, OExceptionCollection):
            self.extra.update(exc.extra)
            self.extend(exc)
        else:
            raise TypeError("exc must be an OException")

    def extend(self, several_exc):
        for exc in several_exc:
            self.append(exc)

    def add_extra(self, **extra):
        self.extra.update(extra)

    def to_dict(self):
        if "errors" in self.extra:
            del self.extra["errors"]
        return dict(errors={key: [v.to_dict() for v in value] for key, value in self.exceptions.items()}, **self.extra)

    def get_status_code(self):
        return max([e.code.status_code for e in self])

    def reduce_instance_paths_for_validation_errors(self):
        exceptions = dict()
        for instance, exc_l in self.exceptions.items():
            for e in exc_l:
                if isinstance(e, ValidationError):
                    e.instance = instance.strip("/").split("/")[-1]
                if e.instance in exceptions:
                    exceptions[e.instance].append(e)
                else:
                    exceptions[e.instance] = [e]
        self.exceptions = exceptions

    def exception_list(self):
        return list(self)

    def raise_if_error(self, warn=False):
        if self.level == Levels.error:
            if CONF.show_full_traceback:
                raise self
            else:
                raise self from None
        if warn:
            self.warn_if_warning()

    def warn_if_warning(self):
        if Levels.warning in {e.level for e in self}:
            warnings.warn(str(self), stacklevel=2)

    @contextlib.contextmanager
    def _dev_catch_errors(self, raise_if_error=False, warn=False):
        try:
            yield
        except (OException, OExceptionCollection) as e:
            self.append(e)
        if raise_if_error:
            self.raise_if_error()
        if warn:
            self.warn_if_warning()

    def catch_errors(self, raise_if_error=False, warn=False, within_chapter=None):
        if within_chapter is None:
            return self._dev_catch_errors(raise_if_error=raise_if_error, warn=warn)
        with self.within_chapter(chapter=within_chapter) as chapter_oec:
            return chapter_oec._dev_catch_errors(raise_if_error=raise_if_error, warn=warn)

    @contextlib.contextmanager
    def within_chapter(self, chapter) -> "OExceptionCollection":
        chapter_oec = OExceptionCollection()
        try:
            with chapter_oec._dev_catch_errors(raise_if_error=False, warn=False):
                yield chapter_oec
        finally:
            for exc in chapter_oec:
                exc.prepend_chapter_to_instance(chapter, instance_separator=self.instance_separator)
                self.append(exc)
            chapter_oec.raise_if_error(warn=False)
