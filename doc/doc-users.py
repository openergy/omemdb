import tempfile

temp_dir = tempfile.TemporaryDirectory()
work_dir_path = r"C:\Users\c.cruveiller\Downloads"  # temp_dir.name

#@ # omemdb: users documentation
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

#@ In the user-docmentation examples are given to exploit an already created model. For specific details on model creation please refer to the developer-documentation.


#@ # Model creation
#@ In order to show functionalities of omemdb, first a model must be created.
#@ Let's declare four tables that will compose our database: Zone, Surface, Consruction, Vertex. Each tables are composed by records.

#@ ## tables creation
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
        minor_zone = LinkField("Zone", load_default=None)
        constructions = TupleLinkField("Construction", load_default=())  # Tuple is authorised (including tuple of links)
        shape = fields.String(load_default="rectangle")  # !! use 'missing' keyword for defaults, not 'default'
        vertices = fields.NumpyArray(required=True)  # There is a special type to store NumpyArrays


class Construction(Record):
    class Schema(Schema):
        ref = fields.String(required=True)

    @property
    def surfaces(self):  # we create our reverse links
        return self.get_pointed_records().select(lambda x: self in x.constructions)


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
#@ Each record contains a primary key that ensure the uniqueness of each record.
#@ The first attribute defined in the schema is by default the primary key

#@ ## database creation

class AppBuildingDb(Db):
    models = [
        Zone,
        Surface,
        Construction,
        Vertex
    ]


#@ ## instantiate and populate database: records creation

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
print(f"db:\n{db}")

#@ multiple distinct database may coexist
db2 = instantiate_and_populate_db()

print(f"databases contain same tables and records (db == db2: {db == db2})")
print(f"but they are distinct (db is not db2: {db is not db2})")
db2.zone.one("z1").ref= "new_ref"
print(f"and their content can evolve distinctly (db == db2: {db == db2})")

#@ # Model manipulation
#@ ## table
#@
#@ A table is a collection of records of the same type.

# get zones table
zones = db.zone  # get table by ref
print(f"{zones}")
print(f"len: {len(zones)}")
print(f"table is defined uniquely by its ref (table.ref: {zones.get_ref})\n")

# iter zones
for z in zones:
    print(z)

# get fields
print(f"get table fields and validation rules: {zones.get_fields()}")

#@ ## queryset
#@
#@ A queryset is the result of a select query.

qs = zones.select()
print(f"all zones:\n{qs}\n")

qs = zones.select(lambda x: x.ref < "z2")
print(f"zones with refs < z2:\n{qs}\n")

# select may also be performed on an existing queryset
qs2 = qs.select(lambda x: x.ref > "z0")
print(f"zones with refs > z0 and < z2:\n{qs2}\n")

#@ The obtained records can be deleted, exported.

#@ queryset api
# todo [GL]: what is intended in this part? explain what are the public attributes you can get from Queryset?

#@ iter queryset
for z in qs:
    print(z)

print(f"len(qs): {len(qs)}")
print(f"first record: {repr(qs[0])}")
print(f"qs == qs2: {qs == qs2}")

#@ ## record
#@
#@  ### get record

#@ from a table
z1 = zones.one(lambda x: x.ref == "z1")  # one syntax
z1 = zones.one("z1")  # pk syntax: will retrieve record who's pk is 'z1'

#@ from a queryset
z1 = qs.one(lambda x: x.ref == "z1")

#@ ### record api
# get table
print(f"pk: {z1.id}")
print(f"db: {z1.get_db()}")
print(f"table: {z1.get_table}")
print(z1.get_table)

#@ ### add records

zones.add(ref="z100")  # single add
zones.batch_add((dict(ref="z101"), dict(ref="z102"), dict(ref="z103")))  # batch add
print(zones.select())

#@ ### remove records
zones.one("z100").delete() # single remove, pk syntax
zones.one(lambda x: x.ref=="z101").delete()  # single remove, one syntax
zones.select(lambda x: x.ref in ["z102", "z103"]).delete()  # batch remove, multi syntax
print(zones.select())

#@ ### get field value
s11 = db.surface.one("s11")
print(s11)

#@ pk
print("pk (ref for a surface):")
print(f"  {s11.ref}")  # getitem syntax is the most accurate syntax to access records database fields
print(f"  {s11.id}")  # gettatr shortcut => is automatically transformed to getitem syntax


#@ other fields
print("\nlinks are automatically transformed to records. major_zone example:")
print(f"  {s11.major_zone}")

#@ ### set field value
#@ simple field
s11.ref = "s115"
print(s11)
s11.ref = "s11"

#@ link field
s11.major_zone = db.zone.one("z2")
print(s11)

#@ ### navigate in pointing/pointed records
# pointed
print(f"records pointed by s11:\n {s11.get_pointed_records}")

# pointing
print(f"\nrecords pointing on c0:\n {db.construction.one('c0').get_pointing_records}")

#@ ## export/import

mono_path = os.path.join(work_dir_path, "mono.json")
multi_path = os.path.join(work_dir_path, "multi")

#@ export to json (mono file format)
db.to_json(mono_path)  # path style

with open(mono_path, "w") as f:  # buffer style
    db.to_json(f)

#@ it is also possible to directly dump in str
json_str = db.to_json()
print(f"content:\n''''\n{json_str}\n'''\n\n")

#@ export to json (multi file format)
db.to_json(multi_path, multi_files=True)  # only path file  is available in multi-mode

#@ import
db_mono = AppBuildingDb.from_json(mono_path)  # buffer style is also available
db_multi = AppBuildingDb.from_json(multi_path)

print(f"db_mono == db: {db_mono == db}")
print(f"db_multi == db: {db_multi == db}")

#@

temp_dir.cleanup()
