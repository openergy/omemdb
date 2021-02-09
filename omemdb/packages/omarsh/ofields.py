import re
import datetime as dt
import json
import collections
import inspect

from marshmallow import fields
import numpy as np
import pandas as pd

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def make_generic(category, instant):
    """
    Parameters
    ----------
    category: 'day', 'year'
    instant: datetime or time
    """
    if isinstance(instant, dt.datetime):
        if category == "day":
            return instant.replace(year=2012, month=1, day=1)
        if category == "year":
            return instant.replace(year=2012)

    # manage time if generic day
    if (category == "day") and isinstance(instant, dt.time):
        return dt.datetime.combine(dt.date(2012, 1, 1), instant)

    raise AttributeError(f"wrong category, instant couple: {category, instant}.")


def iso_parse_fct(x):
    return dt.datetime.strptime(x, ISO_FORMAT)


def epoch_parse_fct(x):
    return dt.datetime.utcfromtimestamp(x / 1000)


class _ImmutableDict(dict):
    def __setitem__(self, key, value):
        raise ValueError("can't change an immutable dict")


# --------------------------------------- marshmallow tweaks -----------------------------------------------------------
class Constant(fields.Constant):
    def __init__(self, constant, **kwargs):
        kwargs["allow_none"] = True
        super().__init__(constant, **kwargs)

    def deserialize(self, value, attr=None, data=None):
        return self.constant


# --------------------------------------- custom fields ----------------------------------------------------------------
class RefField(fields.String):
    pattern = re.compile(r"[a-z\d_]*")
    max_length = None

    default_error_messages = {
        "invalid_ref": f"Invalid ref, does not match expected regex pattern: '{pattern}'",
        "too_short": "Must not be empty.",
        "too_long": f"Longer than maximum length ({max_length})."
    }

    def _deserialize(self, value, attr, data):
        value = super()._deserialize(value, attr, data).lower()
        if (value is None) or (self.pattern.fullmatch(value) is None):
            self.fail("invalid_ref")
        if len(value) == 0:
            self.fail("too_short")
        if self.max_length is not None and len(value) > self.max_length:
            self.fail("too_long")

        return value


class Tuple(fields.List):
    def _deserialize(self, value, attr, data):
        return tuple(super()._deserialize(value, attr, data))


class NumpyArray(fields.Field):
    default_error_messages = {
        "invalid_numpy_array": "Is not a numpy array.",
    }

    def _serialize(self, value, attr, obj):
        return value.tolist() if value is not None else None

    def _deserialize(self, value, attr, data):
        if value is None:
            return None
        if not isinstance(value, np.ndarray):
            try:
                value = np.array(value)
            except (ValueError, AttributeError):
                self.fail("invalid_numpy_array")

        # freeze
        value.flags.writeable = False
        return value


class TimeSeries(fields.Field):
    default_error_messages = {
        "invalid_series": "Is not a pandas series.",
        "invalid_time_index": "Does not have a datetime index."
    }

    def __init__(self, date_format="iso", generic=None, dtype=None, *args, **kwargs):
        """
        Parameters
        ----------
        date_format: str, default None
            'iso', 'epoch'
        generic: str, default None
            'day', 'year'
        """
        self._generic = generic
        self._date_format = date_format
        self._dtype = dtype
        super().__init__(*args, **kwargs)

    def _serialize(self, value, attr, obj):
        if value is None:
            return None
        # convert to pandas json
        json_str = value.to_json(orient="split", date_unit="ms", date_format=self._date_format)

        # convert to json data (sort to prevent random order...)
        json_data = collections.OrderedDict(sorted(json.loads(json_str).items()))

        return json_data

    def _deserialize(self, value, attr, data):
        if value is None:
            return None

        # manage json_data
        if not isinstance(value, pd.Series):
            # check dict
            if not isinstance(value, dict):
                self.fail("invalid_series")

            # check keys
            if len({"data", "index", "name"}.intersection(value.keys())) != 3:
                self.fail("invalid_series")

            # parse index
            if self._date_format == "iso":
                parse_fct = iso_parse_fct
            elif self._date_format == "epoch":
                parse_fct = epoch_parse_fct
            else:
                raise AssertionError("should not be here")

            try:
                index = list(map(lambda x: x if isinstance(x, dt.datetime) else parse_fct(x), value["index"]))
            except ValueError:
                self.fail("invalid_time_index")

            # make a series
            try:
                value = pd.Series(data=value["data"], index=index, name=value["name"], dtype=self._dtype)
            except (ValueError, KeyError):
                self.fail("invalid_series")

        # check if time series
        if len(value) > 0 and not isinstance(value.index, pd.DatetimeIndex):
            self.fail("invalid_time_index")

        # make generic if needed
        if self._generic:
            value.index = value.index.map(lambda x: make_generic(self._generic, x))

        # cast values
        value = value.astype(self._dtype)

        # freeze
        value.values.flags.writeable = False

        return value


class DateTime(fields.DateTime):
    def __init__(self, generic=None, format=None, **kwargs):
        """
        Parameters
        ----------
        generic: str, default None
            'day', 'year'
        format
        """
        _format = format or ISO_FORMAT
        self._generic = generic
        super().__init__(format=_format, **kwargs)

    def _deserialize(self, value, attr, data):
        if not isinstance(value, dt.datetime):
            # call parent
            value = super()._deserialize(value, attr, data)

        # manage generic if needed
        if self._generic:
            return make_generic(self._generic, value)

        return value

    def _serialize(self, value, attr, obj):
        return super()._serialize(value, attr, obj)


class LocalDateTime(fields.LocalDateTime):
    def _deserialize(self, value, attr, data):
        if isinstance(value, dt.datetime):
            return value
        return super()._deserialize(value, attr, data)


class TimeDelta(fields.TimeDelta):
    def _deserialize(self, value, attr, data):
        if isinstance(value, dt.timedelta):
            return value
        return super()._deserialize(value, attr, data)


class Time(fields.Time):
    def _deserialize(self, value, attr, data):
        if isinstance(value, dt.datetime):
            return value.time()
        if isinstance(value, dt.time):
            return value
        return super()._deserialize(value, attr, data)


class Date(fields.Date):
    def _deserialize(self, value, attr, data):
        if isinstance(value, dt.datetime):
            return value.date()
        if isinstance(value, dt.date):
            return value
        return super()._deserialize(value, attr, data)


class PythonScript(fields.String):
    def _deserialize(self, value, attr, data):
        if callable(value):
            value = inspect.getsource(value)
        value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
        return super()._deserialize(value, attr, data)


class FlexibleField(fields.Field):
    def __init__(self, serializer=None, **kwargs):
        self._serializer = serializer
        super().__init__(**kwargs)

    def _serialize(self, value, attr, obj):
        value = super()._serialize(value, attr, obj)
        if self._serializer is not None:
            value = self._serializer(value)
        return value
