from omemdb.packages.omarsh import Schema, fields
from omemdb import Record, Db, LinkField


class Base(Record):
    class Schema(Schema):
        ref = fields.String(required=True)
        age = fields.Integer(required=True)
        optional_age = fields.Integer(missing=None)


def _dynamic_id_fct(x):
    return f"{x.base.ref}/{x.weak_ref}"


class DynamicId(Record):
    class Schema(Schema):
        base = LinkField("Base", required=True)
        weak_ref = fields.String(required=True)

    class TableMeta:
        dynamic_id = _dynamic_id_fct


class AppDynamicId(Db):
    models = [
        Base,
        DynamicId
    ]
