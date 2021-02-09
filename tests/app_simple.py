from omemdb.packages.omarsh import Schema, fields
from omemdb import Record, Db, LinkField


class Simple(Record):
    class Schema(Schema):
        ref = fields.String(required=True)
        age = fields.Integer(required=True)
        optional_age = fields.Integer(missing=None)


class Pointing(Record):
    class Schema(Schema):
        pk = fields.Int(required=True)
        simple = LinkField("Simple", missing=None)


class AppSimpleDb(Db):
    models = [
        Simple,
        Pointing
    ]

