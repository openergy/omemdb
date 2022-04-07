import functools

from omemdb.packages.oerrors import MarshValidator as _MarshValidator

from .omemdb_fields.api import LinkField
from .oerrors_omemdb import InvalidLink


class OmemdbMarshValidator(_MarshValidator):
    @classmethod
    @functools.lru_cache()
    def _get_error_conversion_map(cls):
        enriched_map = super()._get_error_conversion_map().copy()
        enriched_map.update(_marsh_message_to_oexception)
        return enriched_map


_marsh_message_to_oexception = {
    # Link
    LinkField.default_error_messages["invalid_link"]: InvalidLink
}
