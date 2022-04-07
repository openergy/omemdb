import itertools
import logging

from omemdb.packages.omarsh import fields, missing as MISSING, Schema

from .omemdb_fields.api import LinkField, BaseLinkField
from .oerrors_omemdb import OExceptionCollection, NotUnique, NotUniqueTogether, RecordDoesNotExistError, \
    TableDefinitionError
from .util import camel_to_lower, lower_to_initials
from .queryset import Queryset
from .record import Record
from .records_container import FieldPkRecordsContainer, DynamicPkRecordsContainer, DuplicateFieldIdError
from .dynamic_fields_schema import DynamicFieldsSchemaMixin
from .record import EPSILON, SORT_INDEX, SORT_GROUP

logger = logging.getLogger(__name__)


class EmptyMeta:
    pass


class Table:
    # fixme: [GL] document for users (meta, dynamic fields, ...).
    #  Explain dynamic pk risks (must be unique or may corrupt db) and drawbacks (performance issues)
    def __init__(self, record_cls, db):
        """
        Notes
        -----
        Don't use _dev_get_index in get_id method, will generate a recursion
        """
        # fixme: [GL] check all fields are used
        # store info
        self._ref = camel_to_lower(record_cls.__name__)
        self._initials = lower_to_initials(self._ref)
        self._dev_record_cls = record_cls
        self._dev_schema = None  # we store prepared schema
        self._db = db
        self._records = None  # will depend on meta, is set in _check_and_prepare_table
        
        # table meta
        self._dev_pk_field = None
        self._dev_dynamic_id_fct = None
        self._dev_dynamic_id_tables = ()

        self._unique_together = None
        self._dev_sortable = None

    # ----------------------------------------- private ----------------------------------------------------------------
    # check table definition
    def _dev_check_and_prepare_table(self):
        """
        private but access is authorized by db
        """
        assert issubclass(self._dev_record_cls, Record), f"table {self._ref}: record class does not inherit Record"

        # RETRIEVE SCHEMA
        schema_cls = getattr(self._dev_record_cls, "Schema")
        if schema_cls is None:
            raise TableDefinitionError(self._ref, "no Schema defined")

        if not issubclass(schema_cls, Schema):
            raise TableDefinitionError(self._ref, "Schema must inherit from omarsh Schema class")

        # CONNECT DYNAMIC SCHEMA MIXIN
        class DynamicSchema(DynamicFieldsSchemaMixin, schema_cls):  # order matters
            _dev_table = self

        # hack: _dev_table_ref and _dev_pk_field will be set at the end because _dev_pk_field is unknown for the moment

        # CHECK SCHEMA

        # instantiate
        self._dev_schema = DynamicSchema()
        for name, descriptor in self._dev_schema.declared_fields.items():
            # check default is not used
            if descriptor.default is not MISSING:
                logger.error(
                    f"table {self._ref}, field {name}: default was used but it will have no effect. "
                    f"Use missing instead."
                )

            # check allow_none is true if missing is None
            if descriptor.missing is None and not descriptor.allow_none:
                logger.error(
                    f"table {self._ref}, field {name}: "
                    f"missing value is None, but you did not allow_none, this is not coherent."
                )

            # check no missing was defined if value is required
            if descriptor.required and descriptor.missing is not MISSING:
                logger.error(
                    f"table {self._ref}, field {name}: "
                    f"missing value was provided, but field is required, this is not coherent."
                )

            # check missing was provided if value is not required
            if not descriptor.required and descriptor.missing is MISSING:
                logger.error(
                    f"table {self._ref}, field {name}: "
                    f"field is not required, but no missing value was provided, not coherent."
                )

            # check reserved keys
            if name in ("id", SORT_INDEX, SORT_GROUP):
                raise TableDefinitionError(self._ref, "'{name}' is a reserved field name, can't use it")

            # check value
            if isinstance(descriptor, fields.Tuple):  # manage tuples
                self._check_mono_field(descriptor.container)
            else:
                self._check_mono_field(descriptor)

        # CHECK TABLE META

        # * check table meta was defined
        table_meta = getattr(self._dev_record_cls, "TableMeta", EmptyMeta)

        # * check no unknown meta fields
        unknown_fields = {k for k in dir(table_meta) if k[0] != "_"}.difference({
            "dynamic_id",
            "sortable",
            "unique"
        })
        if len(unknown_fields) > 0:
            raise TableDefinitionError(self._ref, f"unknown TableMeta fields: {sorted(unknown_fields)}")

        # * get, check and store dynamic_id field
        dynamic_id = getattr(table_meta, "dynamic_id", False)
        if dynamic_id is False:  # field pk
            # check and store info
            self._dev_pk_field, field_descriptor = next(iter(self._dev_schema.declared_fields.items()))
            if not isinstance(field_descriptor, (fields.Integer, fields.String)):
                raise TableDefinitionError(self._ref, f"pk field must be an integer or a string")
            if not field_descriptor.required or field_descriptor.allow_none:
                raise TableDefinitionError(self._ref, f"pk field must be required and must not allow_none")

            # set records container
            self._records = FieldPkRecordsContainer()

        else:  # dynamic pk
            # check and store info
            if callable(dynamic_id):
                dynamic_id = (dynamic_id, ())
            else:
                try:
                    dynamic_id = tuple(dynamic_id)
                except TypeError:
                    raise TableDefinitionError(self._ref, "dynamic_id must be callable or iterable")

            # check length
            if len(dynamic_id) != 2:
                raise TableDefinitionError(self._ref, "dynamic_id must be callable or a two element iterable")

            # load function
            dynamic_id_fct = dynamic_id[0]
            if not callable(dynamic_id_fct):
                raise TableDefinitionError(self._ref, "dynamic_id must be callable or iterable")
            self._dev_dynamic_id_fct = dynamic_id_fct

            # load tables
            try:
                dynamic_id_tables = tuple(dynamic_id[1])
            except TypeError:
                raise TableDefinitionError(self._ref, "dynamic_id second element must be iterable")
            if len({type(k) for k in dynamic_id_tables}.difference({str})) > 0:
                raise TableDefinitionError(self._ref, "dynamic_id second element must be an iterable of strings")
            self._dev_dynamic_id_tables = dynamic_id_tables

            # set records container
            self._records = DynamicPkRecordsContainer()

        # add id field
        self._dev_schema.add_field("id", fields.String(dump_only=True), last=False)

        # * manage uniqueness (pk uniqueness is managed elsewhere)
        unique = getattr(self._dev_record_cls.TableMeta, "unique", [])
        if isinstance(unique, str):
            unique_together = [(unique,)]
        else:
            unique_together = []
            for u in unique:
                if isinstance(u, str):
                    # check not pk field
                    if u == self._dev_pk_field:
                        raise TableDefinitionError(
                            self._ref,
                            "must not declare pk field as unique, it is taken into account automatically")

                    unique_together.append((u,))
                else:
                    unique_together.append(tuple(u))
        # check
        for ut in unique_together:
            for u in ut:
                if u not in self._dev_schema.declared_fields:
                    raise TableDefinitionError(
                        self._ref,
                        f"unknown field declared as unique: {u}")

        # make unique and store
        self._unique_together = tuple(sorted(set(unique_together)))

        # * manage sorting
        # fixme: [GL] put admin fields at beginning in correct order to optimize sort ?
        self._dev_sortable = getattr(self._dev_record_cls.TableMeta, "sortable", False)
        if self._dev_sortable:
            # add index field (optional but will be set if None in batch_add)
            self._dev_schema.add_field(SORT_INDEX, fields.Integer(), last=False)

            # see if has a sort group
            if callable(self._dev_sortable):
                # add group field
                self._dev_schema.add_field(SORT_GROUP, fields.String(dump_only=True), last=False)
            elif self._dev_sortable is not True:
                raise TableDefinitionError(self._ref, "sortable must be a boolean or a callable")

        # store link dependencies
        self._dev_link_dependencies = set(
            linkField.target_table_ref
            for linkField in self._dev_schema.declared_fields.values()
            if isinstance(linkField, BaseLinkField)
        )

    def _check_mono_field(self, field):
        # check authorized type
        if isinstance(field, (fields.Nested, fields.List, fields.Dict)):
            raise RuntimeError(f"table: {self.get_ref()}: non supported fields: {type(field)}")
        # check link
        if isinstance(field, LinkField) and not hasattr(self._db, field.target_table_ref):
            raise RuntimeError(f"table {self._ref}: unknown target_table of given link ({field.target_table_ref})")

    # -------------------------------------------- dev api -------------------------------------------------------------
    def _dev_add_inert(self, records_data, skip_validation=False):
        # inert being: not unique checked, not sorted, links not activated
        added_records = []

        # prepare exceptions
        oec = OExceptionCollection()

        # create records
        for data in records_data:
            # create record
            with oec.catch_errors():
                added_records.append(self._dev_record_cls(self, data, skip_validation=skip_validation))
        oec.raise_if_error()

        for num, record in enumerate(added_records):
            # manage ordering if necessary
            # algorithm :
            #  - if no position given by user: put at the end of table
            #  - put record to required position (last added wins on a batch)
            #
            #  we use EPSILON to manage priority (works as long as (num+1)*EPSILON is < 1)
            if self._dev_sortable:
                if (num + 1) * EPSILON >= 1:
                    raise RuntimeError("algorithm won't work, too many records were added at once")
                prioritized_sort_index = getattr(record, SORT_INDEX, len(self._records)) - (num + 1) * EPSILON
                record._dev_set_sort_index(prioritized_sort_index)

            # store
            try:
                self._records.add_record(record)
            except DuplicateFieldIdError as e:
                field_name = "id" if self._dev_pk_field is None else self._dev_pk_field
                oec.append(NotUnique(self._ref, e.id, field_name, getattr(record, field_name)))
                continue

        oec.raise_if_error()

        return added_records

    def _dev_check_uniqueness(self):
        # check uniqueness
        oec = OExceptionCollection()
        for ut in self._unique_together:
            values = tuple(map(lambda x: tuple(getattr(x, k) for k in ut), self._records.values()))
            if len(values) != len(set(values)):
                # find duplicates
                seen, duplicates = set(), set()
                for v in values:
                    if v in seen:
                        duplicates.add(v)
                    else:
                        seen.add(v)

                # list records and append exception
                records = filter(lambda x: tuple(getattr(x, k) for k in ut) in duplicates, self._records.values())
                for r in records:
                    if len(ut) == 1:
                        oec.append(NotUnique(
                            self._ref,
                            r.id,
                            field_name=ut[0],
                            value=getattr(r, ut[0])
                        ))
                    else:
                        oec.append(NotUniqueTogether(
                            self._ref,
                            r.id,
                            field_names=ut,
                            values=tuple(str(getattr(r, k)) for k in ut)
                        ))
        oec.raise_if_error()

    def _dev_set_all_sort_indexes(self):
        # leave if not relevant
        if not self._dev_sortable:
            return
        # no sort group
        if self._dev_sortable is True:
            for index, record in enumerate(self._records.values(sort=True)):
                record._dev_set_sort_index(index)
            return
        # with sort group
        for group_key, group in itertools.groupby(
                self._records.values(sort=True),
                self._dev_sortable
        ):
            for index, record in enumerate(group):
                record._dev_set_sort_index(index)

    def _dev_update_pk(self, new_pk, old_pk):
        try:
            self._records.update_pk(new_pk, old_pk)
        except DuplicateFieldIdError:
            raise NotUnique(self._ref, old_pk, self._dev_pk_field, new_pk)

    def _dev_remove_record_without_unregistering(self, record):
        self._records.remove_record(record)

    def _dev_get_index(self, record):
        return self._records.get_index(record)

    # ---------------------------------------- public api --------------------------------------------------------------
    # python magic
    def __repr__(self):
        return f"<table:{self.get_ref()}>"

    def __getitem__(self, item):
        return self.select()[item]

    def __iter__(self):
        """
        returned records are sorted
        """
        # sort returns a list, therefore self._records may be modified safely during iteration
        return iter(sorted(self._records.values()))

    def __len__(self):
        return len(self._records)

    def get_ref(self):
        return self._ref

    def get_initials(self):
        return self._initials

    def get_fields(self):
        return self._dev_schema.declared_fields

    def get_db(self):
        return self._db

    def add(self, data=None, **or_data):
        return self.batch_add([or_data if data is None else data])[0]

    def batch_add(self, records_data):
        """
        workflow
        --------
        (methods belonging to create/update/delete framework:
            db.__init__, table.batch_add, record.update, queryset.delete, record.delete)
        1. add inert
            * data is checked
            * old links are unregistered
            * record is stored in table (=> pk uniqueness is checked)
        2. links are activated
        3. uniqueness is checked
        4. set all sort indexes
        5. post_save is called
        """
        # add inert
        added_records = self._dev_add_inert(records_data)

        # activate links
        for r in added_records:
            r._dev_activate_links()

        # check uniqueness (must be done after links activation so links point on records)
        self._dev_check_uniqueness()

        # set sort index
        self._dev_set_all_sort_indexes()

        # post save
        for r in added_records:
            r._dev_post_save(True, False)  # created, not db_is_initializing

        return added_records

    # explore
    def select(self, filter_by=None, sort=True):
        records = self._records.values() if filter_by is None else filter(filter_by, self._records.values())
        return Queryset(self, records=records, sort=sort)

    def one(self, filter_by=None):
        if isinstance(filter_by, (str, int)):
            try:
                return self._records[filter_by]
            except KeyError:
                raise RecordDoesNotExistError(self.get_ref(), filter_by)
        return self.select(filter_by=filter_by).one()

    # delete
    def delete(self):
        self.select().delete()

    # ------------------------------------------- export ---------------------------------------------------------------
    def to_json_data(self, style=None):
        return self.select().to_json_data(style=style)

    def to_json(self, buffer_or_path=None, indent=2, style=None):
        return self.select().to_json(
            buffer_or_path=buffer_or_path,
            indent=indent,
            style=style
        )
