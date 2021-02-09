from omemdb.packages.oversion import Version
import omemdb as _omemdb
from .record_link import RecordLink as _RecordLink

from omemdb.packages.oerrors import OExceptionCollection, OException
from omemdb.packages.oerrors.base_errors import \
    NotFoundError as _NotFoundError, \
    ValidationError as _ValidationError, \
    ServerError as _ServerError
from omemdb.packages.oerrors.validation_errors import \
    WrongFormat as _WrongFormat, \
    WrongVersion as _WrongVersion, \
    NotUnique as _NotUnique, \
    NotUniqueTogether as _NotUniqueTogether, \
    InvalidType as _InvalidType, Null as _Null, \
    ForbiddenValue as _ForbiddenValue, \
    CrossValidationFailed as _CrossValidationFailed, \
    MaxValueExceeded as _MaxValueExceeded, \
    InvalidValue as _InvalidValue, \
    InvalidLink
from .marsh_validator import OmemdbMarshValidator  # must be imported at the end


def get_instance(table_ref, record_id=None, field_name=None, sub_field_name=None):
    path = f"/{table_ref}"
    if record_id is not None:
        path += f"/{record_id}"
    if field_name is not None:
        path += f"/{field_name}"
    if sub_field_name is not None:
        path += f"/{sub_field_name}"
    return path


def get_instance_from_record(record, field_name=None):
    return get_instance(record.get_table_ref(), record_id=record.id, field_name=field_name)


def get_version_instance():
    return "/__version__"


class MissingVersionKey(_WrongFormat):
    def __init__(self):
        super().__init__(
            get_version_instance(),
            "data set must contain a '__version__' field with an identifiable major version, or else can't load data"
        )


class MissingTableKey(_WrongFormat):
    def __init__(self, table_ref):
        super().__init__(
            get_instance(table_ref),
            f"data set must contain a '{table_ref} field with a list of all table records'"
        )


class VersionIsTooHigh(_WrongVersion):
    def __init__(
            self,
            json_data_version: Version,
            current_obat_version: Version
    ):
        super().__init__(
            get_version_instance(),
            f"json_data version ({json_data_version}) is higher than current obat version ({current_obat_version}), "
            f"please update obat package",
            version=str(json_data_version),
            expected_version_pattern=f"<={current_obat_version}"
        )


class VersionIsTooLowAutoMigrateIsOff(_WrongVersion):
    def __init__(
            self,
            json_data_version: Version,
            current_obat_version: Version
    ):
        super().__init__(
            get_version_instance(),
            f"received an old version of json_data ({json_data_version}) who's major is < to ({current_obat_version}), "
            f"but auto_migrate is false, can't load json_data, please migrate",
            version=str(json_data_version),
            expected_version_pattern=f"{current_obat_version.major}.*"
        )


class NotUnique(_NotUnique):
    def __init__(self, table_ref, record_id, field_name, value):
        super().__init__(
            get_instance(table_ref, record_id=record_id, field_name=field_name),
            f"a record with the same value ({value}) for given field ({field_name}) already exists",
            value=value
        )


class NotUniqueTogether(_NotUniqueTogether):
    def __init__(self, table_ref, record_id, field_names, values):
        super().__init__(
            get_instance(table_ref, record_id=record_id),
            # fixme: NON_FIELD_KEY should be managed in oerrors
            f"a record with the same values ({values}) for given fields ({field_names}) already exists",
            field_names=field_names,
            values=values
        )


class RecordDoesNotExistError(_NotFoundError):
    description = "Record does not exist."

    def __init__(self, table_ref, record_id=None, message=None):
        if message is not None:
            msg = message
        elif record_id is not None:
            msg = f"table {table_ref} does not contain a record whose id is '{record_id}'"
        else:
            msg = f"record not found in table {table_ref}"
        super().__init__(
            get_instance(table_ref, record_id=record_id),
            msg
        )


class MultipleRecordsReturnedError(_ValidationError):
    description = "Multiple records were returned instead of one."

    def __init__(self, table_ref, message=None):
        msg = f"multiple records found in table {table_ref}" if message is None else message
        super().__init__(get_instance(table_ref), msg)


class TargetRecordNotFound(_NotFoundError):
    description = "Link's target record does not exist."

    @classmethod
    def from_link(cls, non_activated_link: _RecordLink):
        message = f"target record not found (table: '{non_activated_link.target_table_ref}', " \
            f"id: '{non_activated_link.initial_target_id}')"
        return cls(
            get_instance(
                non_activated_link.source_record.get_table_ref(),
                record_id=non_activated_link.source_record.id,
                field_name=non_activated_link.source_field
            ),
            message,
            target_table_ref=non_activated_link.target_table_ref,
            target_id=non_activated_link.initial_target_id
        )


class TableDefinitionError(_ServerError):
    description = "There is a problem with the definition of this table"

    def __init__(self, table_ref, message):
        super().__init__(get_instance(table_ref), message)


class InvalidType(_InvalidType):
    @classmethod
    def from_record(cls, record, field_name, given_type, expected_type):
        return cls(
            get_instance_from_record(record, field_name=field_name),
            f"expected type: {expected_type}, given type: {given_type}",
            expected_type=expected_type,
            given_type=given_type
        )


class Null(_Null):
    @classmethod
    def from_record(cls, record, field_name):
        return cls(
            get_instance_from_record(record, field_name=field_name),
            f"field must not be empty: {field_name}"
        )


class ForbiddenValue(_ForbiddenValue):
    @classmethod
    def from_record(cls, record, field_name, value):
        return cls(
            get_instance_from_record(record, field_name=field_name),
            f"given value ({value}) is forbidden for field {field_name}"
        )


class CrossValidationFailed(_CrossValidationFailed):
    @staticmethod
    def _get_default_message(field_names, values):
        return f"cross-validation failed on fields {field_names} (values: {values})"

    @classmethod
    def from_record(cls, record, field_names, message=None):
        values = tuple(getattr(record, k) for k in field_names)
        if message is None:
            message = cls._get_default_message(field_names, values)
        return cls(
            get_instance_from_record(record),
            message,
            field_names=field_names,
            values=values
        )

    @classmethod
    def from_data(cls, table_ref, record_id, field_names, values, message=None):
        if message is None:
            message = cls._get_default_message(field_names, values)
        return cls(
            get_instance(table_ref, record_id=record_id),
            message,
            field_names=field_names,
            values=values
        )


class IncompleteRecordGroup(_ValidationError):
    description = "Incomplete record group."

    @classmethod
    def from_record(cls, master_record, message):
        return cls(
            get_instance_from_record(master_record),
            message
        )


class NonConsistentRecordGroup(_ValidationError):
    description = "Non consistent record group."

    @classmethod
    def from_record(cls, master_record, message, warning=False):
        return cls(
            get_instance_from_record(master_record),
            message,
            warning=warning
        )


class MaxValueExceeded(_MaxValueExceeded):
    @classmethod
    def from_record(cls, record, field_name, max_value):
        return cls(
            get_instance_from_record(record, field_name=field_name),
            value=getattr(record, field_name),
            max_value=max_value
        )


class InvalidValue(_InvalidValue):
    @classmethod
    def from_data(cls, table_ref, record_id, field_name, value, message):
        return cls(
            get_instance(table_ref, record_id=record_id, field_name=field_name),
            message,
            value=value
        )

    @classmethod
    def from_record(cls, record, field_name, message):
        return cls(
            get_instance_from_record(record, field_name=field_name),
            message,
            value=getattr(record, field_name)
        )


class InvalidTable(_ValidationError):
    @classmethod
    def from_table(cls, table, message):
        return cls(get_instance(table.get_ref()), message)


# ------------------------------------------ commitments ---------------------------------------------------------------
def _commitments_to_str(committed_to_dict):
    s = ""
    for table_ref, record_refs in committed_to_dict.items():
        s += f"{table_ref}\n  "
        s += "\n  ".join(record_refs)
    return s


class UpdateCommitmentError(_ValidationError):
    description = "Update commitment is not fulfilled."

    @classmethod
    def from_record(cls, record: "_omemdb.Record", field_name, committed_to_dict):
        """
        committed_to_dict: {table_ref: [record_ids, ...], ...}
        """
        return cls(
            get_instance_from_record(record, field_name=field_name),
            f"Committed to pointing records, can't update:\n{_commitments_to_str(committed_to_dict)}",
            committed_to_dict=committed_to_dict
        )


class DeleteCommitmentError(_ValidationError):
    @classmethod
    def from_record(cls, record, committed_to_dict):
        """
        committed_to_dict: {table_ref: [record_ids, ...], ...}
        """
        return cls(
            get_instance_from_record(record),
            f"Committed to pointing records, can't delete:\n{_commitments_to_str(committed_to_dict)}",
            committed_to_dict=committed_to_dict
        )
