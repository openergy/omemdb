import collections
from omemdb.packages.omarsh import fields

from .record_link import RecordLink as _RecordLink
from .linkable_field_interface import LinkableFieldInterface as _LinkableFieldInterface
from .util import camel_to_lower as _camel_to_lower


class LinkField(fields.String, _LinkableFieldInterface):
    default_error_messages = {
        "invalid_link": "Target object not found.",
    }

    def __init__(self, target_table, *args, **kwargs):
        self.target_table_ref = _camel_to_lower(target_table)
        super().__init__(*args, **kwargs)

    def _serialize(self, value, attr, obj):
        validated = value.target_record.id if value is not None else None
        return super()._serialize(validated, attr, obj)

    def _deserialize(self, value, attr, data):
        # touchy import
        from .record import Record
        if value is None:
            return None
        if isinstance(value, _RecordLink):
            return value
        if isinstance(value, Record):
            return _RecordLink.from_record(value, **self.metadata)
        try:
            return _RecordLink.from_id(self.target_table_ref, str(value), **self.metadata)  # .lower()
        except (ValueError, AttributeError):
            pass
        self.fail("invalid_link")

    def _dev_set_target_to_none(self, value, target_record):
        return None

    def _dev_get_links(self, value):
        return [] if value is None else [value]


class LinkableTupleField(fields.Tuple, _LinkableFieldInterface):
    def _dev_set_target_to_none(self, value, target_record):
        return tuple(v for v in value if v.target_record != target_record)

    def _dev_get_links(self, value):
        return list(filter(lambda k: isinstance(k, _RecordLink), value))


class FlexibleDictField(fields.Field, _LinkableFieldInterface):
    @classmethod
    def serialize_value(cls, value):
        # touchy imports
        from .record import Record
        if isinstance(value, Record):
            return value.id
        return value

    @classmethod
    def wrap(cls, value):
        if isinstance(value, dict):
            return value
        return dict(value=value)

    @classmethod
    def unwrap(cls, value):
        if isinstance(value, dict) and (len(value) == 1) and ("value" in value):
            return value["value"]
        return value

    def _serialize(self, value, attr, obj):
        return collections.OrderedDict(
            (k, self.serialize_value(v)) for k, v in self.wrap(value).items()
        )

    def _deserialize(self, value, attr, data):
        return self.unwrap(value)

    def _dev_set_target_to_none(self, value, target_record):
        value = self.wrap(value)
        none_value = {
            k: None if (isinstance(v, _RecordLink) and v.target_record == target_record) else v
            for k, v in value.items()
        }
        return self.unwrap(none_value)

    def _dev_get_links(self, value):
        value = self.wrap(value)
        return list(filter(lambda v: isinstance(v, _RecordLink), value.values()))
