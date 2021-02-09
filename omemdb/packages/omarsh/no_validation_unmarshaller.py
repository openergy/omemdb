from marshmallow import marshalling
from marshmallow.utils import is_collection, missing, set_value
from marshmallow.compat import iteritems
from marshmallow.exceptions import ValidationError

SCHEMA = marshalling.SCHEMA


class NoValidationUnmarshaller(marshalling.Marshaller):
    def deserialize(self, data, fields_dict, many=False, partial=False,
                    dict_class=dict, index_errors=True, index=None):
        """Deserialize ``data`` based on the schema defined by ``fields_dict``.

        :param dict data: The data to deserialize.
        :param dict fields_dict: Mapping of field names to :class:`Field` objects.
        :param bool many: Set to `True` if ``data`` should be deserialized as
            a collection.
        :param bool|tuple partial: Whether to ignore missing fields. If its
            value is an iterable, only missing fields listed in that iterable
            will be ignored.
        :param type dict_class: Dictionary class used to construct the output.
        :param bool index_errors: Whether to store the index of invalid items in
            ``self.errors`` when ``many=True``.
        :param int index: Index of the item being serialized (for storing errors) if
            serializing a collection, otherwise `None`.
        :return: A dictionary of the deserialized data.
        """
        if many and data is not None:
            if not is_collection(data):
                errors = self.get_errors(index=index)
                self.error_field_names.append(SCHEMA)
                errors[SCHEMA] = ['Invalid input type.']
                ret = []
            else:
                self._pending = True
                ret = [self.deserialize(d, fields_dict, many=False,
                                        partial=partial, dict_class=dict_class,
                                        index=idx, index_errors=index_errors)
                       for idx, d in enumerate(data)]

                self._pending = False
                if self.errors:
                    raise ValidationError(
                        self.errors,
                        field_names=self.error_field_names,
                        fields=self.error_fields,
                        data=ret,
                    )
            return ret
        if data is not None:
            partial_is_collection = is_collection(partial)
            ret = dict_class()
            for attr_name, field_obj in iteritems(fields_dict):
                if field_obj.dump_only:
                    continue
                try:
                    raw_value = data.get(attr_name, missing)
                except AttributeError:  # Input data is not a dict
                    errors = self.get_errors(index=index)
                    msg = field_obj.error_messages['type'].format(
                        input=data, input_type=data.__class__.__name__
                    )
                    self.error_field_names = [SCHEMA]
                    self.error_fields = []
                    errors = self.get_errors()
                    errors.setdefault(SCHEMA, []).append(msg)
                    # Input data type is incorrect, so we can bail out early
                    break
                field_name = attr_name
                if raw_value is missing and field_obj.load_from:
                    field_name = field_obj.load_from
                    raw_value = data.get(field_obj.load_from, missing)
                if raw_value is missing:
                    # Ignore missing field if we're allowed to.
                    if (
                            partial is True or
                            (partial_is_collection and attr_name in partial)
                    ):
                        continue
                    _miss = field_obj.missing
                    raw_value = _miss() if callable(_miss) else _miss
                if raw_value is missing and not field_obj.required:
                    continue

                getter = lambda val: deserialize_field(
                    field_obj,
                    val,
                    field_obj.load_from or attr_name,
                    data,
                    skip_validation=True
                )
                value = self.call_and_store(
                    getter_func=getter,
                    data=raw_value,
                    field_name=field_name,
                    field_obj=field_obj,
                    index=(index if index_errors else None)
                )
                if value is not missing:
                    key = fields_dict[attr_name].attribute or attr_name
                    set_value(ret, key, value)
        else:
            ret = None

        if self.errors and not self._pending:
            raise ValidationError(
                self.errors,
                field_names=self.error_field_names,
                fields=self.error_fields,
                data=ret,
            )
        return ret

    # Make an instance callable
    __call__ = deserialize


def deserialize_field(field, value, attr=None, data=None, skip_validation=False):
    """Deserialize ``value``.

    :raise ValidationError: If an invalid value is passed or if a required value
        is missing.
    """
    # Validate required fields, deserialize, then validate
    # deserialized value
    field._validate_missing(value)
    if getattr(field, 'allow_none', False) is True and value is None:
        return None
    output = field._deserialize(value, attr, data)
    if not skip_validation:
        field._validate(output)
    return output
