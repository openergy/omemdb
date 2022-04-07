from omemdb.packages.omarsh import fields
from ..record_link import RecordLink
from ..util import camel_to_lower
from .base_link_field import BaseLinkField


class LinkField(fields.String, BaseLinkField):
    default_error_messages = {
        "invalid_link": "Target object not found.",
    }

    def __init__(self, target_table_ref, *args, **kwargs):
        self._target_table_ref = camel_to_lower(target_table_ref)
        super().__init__(*args, **kwargs)

    @property
    def target_table_ref(self):
        return self._target_table_ref

    def _serialize(self, value, attr, obj):
        validated = value.target_record.id if value is not None else None
        return super()._serialize(validated, attr, obj)

    def _deserialize(self, value, attr, data):
        # touchy import
        from ..record import Record
        if value is None:
            return None
        if isinstance(value, RecordLink):
            return value
        if isinstance(value, Record):
            return RecordLink.from_record(value, **self.metadata)
        try:
            return RecordLink.from_id(self.target_table_ref, str(value), **self.metadata)  # .lower()
        except (ValueError, AttributeError):
            pass
        self.fail("invalid_link")

    def _dev_set_target_to_none(self, value, target_record):
        return None

    def _dev_get_links(self, value):
        return [] if value is None else [value]
