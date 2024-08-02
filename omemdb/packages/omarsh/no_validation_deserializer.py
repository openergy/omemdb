from marshmallow import Schema
from marshmallow.utils import is_collection, missing, set_value
from marshmallow.exceptions import ValidationError, SCHEMA
from marshmallow.error_store import ErrorStore
from marshmallow.utils import RAISE, EXCLUDE, INCLUDE
from collections.abc import Mapping
import typing

_T = typing.TypeVar


# https://github.com/marshmallow-code/marshmallow/pull/1070/files

def _deserialize_no_validation(
        self,
        data: (
                typing.Mapping[str, typing.Any]
                | typing.Iterable[typing.Mapping[str, typing.Any]]
        ),
        *,
        error_store: ErrorStore,
        many: bool = False,
        partial=False,
        unknown=RAISE,
        index=None,
) -> _T | list[_T]:
    """Deserialize ``data``.

    :param dict data: The data to deserialize.
    :param ErrorStore error_store: Structure to store errors.
    :param bool many: `True` if ``data`` should be deserialized as a collection.
    :param bool|tuple partial: Whether to ignore missing fields and not require
        any fields declared. Propagates down to ``Nested`` fields as well. If
        its value is an iterable, only missing fields listed in that iterable
        will be ignored. Use dot delimiters to specify nested fields.
    :param unknown: Whether to exclude, include, or raise an error for unknown
        fields in the data. Use `EXCLUDE`, `INCLUDE` or `RAISE`.
    :param int index: Index of the item being serialized (for storing errors) if
        serializing a collection, otherwise `None`.
    :return: A dictionary of the deserialized data.
    """
    index_errors = self.opts.index_errors
    index = index if index_errors else None
    if many:
        if not is_collection(data):
            error_store.store_error([self.error_messages["type"]], index=index)
            ret_l = []  # type: typing.List[_T]
        else:
            ret_l = [
                typing.cast(
                    _T,
                    self._deserialize(
                        typing.cast(typing.Mapping[str, typing.Any], d),
                        error_store=error_store,
                        many=False,
                        partial=partial,
                        unknown=unknown,
                        index=idx,
                    ),
                )
                for idx, d in enumerate(data)
            ]
        return ret_l
    ret_d = self.dict_class()
    # Check data is a dict
    if not isinstance(data, Mapping):
        error_store.store_error([self.error_messages["type"]], index=index)
    else:
        partial_is_collection = is_collection(partial)
        for attr_name, field_obj in self.load_fields.items():
            field_name = (
                field_obj.data_key if field_obj.data_key is not None else attr_name
            )
            raw_value = data.get(field_name, missing)
            if raw_value is missing:
                # Ignore missing field if we're allowed to.
                if partial is True or (
                        partial_is_collection and attr_name in partial
                ):
                    continue
            d_kwargs = {}
            # Allow partial loading of nested schemas.
            if partial_is_collection:
                prefix = field_name + "."
                len_prefix = len(prefix)
                sub_partial = [
                    f[len_prefix:] for f in partial if f.startswith(prefix)
                ]
                d_kwargs["partial"] = sub_partial
            else:
                d_kwargs["partial"] = partial
            getter = lambda val: deserialize_field(field_obj,
                                                   val, field_name, data, skip_validation=True
                                                   )
            value = self._call_and_store(
                getter_func=getter,
                data=raw_value,
                field_name=field_name,
                error_store=error_store,
                index=index,
            )
            if value is not missing:
                key = field_obj.attribute or attr_name
                set_value(ret_d, key, value)
        if unknown != EXCLUDE:
            fields = {
                field_obj.data_key if field_obj.data_key is not None else field_name
                for field_name, field_obj in self.load_fields.items()
            }
            for key in set(data) - fields:
                value = data[key]
                if unknown == INCLUDE:
                    ret_d[key] = value
                elif unknown == RAISE:
                    error_store.store_error(
                        [self.error_messages["unknown"]],
                        key,
                        (index if index_errors else None),
                    )
    return ret_d


def deserialize_field(field, value, attr=None, data=None, skip_validation=False):
    """Deserialize ``value``.

    :raise ValidationError: If an invalid value is passed or if a required value
        is missing.
    """
    # Validate required fields, deserialize, then validate
    # deserialized value
    field._validate_missing(value)
    if value is missing:
        _miss = field.load_default
        return _miss() if callable(_miss) else _miss
    if field.allow_none and value is None:
        return None
    output = field._deserialize(value, attr, data)
    if not skip_validation:
        field._validate(output)
    return output
