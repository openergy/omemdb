from omemdb.packages.omarsh import fields
from .base_link_field import BaseLinkField
from .link_field import LinkField
from ..record_link import RecordLink


class TupleLinkField(fields.Tuple, BaseLinkField):
    def __init__(self, target_table_name, *args, **kwargs):
        link = LinkField(target_table_name, required=True)
        self._target_table_ref = link.target_table_ref
        super().__init__(link, *args, **kwargs)

    @property
    def target_table_ref(self):
        return self._target_table_ref

    # fixme: should check that record is a Link of correct table (only Link check is performed by marsh List field)
    def _dev_set_target_to_none(self, value, target_record):
        return tuple(v for v in value if v.target_record != target_record)

    def _dev_get_links(self, value):
        return list(filter(lambda k: isinstance(k, RecordLink), value))
