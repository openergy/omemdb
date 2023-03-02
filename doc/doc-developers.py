#@ # omemdb: developers documentation
#@
#@ ## use marshmallow docs
#@
#@ we are using marshmallow v2.x
#@ docs: https://marshmallow.readthedocs.io/en/2.x-line/
#@
#@ ## imports
import os
from omemdb.packages.omarsh import Schema, fields, validate, post_load , pre_load
from omemdb import Record, Db
from omemdb import LinkField, TupleLinkField
from omemdb.oerrors_omemdb import OExceptionCollection, InvalidValue

#@ # Table creation
#@ Tables are collections of records. Let's create tables that will compose our database.

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

    class TableMeta:
        unique = (("x", "y", "z"),)  # tuple of unique together fields


class Construction(Record):
    class Schema(Schema):
        ref = fields.String(required=True)

    @property
    def surfaces(self):  # we create our reverse links
        return self.get_pointed_records().select(lambda x: self in x.constructions)

#@ Each record of a tables contains a primary key that ensure its uniqueness.
#@ The primary key is by default the first attribute defined in the schema

#@ # TableMeta
#@ TableMeta class can be used to specify information on fields:
#@ - a field id can be created dynamically by specifying a "dynamic_id" in the table meta.
#@ - a field can be specified as unique in the table, uniqueness can be attributed to a unique field or a set of fields
#@ - all records have a get_index field, by default records are sorted in ascending order, if a specific order is needed a field can have a sort_index

#@ For example, let's define a new table with TableMeta:

#@ dynamic_id and sortable example:

def get_ref(record):
    """
    function to get ids dynamically
    """
    return f"{record.construction.ref}~{record.sort_index}"

def get_sort_group(layer):
    """
    defining the group in which the record will be sorted
    """
    return layer.construction.id


class Layer(Record):

    class Schema(Schema):
        construction = LinkField("Construction", required=True)  # delete commitment: construction to layer
        material = fields.String(required=True, validate=validate.OneOf(("concrete","wood","insulation")))
        thickness = fields.Float(required=True, validate=validate.Range(0, min_strict=True))

    class TableMeta:
        dynamic_id = get_ref, ("Construction",)
        sortable = get_sort_group  # for vertical surfaces: interior to exterior, for horizontal surfaces: down to up


#@ unique id example
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

#@ # Authorized fields
#@ All simple fields are allowed. List or Dicts are forbidden.
#@ However, a Tuple field is defined to replace list fields. The reason is to ensure that all modifications are controlled on a database (for link modification management).
#@ Tuple fields are immutable: setitem is necessarily called if changed.

#@ ## Link modification management
#@ Only four methods impact links and trigger a link management workflow:
#@ ### add record
#@ table: .add
#@     record: .__init__ -> ._dev_link
#@         record_link: .activate
#@            db: ._dev_register_link

#@ ### remove record
#@ table: .delete
#@     record: ._dev_unlink
#@         record_link: .deactivate
#@             db: ._dev_unregister_link & db._dev_remove_pointing_links
#@                 record_link: .deactivate
#@                     record:    ._dev_remove_link

#@ ### setitem
#@ [record]: .__setitem__
#@     [record_link]: .deactivate
#@         [db]: ._dev_unregister_link
#@
#@ ### from_json
#@ 1. all records are added: table._dev_add(link=False, sanitize=False) => records are appended, without registering links nor checking table sanity
#@ 2. table._dev_sanitize() is called on table
#@ 3. all records of table are linked: table._dev_link() => record._dev_link()


#@ # Schema fields definition
#@ Fields are used to describe the Schema attributes to database tables.
#@ When creating a schema fields are defined as class attributes.
#@ 1. Simple fields types are defined in the the omarsh package based on marshmallow
#@ 2. More complex fields are defined for link management: LinkField, TupleLinkField

#@ ## Default field values
#@ Default values can be set when records are created:

class Surface(Record):
    class Schema(Schema):
        ref = fields.String(required=True)  # no need to specify as unique and
        major_zone = LinkField("Zone", required=True)  # Link: point on other table of db
        minor_zone = LinkField("Zone", missing=None)
        construction = TupleLinkField("Construction", missing=())  # Tuple is authorized (including tuple of links)
        shape = fields.String(missing="rectangle")  # !! use 'missing' keyword for defaults, not 'default'
        vertices = fields.NumpyArray(required=True)  # There is a special type to store NumpyArrays


#@ ## Missing, default, allow_none:
#@
#@ - Never use default (it is used to specify a default value when serializing)
#@ - Use missing instead. Use missing=None to allow null or specific values by default
#@ - Use allow_none when you want to allow null values, and want to specify another default (in this case, both allow_none and missing must be used)

#@ # Validation best practices
#@ When creating a record, input data validation must be performed. In the following order of preference:
#@
#@ ## 1. for unique fields:
#@
#@ * with marshmallow field definition and validate argument

class TestSystem(Record):

    class Schema(Schema):
        name = fields.String(required=True, validate=validate.Length(1))
        is_centralized = fields.Boolean(required=True)
        type = fields.String(required=True, validate=validate.OneOf(
            ("system_centralized", "system_decentralized_1", "system_decentralized_2")))
        capacity = fields.Float(missing=None, validate=validate.Range(0))

#@ * with marshmallow schema post_load decorator (after deserialization): see marshmallow documentation
#@
#@ ## 2. for cross field validation:
#@
#@ * with omemdb dynamic_post_loader (watch out with using missing: won't work if missing is already used in base schema)

class HeatingSystem(Record):

    class Schema(Schema):
        ref = fields.String(required=True, validate=validate.Length(1))
        is_centralized = fields.Boolean(required=True)
        type = fields.String(required=True, validate=validate.OneOf(("system_centralized","system_decentralized_1","system_decentralized_2")))
        capacity = fields.Float(missing=None,validate=validate.Range(0))

        def dynamic_post_load(self, data):
            dsd = dict()

            # --- manage decentralized
            if not data["is_centralized"]:
                dsd["type"] = fields.String(
                    required=True,
                    validate=validate.OneOf(("system_decentralized_1", "system_decentralized_2"))
                )
                # clear all other fields
                for field in ["capacity"]:
                    data[field] = None

            else:
                for field in ["type"]:
                    data[field]="system_centralized"

            return dsd

#@
#@ * with marshmallow schema post_load decorator (after deserialization): see marshmallow documentation
#@ * with marshmallow schema pre_load decorator to validate the input data (before deserialization): see marshmallow documentation

#@ * if previous solutions are not sufficient, use post_save model method (see 3.). For example, to raise a specific cross-field message using oerrors.
#@
#@ ## 3. if links are used, use omemdb _post_save model method:
#@ * this is the last option, because if it fails, model may be in a corrupt state, which is not a good situation
#@
#@ ### instantiate and populate database
#@ ### declare database
class AppBuildingDb(Db):
    models = [
        Zone,
        Surface,
        Construction,
        Layer,
        Vertex,
        HeatingSystem
    ]
#@ ### populate database
def instantiate_and_populate_db():

    db = AppBuildingDb()
    # populate
    for c_i in range(3):
        db.construction.add(ref=f"c{c_i}")

    # populate
    for l_i in range(5):
        db.layer.add(ref=f"l{l_i}",
                     construction="c0",
                     material="concrete",
                     thickness=0.15)

    # populate
    for hs_i in range(3):
        db.heating_system.add(ref=f"hs{hs_i}",
                              is_centralized=False,
                              type="system_decentralized_1",
                              capacity=1000
                              )

    # create zones (batch)
    db.zone.batch_add((dict(ref=f"z{z_i}") for z_i in range(3)))

    for z_i in range(3):
        # create surfaces
        for s_i in range(3):
            db.surface.add(
                ref=f"s{z_i}{s_i}",
                major_zone=f"z{z_i}",
                minor_zone=None if s_i == 2 else f"z{s_i+1}",
                construction=[f"c{c_i}" for c_i in range(3)],
                vertices=[[1, 2, 3], [4, 5, 6], [7, 8, 9]]
            )

    return db


db = instantiate_and_populate_db()

#@ Check dynamic_post_load is working
heating_system_1 = db.heating_system.one("hs1")
print(f"initial record {heating_system_1}")
heating_system_1.update(is_centralized=True)
print(f"updated record with post load validation{heating_system_1}")

#@ Check that sortable meta is working
l1 = db.layer.one(lambda x: x.sort_index==0)
print(f"first layer{l1}")

#@ Need to add a new layer as first layer, interior insulation
db.layer.add(
    ref="insulation",
    material="insulation",
    construction="c0",
    thickness="0.15",
    sort_index=0
)

l2 = db.layer.one(lambda x: x.sort_index==0)
print(f"first layer after adding the insulation {l2}")
#@
