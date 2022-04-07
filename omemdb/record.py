import collections
import hashlib
import logging
import warnings

import numpy as np

from .omemdb_fields.api import LinkField, TupleLinkField, BaseLinkableField
from .record_link import RecordLink
from .oerrors_omemdb import OExceptionCollection, UpdateCommitmentError, DeleteCommitmentError, get_instance

EPSILON = 0.00001
SORT_GROUP = "sort_group"  # don't forget to change record property (and it's calls) if variable is changed
SORT_INDEX = "sort_index"


logger = logging.getLogger(__name__)


def _secured_eq(value, other):
    """
    some __eq__ may raise (for example comparing pandas series that don't have the same labels)
    """
    try:
        return bool(value == other)
    except:
        return False


class Record:
    """
    Committing relations
    --------------------
    - update:
        When an update is performed, it may break a _post_save validation in a foreign table, without any warning. The
        consequence is that update is accepted, but obat becomes corrupt.
        This is the reason why we introduced update committing relations: we prevent modification for some fields, if
        record is pointed by committed_to_tables.
        committing_relations_for_update therefore has two purposes:
            - explain to frontend current relations (to prevent wrong behavior)
            - block bad updates that omemdb would have accepted (update was subclassed)
    - delete:
        A deletion will be refused by omemdb if delete record is pointed by a required field in initial schema.
        Omemdb therefore properly manages this situation. However, when dynamic post load validations are used,
        a link field may become required, and omemdb can't know. We nee to prevent this case.
        committing_relations_for_delete therefore has two purposes:
            - explain to frontend current relations (to prevent wrong behavior)
            - block bad updates that omemdb would have accepted (delete was subclassed)
        no need to subclass delete
    """
    _committing_relations_for_update = None  # to subclass: {committed_field: {committed_to_tables, ...
    _committing_relations_for_delete = None  # to subclass: {committed_to_tables

    Schema = None
    TableMeta = None

    _initialized_for_setattr_ = False  # used by __setattr__

    _initialized = False

    def __init__(self, table, data, skip_validation=False):
        """
        Parameters
        ----------
        on creation, record is inert (updated inert called, not update)
        """
        self._table = table
        self._data = {}
        self._post_save_in_progress = False

        # signal initialized (to manage __setattr__
        self._initialized_for_setattr_ = True

        # set data
        self._update_inert(data, skip_validation=skip_validation)
        self._initialized = True

    # ----------------------------------------------- private ----------------------------------------------------------
    def _update_inert(self, data, unregister_links=True, skip_validation=False):
        initial_id = self.id if self._initialized else None

        # merge new data and current data
        new_data = self._data.copy()
        new_data.update(data)

        # manage error message pk
        error_message_id = self._dev_guess_new_data_id(self._table, new_data) if initial_id is None else initial_id

        # deserialize
        schema = self.get_schema()
        marsh_validator = self.get_db().marsh_validator_cls(
            schema,
            get_instance(
                self.get_table_ref(),
                record_id=error_message_id
            )
        )
        new_data, oec = marsh_validator.validate(new_data, skip_validation=skip_validation)
        oec.raise_if_error()

        # manage pk update if persistent pk field (will be skipped on creation)
        if initial_id is not None and self._table._dev_pk_field is not None and self._table._dev_pk_field in data:
            self.get_table()._dev_update_pk(data[self._table._dev_pk_field], initial_id)

        # unregister old links that will be removed, if asked
        if unregister_links:
            for key, value in new_data.items():
                old_value = self._data.get(key)
                field_descriptor = schema.declared_fields[key]
                if (
                        (old_value is None)
                        or _secured_eq(value, old_value)
                        or not isinstance(field_descriptor, BaseLinkableField)
                ):
                    # !! it is important to check that old value is record link (not new one), because of dynamic
                    # fields: old value may be a link, although new value has become something else
                    continue
                for old_link in field_descriptor._dev_get_links(old_value):
                    old_link.unregister()

        # tweak sort index if necessary
        if (
                self.get_table()._dev_sortable  # sortable
                and len(self._data) > 0  # if first update inert (at creation), may not have a sort_index
        ):
            # for following comments, we consider records are ordered from left to right
            if self._data[SORT_INDEX] < new_data[SORT_INDEX]:
                # record has been shifted rightwards. New sort index might therefore overlap an existing record. We make
                # sure current record is after existing record.
                new_data[SORT_INDEX] += EPSILON
            elif self._data[SORT_INDEX] > new_data[SORT_INDEX]:
                # record has been shifted leftwards. Ne sort index might therefore overlap an existing record. We make
                # sure that current record is before existing record.
                new_data[SORT_INDEX] -= EPSILON

        # store
        self._data = new_data

    # ----------------------------------------- dev api ----------------------------------------------------------------
    # guess id from data (for validation, record does not yet exist)
    @classmethod
    def _dev_guess_new_data_id(cls, table, data):
        # manage pk_field case
        if table._dev_pk_field is not None and table._dev_pk_field in data:
            return data[table._dev_pk_field]

        # manage no data case
        if len(data) == 0:
            return "?"

        # try to guess
        for standard_var in ("id", "_id", "pk", "ref", "name"):
            if standard_var in data:
                return str(data[standard_var])

        # put all (we sort after conversion to str to prevent non sortable errors)
        return "<" + ",".join(sorted(f"{repr(k)}={repr(v)}" for k, v in data.items())) + ">"

    # get
    def _dev_get_raw_value(self, item):
        return self._data[item]

    # save/update/delete
    def _dev_activate_links(self):
        """
        used by: db.__init__, table.batch_add, record.update
        """
        links_to_activate = []  # [(field, link), ...]
        for field, descriptor in self.get_schema().declared_fields.items():
            if not isinstance(descriptor, BaseLinkableField):
                continue
            links_to_activate.extend([
                (field, link) for link in descriptor._dev_get_links(self._data[field])
            ])

        oec = OExceptionCollection()
        for field, record_link in links_to_activate:
            # activate
            with oec.catch_errors():
                record_link.activate(self, field)
        oec.raise_if_error()

    def _dev_set_none_without_unregistering(self, field, target_record):
        """
        called by relations manager while unregistering links
        only fields implementing the LinkableFieldInterface are concerned
        """
        # prepare empty value
        field_schema = self.get_schema().fields[field]
        empty_value = field_schema._dev_set_target_to_none(self._data[field], target_record)

        # update without unregistering links
        self._update_inert({field: empty_value}, unregister_links=False)

    def _dev_delete_without_setting_sort_index(self):
        # manage delete commitments if relevant
        if self._committing_relations_for_delete is not None:
            # retrieve delete commitments
            delete_commitments = self.get_commitments()["delete"]

            # raise if problem
            if len(delete_commitments) > 0:
                raise DeleteCommitmentError.from_record(self, delete_commitments)

        # call pre delete
        self._pre_delete()

        # unregister record (will also unregister it's links)
        self.get_db()._dev_relations_manager.unregister_record(self)

        # tell table to remove without unregistering
        self.get_table()._dev_remove_record_without_unregistering(self)

        # make stale
        self._table = None
        self._data = None

    def _dev_post_save(self, created, db_is_initializing):
        """
        Ensures user is not modifying the record on his post_save method, to avoid infinite loops.
        DO NOT OVERRIDE UNLESS YOU ARE SURE YOU KNOW WHAT YOU ARE DOING
        """
        if self._post_save_in_progress:
            raise AssertionError("Tried to update a record from its post_save function, which is forbidden.")
        self._post_save_in_progress = True
        try:
            self._post_save(created=created, db_is_initializing=db_is_initializing)
        except Exception as e:
            warnings.warn(
                f"Error while running post_save function on a record."
                f" Your obat/obm/ogw object is now probably corrupted, please reload it.")
            raise
        finally:
            self._post_save_in_progress = False

    # manage sort index
    def _dev_set_sort_index(self, sort_index):
        self._data[SORT_INDEX] = sort_index

    # ------------------------------------------- public api -----------------------------------------------------------
    # python magic
    def __repr__(self):
        if self.get_db() is None:
            return "<Record (deleted)>"
        return f"<Record {self.get_table_ref()} '{self.id}'>"

    def __str__(self):
        if self.get_db() is None:
            return repr(self)

        s = self.get_table_ref() + "\n"
        s += f"  id: {self.id}\n"
        for k, v in sorted(self._data.items()):
            s += f"  {k}: {v}\n"
        return s

    def __getattr__(self, item):
        # get raw value
        try:
            value = self._data[item]
        except KeyError as e:
            raise AttributeError(f"{e} not found (record type: {self.get_table_ref()})")

        # transform and return
        if isinstance(value, RecordLink):
            return value.target_record
        if isinstance(value, tuple):
            return tuple((v.target_record if isinstance(v, RecordLink) else v for v in value))
        return value

    def __setattr__(self, key, value):
        """
        protect fields once object has been frozen
        """
        if self._initialized_for_setattr_ and key in self._data:
            self.update({key: value})
        else:
            super().__setattr__(key, value)

    def __dir__(self):
        return list(self.get_schema().declared_fields.keys()) + list(self.__dict__.keys())

    def __lt__(self, other):
        # compare tables
        self_ref, other_ref = self.get_table_ref(), other.get_table_ref()
        if self_ref < other_ref:
            return True
        if self_ref > other_ref:
            return False

        # same table => compare records

        # non sortable
        if not self._table._dev_sortable:
            return self.id < other.id

        # sortable without a group
        if self._table._dev_sortable is True:
            return getattr(self, SORT_INDEX) < getattr(other, SORT_INDEX)

        # sortable with a group
        return (self.sort_group, getattr(self, SORT_INDEX)) < (other.sort_group, getattr(other, SORT_INDEX))

    @property
    def id(self):
        if not self._initialized:
            raise AssertionError("shouldn't call id on a non initialized record")
        if self._table._dev_pk_field is None:
            try:
                return self._table._dev_dynamic_id_fct(self)
            except AttributeError as e:
                raise RuntimeError(
                    f"{e}\n"
                    f"AttributeError while calling dynamic id function on table '{self.get_table_ref()}', "
                    f"this function is probably buggy"
                ) from None

        try:
            return getattr(self, self._table._dev_pk_field)
        except AttributeError:
            raise RuntimeError(f"did not find pk field in _data ({self._table._dev_pk_field}), should not happen")

    @property
    def sort_group(self):
        return self._table._dev_sortable(self) if callable(self._table._dev_sortable) else None

    def get_index(self):
        return self.get_table()._dev_get_index(self)

    def get_table_ref(self):
        return self.get_table().get_ref()

    def get_schema(self):
        return self.get_table()._dev_schema

    def get_hash(self, table_prefix=True):
        """
        max records (n): 15000
        probability (p): 10-5 (of one collision if n hashes generated)
        hash space (hs) = n**2/(2*ln(1/(1-p)))

        36 encoding characters = ln(hs)/ln(36) = 9

        (36 is the max)
        """
        # fixme: could parametrize hypothesis in a framework-like way (for the moment thought for obat only)
        hashed_ref = np.base_repr(
            int.from_bytes(
                hashlib.md5(str(self.id).encode()).digest(),
                "big"),
            36)[:9].lower()
        if table_prefix:
            return f"{self.get_table().get_initials()}-{hashed_ref}"
        return hashed_ref

    def get_db(self):
        return self._table.get_db()

    def get_table(self):
        """
        Returns
        -------
        omemdb.table.Table
        """
        return self._table

    # construct
    def update(self, data=None, **or_data):
        """
         workflow
        --------
        (methods belonging to create/update/delete framework:
            db.__init__, table.batch_add, record.update, queryset.delete, record.delete)
        1. update inert
            * data is checked
            * old links are unregistered
        2. links are activated
        3. uniqueness is checked
        4. set all sort indexes
        5. post_save is called
        """
        # prepare data
        data = or_data if data is None else data

        # manage update commitments if relevant
        if self._committing_relations_for_update is not None:
            # retrieve update commitments
            update_commitments = self.get_commitments()["update"]

            # prepare error management
            oec = OExceptionCollection()

            # iter problems
            for committed_field in set(update_commitments).intersection(data):
                oec.append(
                    UpdateCommitmentError.from_record(self, committed_field, update_commitments[committed_field]))

            # raise if relevant
            oec.raise_if_error()

        # update inert
        self._update_inert(data)

        # activate links
        self._dev_activate_links()

        # check table unique fields (must be done after links activation so links point on records)
        self.get_table()._dev_check_uniqueness()

        # set sort index
        self.get_table()._dev_set_all_sort_indexes()

        # post save
        self._dev_post_save(False, False)  # not created, not db_is_initializing

        # fixme: [GL] cross table verifications are not called here, db may become corrupt, manage.
        #  Possible optimization problems.

    def copy(self, **data):
        """
        for sortable records, if no sort_index is provided, new record will go after copied record
        """
        # fixme: [GL] test
        self_data = {k: getattr(self, k) for k in self.get_schema().declared_fields}
        self_data.update(data)

        # if sortable and no sort index provided, we want record to go after copied record
        if self.get_table()._dev_sortable and "sort_index" not in data:
            self_data["sort_index"] += 1

        return self.get_table().add(**self_data)

    def get_pointed_records(self, sort=True):
        return self.get_db()._dev_relations_manager.get_pointed_from(self, sort=sort)

    def get_pointing_records(self, sort=True):
        # fixme: could be optimized : user usually works on one type of records at a time
        #  (zone.get_pointing_records().surface), in which case there is no need to look for other types of records
        return self.get_db()._dev_relations_manager.get_pointing_on(self, sort=sort)

    # delete
    def delete(self):
        """
         workflow
        --------
        (methods belonging to create/update/delete framework:
            db.__init__, table.batch_add, record.update, queryset.delete, record.delete)
        1. delete without setting all sort indexes
        2. set all sort indexes
        """
        # store table (to sort indexes later on)
        table = self._table

        # delete
        self._dev_delete_without_setting_sort_index()

        # set table sort index
        table._dev_set_all_sort_indexes()

    def get_commitments(self):
        """
        Returns
        -------
        commitments
        if no commitment in a table, table key will not be present
        """
        commitments = collections.OrderedDict(
            update=collections.OrderedDict(),  # {committed_field: {table_ref: [record pks, ...], ...}, ...}
            delete=collections.OrderedDict()  # {table_ref: [record pks, ...], ...}
        )

        if (self._committing_relations_for_update is None) and (self._committing_relations_for_delete is None):
            return commitments

        # prepare variables
        pointing = self.get_pointing_records(sort=False)

        # update commitments
        if self._committing_relations_for_update is not None:
            for committed_field, potential_committed_to_tables in self._committing_relations_for_update.items():
                committed_to_tables = potential_committed_to_tables.intersection(pointing)
                if len(committed_to_tables) == 0:
                    continue
                commitments["update"][committed_field] = {
                    table_ref: [r.id for r in getattr(pointing, table_ref)]
                    for table_ref in committed_to_tables
                }

        # deletion commitments
        if self._committing_relations_for_delete is not None:
            committed_to_tables = self._committing_relations_for_delete.intersection(pointing)
            commitments["delete"] = {
                    table_ref: [r.id for r in getattr(pointing, table_ref)]
                    for table_ref in committed_to_tables
                }

        return commitments

    # --------------------------------------------- export -------------------------------------------------------------
    def to_dict(self, raw_links=False):
        schema = self.get_schema()
        if not raw_links:
            return collections.OrderedDict(
                (field, getattr(self, field)) for field in schema.declared_fields
            )
        d = collections.OrderedDict()
        for field, descriptor in schema.declared_fields.items():
            if isinstance(descriptor, LinkField) or (
                    isinstance(descriptor, TupleLinkField) and isinstance(descriptor.container, LinkField)):
                d[field] = self._data.get(field)
            else:
                d[field] = getattr(self, field, None)
        return d

    def to_json_data(self, style=None):
        """
        may be subclassed to define other styles (for example for more detail)
        !! if subclassed, style=None must behave as if was not subclassed !!
        """
        return collections.OrderedDict(self.get_schema().dump(self.to_dict(raw_links=True)).data.items())

    # ------------------------------------------- custom user actions --------------------------------------------------
    def _pre_delete(self, **kwargs):
        pass

    def _post_save(self, **kwargs):
        """

        Parameters
        ----------
        kwargs:
            created: boolean
        """
        pass
