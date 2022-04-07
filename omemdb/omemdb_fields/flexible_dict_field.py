import collections

from omemdb.packages.omarsh import fields
from .base_linkable_field import BaseLinkableField
from ..record_link import RecordLink


class FlexibleDictField(fields.Field, BaseLinkableField):
    @classmethod
    def serialize_value(cls, value):
        # touchy imports
        from ..record import Record
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
            k: None if (isinstance(v, RecordLink) and v.target_record == target_record) else v
            for k, v in value.items()
        }
        return self.unwrap(none_value)

    def _dev_get_links(self, value):
        value = self.wrap(value)
        return list(filter(lambda v: isinstance(v, RecordLink), value.values()))


