from itertools import filterfalse
import collections

from .oerrors_omemdb import MultipleRecordsReturnedError, RecordDoesNotExistError
from .util import json_data_to_json


def unique_ever_seen(iterable, key=None):
    """
    https://docs.python.org/3.6/library/itertools.html#itertools-recipes
    List unique elements, preserving order. Remember all elements ever seen.

    unique_ever_seen('AAAABBBCCDAABBB') --> A B C D
    unique_ever_seen('ABBCcAD', str.lower) --> A B C D
    """
    seen = set()
    seen_add = seen.add
    if key is None:
        for element in filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element


class Queryset:
    def __init__(self, table, records=None, sort=True):
        self._table = table

        # manage no record
        if records is None:
            records = {}

        # ensure unique, sort and make un-mutable
        if sort:
            self._records = collections.OrderedDict((r.id, r) for r in tuple(sorted(unique_ever_seen(records))))
        else:
            self._records = collections.OrderedDict((r.id, r) for r in tuple(unique_ever_seen(records)))

        # check table
        if len({r.get_table() for r in self._records.values()}.difference({self._table})) > 0:
            raise RuntimeError(
                f"queryset contains records that belong to other table than {self.get_table_ref()}"
            )

    # python magic
    def __getitem__(self, item):
        return next(iter(self)) if item == 0 else list(self)[item]

    def __reversed__(self):
        """
        we need to implement reversed since __getitem__ is not coded in a list fashion way
        """
        return reversed(self._records.values())

    def __iter__(self):
        return iter(self._records.values())

    def __repr__(self):
        return f"<Queryset of {self._table.get_ref()}: {len(self._records)} records>"

    def __len__(self):
        return len(self._records)

    def __add__(self, other):
        return Queryset(self._table, list(self) + list(other))

    def __eq__(self, other):
        return set(self) == set(other)

    def get_table(self):
        return self._table

    def get_table_ref(self):
        return self._table.get_ref()

    def select(self, filter_by=None, sort=True):
        iterator = self._records.values() if filter_by is None else filter(filter_by, self._records.values())
        return Queryset(self._table, iterator, sort=sort)

    def one(self, filter_by=None):
        if isinstance(filter_by, (str, int)):
            try:
                return self._records[filter_by]
            except KeyError:
                raise RecordDoesNotExistError(
                    f"Queryset of table {self.get_table_ref()} contains no record whose id is '{filter_by}'"
                )

        # filter if needed
        qs = self if filter_by is None else self.select(filter_by=filter_by)

        # check one and only one
        if len(qs) == 0:
            raise RecordDoesNotExistError(
                self.get_table_ref(),
                message=f"Queryset of table{self.get_table_ref()} contains no value.")
        if len(qs) > 1:
            raise MultipleRecordsReturnedError(
                self.get_table_ref(),
                message=f"Queryset of table {self.get_table_ref()} contains more than one value.")

        # return record
        return qs[0]

    # delete
    def delete(self):
        """
        workflow
        --------
        (methods belonging to create/update/delete framework:
            db.__init__, table.batch_add, record.update, queryset.delete, record.delete)
        1. delete without setting sort index (calls pre-delete)
        2. set all sort indexes
        """
        for r in self:
            r._dev_delete_without_setting_sort_index()

        # set sort index
        self._table._dev_set_all_sort_indexes()

        # clear content
        self._records = ()

    # ------------------------------------------- export ---------------------------------------------------------------
    def to_json_data(self, style=None):
        return [r.to_json_data(style=style) for r in self._records.values()]

    def to_json(self, buffer_or_path=None, indent=2, style=None):
        d = self.to_json_data(style=style)
        return json_data_to_json(
            d,
            buffer_or_path=buffer_or_path,
            indent=indent
        )
