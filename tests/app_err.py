from omemdb.packages.omarsh import Schema, fields
from omemdb import Record, Db


class Simple(Record):
    class Schema(Schema):
        ref = fields.String()
        age = fields.Integer(required=True)
        optional_age = fields.Integer(missing=None)


class AppErrDb(Db):
    models = [Simple]

