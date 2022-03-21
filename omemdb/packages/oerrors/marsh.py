import inspect
import itertools
import json

from omemdb.packages.omarsh import Schema, fields, ValidationError as OMarshValidationError, validate
from omemdb.packages.omarsh.no_validation_unmarshaller import deserialize_field

from . import validation_errors
from .oexception_collection import OExceptionCollection


class MarshValidator:
    def __init__(self, schema_cls_or_field, root_instance="/", instance_sep="/"):
        # store schema / field descriptor
        if inspect.isclass(schema_cls_or_field) and issubclass(schema_cls_or_field, Schema):
            # schema_cls -> we instantiate
            schema_cls_or_field = schema_cls_or_field()
        self.schema = schema_cls_or_field if isinstance(schema_cls_or_field, Schema) else None
        self.field_descriptor = schema_cls_or_field if isinstance(schema_cls_or_field, fields.Field) else None

        if self.schema is None and self.field_descriptor is None:
            raise TypeError("schema_cls_or_field must be a omarsh schema or field")

        # store root instance and instance sep
        self.root_instance = root_instance
        self.instance_sep = instance_sep

    def validate(self, data_or_value, skip_validation=False):
        # load
        if self.schema is not None:
            result = self.schema.load(data_or_value, skip_validation=skip_validation)
            data, errors = result.data, result.errors
        else:
            try:
                data, errors = deserialize_field(
                    self.field_descriptor,
                    data_or_value,
                    skip_validation=skip_validation
                ), {}
            except OMarshValidationError as e:
                data, errors = None, [str(msg) for msg in e.messages]

        oec = OExceptionCollection()
        oec.extend(self._marsh_errors_to_oexception_errors(self.root_instance, errors, instance_sep=self.instance_sep))

        # return
        return data, oec

    def _marsh_errors_to_oexception_errors(self, current_instance, marsh_errors, instance_sep="/"):
        # if dict, nested schema, we create errors recursively
        if isinstance(marsh_errors, dict):
            return list(itertools.chain(*(
                self._marsh_errors_to_oexception_errors(
                    current_instance + f"{instance_sep}{key}",
                    _marsh_errors,
                    instance_sep=instance_sep
                )
                for key, _marsh_errors in marsh_errors.items()
            )))

        # create and return errors
        return [
            self._get_oexception_from_marsh_message(marsh_message, current_instance)
            for marsh_message in marsh_errors
        ]

    @classmethod
    def _get_oexception_from_marsh_message(cls, marsh_message, current_instance):
        conversion_map = cls._get_error_conversion_map()
        if marsh_message in conversion_map:
            oexception_cls = conversion_map[marsh_message]
            return oexception_cls(current_instance, marsh_message)
        elif "__omarsh__" in marsh_message:  # we found a custom omarsh message, we use it
            return _omarsh_message_to_oexception(marsh_message, current_instance)
        raise ValueError(f"unknown marsh message: '{marsh_message}'")

    @classmethod
    def _get_error_conversion_map(cls):  # may be subclassed
        return _marsh_message_to_oexception_cls


_marsh_message_to_oexception_cls = {
    # -- MARSHMALLOW FIELDS MESSAGES --
    # Field
    fields.Field.default_error_messages["required"]: validation_errors.FieldRequired,  # "Missing data for required field.",
    fields.Field.default_error_messages["type"]: validation_errors.InvalidType,  # "Invalid input type.",
    fields.Field.default_error_messages["null"]: validation_errors.Null,  # "Field may not be null.",
    fields.Field.default_error_messages["validator_failed"]: validation_errors.InvalidValue,  # "Invalid value.",

    # List
    fields.List.default_error_messages["invalid"]: validation_errors.InvalidList,  # "Not a valid list.",

    # Dict
    fields.Dict.default_error_messages["invalid"]: validation_errors.InvalidDict,  # "Not a valid dict."

    # String
    fields.String.default_error_messages["invalid"]: validation_errors.InvalidString,  # "Not a valid string.",
    fields.String.default_error_messages["invalid_utf8"]: validation_errors.InvalidUtf8String,  # "Not a valid utf-8 string.",

    # UUID
    fields.UUID.default_error_messages["invalid_uuid"]: validation_errors.InvalidUuid,  # "Not a valid UUID.",
    # fixme: remove invalid_guid in marshmallow 3.0
    fields.UUID.default_error_messages["invalid_guid"]: validation_errors.InvalidUuid,  # "Not a valid UUID.",

    # Number
    fields.Number.default_error_messages["invalid"]: validation_errors.InvalidNumber,  # "Not a valid number.",

    # Integer
    fields.Integer.default_error_messages["invalid"]: validation_errors.InvalidInteger,  # "Not a valid integer.",

    # Decimal
    fields.Decimal.default_error_messages["special"]: validation_errors.InvalidSpecialDecimal,  # "Special numeric values are not permitted.",

    # Boolean
    fields.Boolean.default_error_messages["invalid"]: validation_errors.InvalidBoolean,  # "Not a valid boolean.",

    # FormattedString
    fields.FormattedString.default_error_messages["format"]: validation_errors.InvalidFormattedString,  # "Cannot format string with given data.",

    # DateTime
    fields.DateTime.default_error_messages["invalid"]: validation_errors.InvalidDatetime,  # "Not a valid datetime.",
    fields.DateTime.default_error_messages["format"]: validation_errors.InvalidDatetime,  # "'{input}' cannot be formatted as a datetime.",

    # Time
    fields.Time.default_error_messages["invalid"]: validation_errors.InvalidTime,  # "Not a valid time.",
    fields.Time.default_error_messages["format"]: validation_errors.InvalidTime,  # "'{input}' cannot be formatted as a time.",

    # Date
    fields.Date.default_error_messages["invalid"]: validation_errors.InvalidDate,  # "Not a valid date.",
    fields.Date.default_error_messages["format"]: validation_errors.InvalidDate,  # "'{input}' cannot be formatted as a date.",

    # TimeDelta
    fields.TimeDelta.default_error_messages["invalid"]: validation_errors.InvalidTimedelta,  # "Not a valid period of time.",
    fields.TimeDelta.default_error_messages["format"]: validation_errors.InvalidTimedelta,  # "{input!r} cannot be formatted as a timedelta.",

    # Url
    fields.Url.default_error_messages["invalid"]: validation_errors.InvalidUrl,  # "Not a valid URL.",

    # Email
    fields.Email.default_error_messages["invalid"]: validation_errors.InvalidEmail, # "Not a valid email address.",


    # -- OMEMDB FIELDS MESSAGES --
    # RefField
    fields.RefField.default_error_messages["invalid_ref"]: validation_errors.InvalidRef,
    fields.RefField.default_error_messages["too_short"]: validation_errors.MinLengthNotReached,
    fields.RefField.default_error_messages["too_long"]: validation_errors.MaxLengthExceeded,

    # Numpy Array
    fields.NumpyArray.default_error_messages["invalid_numpy_array"]: validation_errors.InvalidNumpyArray,

    # TimeSeries
    fields.TimeSeries.default_error_messages["invalid_series"]: validation_errors.InvalidSeries,
    fields.TimeSeries.default_error_messages["invalid_time_index"]: validation_errors.InvalidTimeIndex,

    # -- MARSHMALLOW VALIDATE MESSAGE --
    validate.URL.default_message: validation_errors.InvalidUrl,
    validate.Email.default_message: validation_errors.InvalidEmail,
    validate.Length.message_min: validation_errors.MinLengthNotReached,
    validate.Length.message_max: validation_errors.MaxLengthExceeded,
    validate.Length.message_all: validation_errors.InvalidLength,
    validate.Length.message_equal: validation_errors.InvalidLength,
    validate.Equal.default_message: validation_errors.NotEqualTo,
    validate.Regexp.default_message: validation_errors.InvalidPattern,
    validate.Predicate.default_message: validation_errors.InvalidValue,
    validate.NoneOf.default_message: validation_errors.ForbiddenValue,
    validate.OneOf.default_message: validation_errors.InvalidChoice,
    validate.ContainsOnly.default_message: validation_errors.InvalidChoice,
}


def _omarsh_message_to_oexception(omarsh_message, instance):
    data = json.loads(omarsh_message)

    if data["__omarsh__"] == "Range":
        return validation_errors.RangeNotRespected(
            instance,
            value=data["value"],
            min_value=data["min_value"],
            max_value=data["max_value"],
            min_strict=data["min_strict"],
            max_strict=data["max_strict"]
        )

    if data["__omarsh__"] == "Equal":
        return validation_errors.NotEqualTo(
            instance,
            value=data["value"],
            expected=data["expected"]
        )

    raise ValueError(f"unknown __omarsh__ code: {data['__omarsh__']}")
