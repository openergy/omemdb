import abc

from .base_linkable_field import BaseLinkableField


class BaseLinkField(BaseLinkableField, abc.ABC):
    # fixme: manage link definition properly
    @property
    @abc.abstractmethod
    def target_table_ref(self):
        pass
