# fixme: [GL] update documentation
import tempfile
temp_dir = tempfile.TemporaryDirectory()
work_dir_path = r"C:\Users\geoffroy.destaintot\Downloads"  # temp_dir.name

#@ # omemdb: developers documentation
#@
#@ ## use marshmallow docs
#@
#@ we are using marshmallow v2.x
#@ docs: https://marshmallow.readthedocs.io/en/2.x-line/
#@
#@ ## imports
import os
from omemdb.packages.omarsh import Schema, fields
from omemdb import Record, Db
from omemdb import LinkField, TupleLinkField

#@ Table creation

class Zone(Record):
    class Schema(Schema):  # marshmallow schema, see docs
        ref = fields.String(required=True)

    @property
    def surfaces(self):  # we create our reverse links
        return self.get_pointing_records().select(lambda x: (x.major_zone == self) or (x.minor_zone == self))


class Surface(Record):
    class Schema(Schema):
        ref = fields.String(required=True)  # no need to specify as unique and
        major_zone = LinkField("Zone", required=True)  # Link: point on other table of db
        minor_zone = LinkField("Zone", missing=None)
        constructions = TupleLinkField("Construction", missing=())  # Tuple is authorised (including tuple of links)
        shape = fields.String(missing="rectangle")  # !! use 'missing' keyword for defaults, not 'default'
        vertices = fields.NumpyArray(required=True)  # There is a special type to store NumpyArrays


class Construction(Record):
    class Schema(Schema):
        ref = fields.String(required=True)

    @property
    def surfaces(self):  # we create our reverse links
        return self.get_pointed_records().select(lambda x: self in x.constructions)

#@ Each record contains a primary key that ensure the uniqueness of each record.
#@ When the primary key is not defined, by default the first attribute defined in the schema
#@ will be the primary key
#@ If specified the primary key can be a unique,dynamic_id, sortable and be declared in a TableMeta

class Vertex(Record):
    last_id = 0

    class Schema(Schema):
        pk = fields.String(required=True)  # it is mandatory for the pk to be a string
        x = fields.Integer(required=True)
        y = fields.Integer(required=True)
        z = fields.Integer(required=True)

    class TableMeta:
        unique = (("x", "y", "z"),)  # tuple of unique together fields

    @classmethod
    def _pre_init(cls, data):  # enables a pre-processing before record __init__ method is called
        x, y, z = data["coordinates"]
        current_id = cls.last_id
        cls.last_id += 1
        return dict(
            id=current_id,  # pk will be cast to string when the record is created
            x=x,
            y=y,
            z=z
        )


#@ ### declare database

class AppBuildingDb(Db):
    models = [
        Zone,
        Surface,
        Construction,
        Vertex
    ]


#@ ### instantiate and populate database

def instantiate_and_populate_db():
    db = AppBuildingDb()

    # populate
    for c_i in range(3):
        db.construction.add(ref=f"c{c_i}")

    # create zones (batch)
    db.zone.batch_add((dict(ref=f"z{z_i}") for z_i in range(3)))

    for z_i in range(3):
        # create surfaces
        for s_i in range(3):
            db.surface.add(
                ref=f"s{z_i}{s_i}",
                major_zone=f"z{z_i}",
                minor_zone=None if s_i == 2 else f"z{s_i+1}",
                constructions=[f"c{c_i}" for c_i in range(3)],
                vertices=[[1, 2, 3], [4, 5, 6], [7, 8, 9]]
            )

    return db


db = instantiate_and_populate_db()

#@ ## Authorized fields
#@
#@ We allow all simple fields (List or Dicts are forbidden).
#@
#@ However, we created a Tuple field to replace list fields. The reason is that we want to ensure that we control all
#@ modification on database (for link modification management). Tuple fields are immutable: setitem is necessarily called if changed.

#@ ## Link modification management
#@ Only four methods impact links and trigger a link management workflow:

#@ ### add record

#@
#@table: .add
#@     record: .__init__ -> ._dev_link
#@         record_link: .activate
#@            db: ._dev_register_link
#@
#print(db.surface.add(ref="test"))

#@ ### remove record

#@
#@table: .remove
#@
#@     record: ._dev_unlink
#@
#@         record_link: .deactivate
#@
#@             db: ._dev_unregister_link & db._dev_remove_pointing_links
#@
#@                 record_link: .deactivate
#@
#@                     record:    ._dev_remove_link
#@
#@
#print(db.zone.one("test").delete())

#@ ### setitem
#@
# [record]: .__setitem__
#     [record_link]: .deactivate
#         [db]: ._dev_unregister_link
# #@

#@ ## from_json
#@ 1. all records are added: table._dev_add(link=False, sanitize=False) => records are appended, without registering links nor checking table sanity
#@ 2. table._dev_sanitize() is called on table
#@ 3. all records of table are linked: table._dev_link() => record._dev_link()


#@ # Schema fields definition
# Missing, default, allow_none:
#
# Never use default (it is used to specify a default value when serializing)
# Use missing instead. Use missing=None to allow null values by default
# Use allow_none when you want to allow null values, and want to specify another default (in this case, both allow_none and missing must be used)

#@ Validation best practices
# Validation must be performed, in the following order of preference:
#
# for unique fields:
# with marshmallow field definition
# with marshmallow schema post_load decorator (after deserialization)
# for cross field validation:
# with omemdb dynamic_post_loader (watch out with using missing: won't work if missing is already used in base schema)
# with marshmallow schema post_load decorator (after deserialization)
# with marshmallow schema pre_load decorator (before deserialization)
# if previous solutions are not sufficient, use post_save model method (see 3.). For example, to raise a specific cross-field message using oerrors.
# if links are used, use omemdb _post_save model method. This is the last option, because if it fails, obat may be in a corrupt state, which is not a good situation

#@



