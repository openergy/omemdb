import collections
from typing import Iterable
import os
import logging
import importlib

from . import CONF
from .util import json_load, json_dump
from .packages.oversion import Version
from .oerrors_omemdb import OExceptionCollection, MissingVersionKey, MissingTableKey, VersionIsTooHigh, \
    VersionIsTooLowAutoMigrateIsOff, OmemdbMarshValidator

from .table import Table
from .util import json_data_to_json, camel_to_lower
from .relations_manager import RelationsManager

logger = logging.getLogger(__name__)


def _get_json_data_version(json_data):
    json_data_version = json_data.get("__version__", None)
    if json_data_version is None:
        raise MissingVersionKey()
    return Version.from_text(json_data_version)


class Db:
    # --------------------------------------------- to subclass --------------------------------------------------------
    version = None  # to subclass (optional)
    migration_dir = None  # to subclassed, for example: ".".join(__name__.split(".")[:-1] + ["migrations"])
    models = None  # to subclass
    marsh_validator_cls = OmemdbMarshValidator  # to subclass

    @classmethod
    def migrate(cls, json_data, report=None, warn=True):
        # check migration dir is defined
        if cls.migration_dir is None:
            raise RuntimeError("migration dir was not defined on db class, can't migrate")

        # load json_data version
        json_data_version = _get_json_data_version(json_data)
        current_version = Version.from_text(cls.version)

        # prepare migrations dir path
        migration_report = OExceptionCollection()
        for major in range(json_data_version.major + 1, current_version.major + 1):
            # load read module
            module_name = f"{cls.migration_dir}.to{major:04}"
            migration_module = importlib.import_module(module_name)
            json_data, _migration_report = migration_module.migrate(json_data)
            migration_report.append(_migration_report)

        # store converted version
        json_data["__version__"] = f"{current_version.major}.0.0"

        # manage report
        migration_report.raise_if_error(warn=warn)
        if report is not None:
            report.append(migration_report)

        return json_data

    def _pre_load(self, json_data):
        """
        Parameters
        ----------
        json_data

        Returns
        -------
        modified json_data

        Raises
        ------
        OExceptionCollection, OException

        May be subclassed.
        """
        return json_data

    # ---------------------------------------- end of to subclass ------------------------------------------------------
    def __init__(self, json_data=None, auto_migrate=True, skip_validation=False):
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
        5. post save is called
        """
        # 1. PREPARE STRUCTURE

        # define tables
        self._tables = collections.OrderedDict(
            sorted((camel_to_lower(cls.__name__), Table(cls, self)) for cls in self.models))  # {lower_ref: table,

        # check and prepare tables
        table_activation_map = collections.OrderedDict()
        for t_ref, t in self._tables.items():
            t._dev_check_and_prepare_table()
            table_activation_map[t_ref] = tuple(set(
                [camel_to_lower(t_name) for t_name in t._dev_dynamic_id_tables] +
                list(t._dev_link_dependencies)
            ))

        # check activation map
        activation_order = []
        for i in range(10):
            for t, dependencies in table_activation_map.items():
                if t in activation_order:
                    continue
                if len(set(dependencies).difference(set(activation_order))) == 0:
                    activation_order.append(t)
            if len(activation_order) == len(self._tables):
                break
        else:
            dependencies_map_str = "\n".join([
                f"{t_ref}: {sorted(dependencies)}"
                for t_ref, dependencies in sorted(table_activation_map.items())
            ])
            activation_order_str = "\n".join(sorted(activation_order))
            raise RuntimeError(
                f"dynamic ids dependency problem.\n\n"
                f"Dependency map:\n{dependencies_map_str}\n\n"
                f"Incomplete activation order:\n{activation_order_str}"
            )
        self._activation_order = tuple(activation_order)

        # record links container
        self._dev_relations_manager = RelationsManager(self)

        # 2. POPULATE IF JSON_DATA
        if json_data is None:
            return

        # pre load json data (may be subclassed for custom data operations)
        json_data = self._pre_load(json_data)

        # check version
        if self.version is not None:
            # prepare versions
            current_version = Version.from_text(self.version)
            json_data_version = _get_json_data_version(json_data)

            # migrate if asked and relevant
            if auto_migrate and (json_data_version.major != current_version.major):
                json_data = self.migrate(json_data)

            # update json_data_version
            json_data_version = _get_json_data_version(json_data)

            # check version is not in the future
            if json_data_version > current_version:
                raise VersionIsTooHigh(json_data_version, current_version)

            # check major version is ok
            if json_data_version.major != current_version.major:
                raise VersionIsTooLowAutoMigrateIsOff(json_data_version, current_version)

        # add records
        added_records_by_table = {}  # {table_ref: [records, ...]
        oec = OExceptionCollection()
        for table in self._tables.values():
            with oec.catch_errors():
                try:
                    added_records_by_table[table.get_ref()] = table._dev_add_inert(
                        json_data[table.get_ref()],
                        skip_validation=skip_validation)
                except KeyError:
                    raise MissingTableKey(table.get_ref())
        oec.raise_if_error()

        # activate links in correct order (must be done before uniqueness check so links point on records)
        for t_ref in self._activation_order:
            for r in added_records_by_table.get(t_ref, ()):
                r._dev_activate_links()

        # check uniqueness and set sort index
        for table in self._tables.values():
            table._dev_check_uniqueness()
            table._dev_set_all_sort_indexes()

        # post save
        for records in added_records_by_table.values():
            for r in records:
                r._dev_post_save(True, True)  # created, db_is_initializing

    # --------------------------------------------- public api ---------------------------------------------------------
    @classmethod
    def get_table_refs(cls):
        return [camel_to_lower(m.__name__) for m in cls.models]

    @classmethod
    def generate_excel_input_form(cls, path):
        from .excel import generate_input_form
        generate_input_form(cls(), path)

    def __repr__(self):
        return f"<db: {self.__class__.__name__}>"

    def __str__(self):
        s = f"Database: {self.__class__.__name__}\n"
        for (k, v) in self._tables.items():
            s += f"  {v.get_ref()}\n"
        return s

    def __eq__(self, other):
        return self.to_json() == other.to_json()

    def __dir__(self):
        return list(self._tables) + list(self.__dict__)

    def __getattr__(self, item):
        if item not in self._tables:
            raise AttributeError(f"no table named '{item}'")
        return self._tables[item]

    def __iter__(self) -> Iterable[Table]:
        return iter(self._tables.values())

    # ----------------------------------------- load -------------------------------------------------------------------
    @classmethod
    def from_json(cls, buffer_or_path, auto_migrate=True, skip_validation=False):
        # find mode
        if isinstance(buffer_or_path, str) and os.path.isdir(buffer_or_path):  # multi
            # load content
            json_data = {}

            # version
            admin_path = os.path.join(buffer_or_path, "__admin__.json")
            if not os.path.exists(admin_path):
                raise FileNotFoundError("no __admin__.json file, can't load data")
            with open(admin_path, encoding=CONF.encoding) as f:
                json_data["__version__"] = json_load(f)["__version__"]

            # tables
            for model in cls.models:
                table_ref = camel_to_lower(model.__name__)
                table_path = os.path.join(buffer_or_path, f"{table_ref}.json")
                if not os.path.exists(table_path):
                    raise FileNotFoundError(f"no file for table {table_ref} at path {table_path}")
                with open(table_path, encoding=CONF.encoding) as f:
                    json_data[table_ref] = json_load(f)

        else:  # mono
            # transform to buffer if is path
            is_path = False
            if isinstance(buffer_or_path, str):
                if os.path.isfile(buffer_or_path):  # is path
                    is_path = True
                    buffer_or_path = open(buffer_or_path, encoding=CONF.encoding)
                else:
                    raise FileNotFoundError(f"no such file: {buffer_or_path}")

            # load content
            try:
                json_data = json_load(buffer_or_path)
            finally:
                # close buffer if is path
                if is_path:
                    buffer_or_path.close()

        return cls(json_data=json_data, auto_migrate=auto_migrate, skip_validation=skip_validation)

    # ----------------------------------------- export -----------------------------------------------------------------
    def to_json_data(self):
        d = collections.OrderedDict(
            (t.get_ref(), t.to_json_data()) for t in self._tables.values())
        d["__version__"] = self.version
        d.move_to_end("__version__", last=False)
        return d

    def to_json(self, buffer_or_path=None, indent=2, multi_files=False):
        # mono file
        if not multi_files:
            return json_data_to_json(
                self.to_json_data(),
                buffer_or_path=buffer_or_path,
                indent=indent
            )

        # multi files

        # check dir path
        assert isinstance(buffer_or_path, str), "buffer_or_path must provide dir path in multi_file mode"

        # make dir if needed
        if not os.path.isdir(buffer_or_path):
            os.mkdir(buffer_or_path)

        # dump version
        with open(os.path.join(buffer_or_path, "__admin__.json"), "w", encoding=CONF.encoding) as f:
            json_dump({"__version__": self.version}, f)

        # dump tables
        for table in self._tables.values():
            with open(os.path.join(buffer_or_path, f"{table.get_ref()}.json"), "w", encoding=CONF.encoding) as f:
                table.to_json(buffer_or_path=f, indent=indent)

    # ----------------------------------- miscellaneous ----------------------------------------------------------------
    def get_major_version(self):
        return None if self.version is None else int(self.version.split(".")[0])

    def copy(self) -> "Db":
        """
        copies data and returns a new database
        """
        return self.__class__(json_data=self.to_json_date(), skip_validation=True)
