from marshmallow.exceptions import ValidationError
from marshmallow.decorators import PRE_LOAD, POST_LOAD, VALIDATES_SCHEMA
from marshmallow import Schema as BaseSchema, types, EXCLUDE
from marshmallow.utils import validate_unknown_parameter_value
from collections import OrderedDict
import typing
from marshmallow.error_store import ErrorStore
from .no_validation_deserializer import _deserialize_no_validation


# fixme: [GL] document that, if Meta is subclassed, don't forget to maintain ordered = True


class Schema(BaseSchema):
    """
    Extended Marshmallow schema with custom functionalities:
        - dynamic schema creation
        - load schema with validation skipped for performance issues
    """

    # sort_index = fields.Int(missing=0)

    def add_field(
            self,
            key,
            value,
            last: bool = True):
        new_field = {key: value}
        if last:
            self.declared_fields.update(new_field)
        else:
            self.declared_fields = {**new_field, **self.declared_fields}
        self._init_fields()

    class Meta:
        ordered = True  # to serialize data to a `collections.OrderedDict`
        # Pass EXCLUDE as Meta option to keep marshmallow 2 behavior to drop unknown keys
        unknown = EXCLUDE

    def load(self, data, many=None, partial=None, unknown=None, skip_validation=False):
        errors = {}
        result = OrderedDict()
        try:
            if skip_validation:
                result = self._do_load_no_validate(data, many=many, partial=partial, unknown=unknown, postprocess=True)
            else:
                result = self._do_load(data, many=many, partial=partial, unknown=unknown, postprocess=True)

        except ValidationError as err:
            errors = err.messages

        return dict(data=result, errors=errors)

    # fixme: see if we want to de-activate pre-load and post-load ?
    def _do_load_no_validate(
            self,
            data: (
                    typing.Mapping[str, typing.Any]
                    | typing.Iterable[typing.Mapping[str, typing.Any]]
            ),
            *,
            many: bool | None = None,
            partial: bool | types.StrSequenceOrSet | None = None,
            unknown: str | None = None,
            postprocess: bool = True,
    ):
        """Deserialize `data`, returning the deserialized result.
        This method is private API.

        :param data: The data to deserialize.
        :param many: Whether to deserialize `data` as a collection. If `None`, the
            value for `self.many` is used.
        :param partial: Whether to validate required fields. If its
            value is an iterable, only fields listed in that iterable will be
            ignored will be allowed missing. If `True`, all fields will be allowed missing.
            If `None`, the value for `self.partial` is used.
        :param unknown: Whether to exclude, include, or raise an error for unknown
            fields in the data. Use `EXCLUDE`, `INCLUDE` or `RAISE`.
            If `None`, the value for `self.unknown` is used.
        :param postprocess: Whether to run post_load methods..
        :return: Deserialized data
        """
        error_store = ErrorStore()
        errors = {}  # type: dict[str, list[str]]
        many = self.many if many is None else bool(many)
        unknown = (
            self.unknown
            if unknown is None
            else validate_unknown_parameter_value(unknown)
        )
        if partial is None:
            partial = self.partial
        # Run preprocessors
        if self._has_processors(PRE_LOAD):
            try:
                processed_data = self._invoke_load_processors(
                    PRE_LOAD, data, many=many, original_data=data, partial=partial
                )
            except ValidationError as err:
                errors = err.normalized_messages()
                result = None  # type: list | dict | None
        else:
            processed_data = data
        if not errors:
            # Deserialize data
            result = _deserialize_no_validation(
                self,
                processed_data,
                error_store=error_store,
                many=many,
                partial=partial,
                unknown=unknown,
            )
            # Run field-level validation
            self._invoke_field_validators(
                error_store=error_store, data=result, many=many
            )
            # Run schema-level validation
            if self._has_processors(VALIDATES_SCHEMA):
                field_errors = bool(error_store.errors)
                self._invoke_schema_validators(
                    error_store=error_store,
                    pass_many=True,
                    data=result,
                    original_data=data,
                    many=many,
                    partial=partial,
                    field_errors=field_errors,
                )
                self._invoke_schema_validators(
                    error_store=error_store,
                    pass_many=False,
                    data=result,
                    original_data=data,
                    many=many,
                    partial=partial,
                    field_errors=field_errors,
                )
            errors = error_store.errors
            # Run post processors
            if not errors and postprocess and self._has_processors(POST_LOAD):
                try:
                    result = self._invoke_load_processors(
                        POST_LOAD,
                        result,
                        many=many,
                        original_data=data,
                        partial=partial,
                    )
                except ValidationError as err:
                    errors = err.normalized_messages()
        if errors:
            exc = ValidationError(errors, data=data, valid_data=result)
            self.handle_error(exc, data, many=many, partial=partial)
            raise exc

        return result
