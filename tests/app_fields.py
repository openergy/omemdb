from omemdb.packages.omarsh import Schema, fields
from omemdb import Record, Db


class CustomFieldsRecord(Record):
    class Schema(Schema):
        pk = fields.Int(required=True)
        date_time = fields.DateTime(allow_none=True, missing=None)
        date = fields.Date(allow_none=True, missing=None)
        time = fields.Time(allow_none=True, missing=None)
        time_delta = fields.TimeDelta(allow_none=True, missing=None)
        numpy_array = fields.NumpyArray(allow_none=True, missing=None)

    class TableMeta:
        pass


class RefFieldRecord(Record):
    class Schema(Schema):
        ref = fields.RefField(required=True)

    class TableMeta:
        pass


class AllowNoneFieldRecord(Record):
    """
    allow_none documentation:
    Set this to True if None should be considered a valid value during validation/deserialization.
    If missing=None and allow_none is unset, will default to True. Otherwise, the default is False.
    """
    class Schema(Schema):
        ref = fields.RefField(required=True)
        can_be_none = fields.Int(allow_none=True, missing=None)
        cant_be_none = fields.Int(allow_none=False, missing=0)
        default_can_be_none = fields.Int(allow_none=True, missing=None)
        default_cant_be_none = fields.Int(missing=0)


class AppFields(Db):
    models = [
        CustomFieldsRecord,
        RefFieldRecord,
        AllowNoneFieldRecord
    ]
