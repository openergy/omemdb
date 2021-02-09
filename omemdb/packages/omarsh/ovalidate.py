import operator
import json

from marshmallow import validate, exceptions


class Range(validate.Validator):
    """
    Re-coded by Openergy (strict bounds option) and omarsh custom message.

    Validator which succeeds if the value it is passed is greater
    or equal to ``min`` and less than or equal to ``max``. If ``min``
    is not specified, or is specified as `None`, no lower bound
    exists. If ``max`` is not specified, or is specified as `None`,
    no upper bound exists.

    :param min: The minimum value (lower bound). If not provided, minimum
        value will not be checked.
    :param max: The maximum value (upper bound). If not provided, maximum
        value will not be checked.
    :param str error: Error message to raise in case of a validation error.
        Can be interpolated with `{input}`, `{min}` and `{max}`.
    """
    # fixme: [GL] test

    def __init__(self, min=None, max=None, error=None, min_strict=False, max_strict=False):
        self.min = min
        self.max = max
        self.error = error
        self.min_strict = min_strict
        self.max_strict = max_strict

    def _repr_args(self):
        return 'min={0!r}, max={1!r}'.format(self.min, self.max)

    def _format_error(self, value, message):
        return (self.error or message).format(
            input=value,
            min=self.min,
            max=self.max,
            min_operator=">" if self.min_strict else ">=",
            max_operator="<" if self.max_strict else "<="
        )

    def __call__(self, value):
        min_greater = operator.gt if self.min_strict else operator.ge
        max_lower = operator.lt if self.max_strict else operator.le

        # check if ok
        if (
                ((self.min is not None) and not min_greater(value, self.min))
                or (self.max is not None and not max_lower(value, self.max))
        ):
            raise exceptions.ValidationError(json.dumps(dict(
                __omarsh__=self.__class__.__name__,
                value=str(value),
                min_value=self.min,
                max_value=self.max,
                min_strict=self.min_strict,
                max_strict=self.max_strict
            )))

        return value


class Equal(validate.Equal):
    def __call__(self, value):
        if value != self.comparable:
            raise exceptions.ValidationError(json.dumps(dict(
                __omarsh__=self.__class__.__name__,
                value=str(value),
                expected=str(self.comparable)
            )))
        return value
