from omemdb.packages.omarsh import Schema, fields
from omemdb import Record, Db, LinkField, TupleLinkField


class Zone(Record):
    class Schema(Schema):
        ref = fields.String(required=True)

    @property
    def surfaces(self):
        return self.get_pointing_records().surface.select(lambda x: (x.major_zone == self) or (x.minor_zone == self))

    def _pre_delete(self):
        # cascade delete
        for s in self.surfaces:
            if s.major_zone == self:
                if s.minor_zone is None:
                    s.delete()
                else:
                    s.update(major_zone=s.minor_zone, minor_zone=None)
            else:
                s.minor_zone = None


class Surface(Record):
    _post_save_counter = 0

    class Schema(Schema):
        ref = fields.String(required=True)
        major_zone = LinkField("Zone", required=True)
        minor_zone = LinkField("Zone", missing=None)
        constructions = TupleLinkField("Construction", missing=())

    def _post_save(self, **kwargs):
        self._post_save_counter += 1


class Construction(Record):
    class Schema(Schema):
        ref = fields.String(required=True)

    @property
    def surfaces(self):
        return self.get_pointed_records().select(lambda x: self in x.constructions)


def _increment(cls):
    current = cls.last_pk
    cls.last_pk += 1
    return current


class Vertex(Record):
    last_pk = 0

    class Schema(Schema):
        pk = fields.Int(required=True)
        x = fields.Integer(required=True)
        y = fields.Integer(required=True)
        z = fields.Integer(required=True)


class AppBuildingDb(Db):
    models = [
        Zone,
        Surface,
        Construction,
        Vertex
    ]
