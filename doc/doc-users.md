 # omemdb: users documentation

 ## use marshmallow docs

 we are using marshmallow v2.x
 docs: https://marshmallow.readthedocs.io/en/2.x-line/

 ## imports

	import os
	from omemdb.packages.omarsh import Schema, fields
	from omemdb import Record, Db
	from omemdb import LinkField, TupleLinkField


 In the user-docmentation examples are given to exploit an already created model. For specific details on model creation please refer to the developer-documentation.




 # Model creation
 In order to show functionalities of omemdb, first a model must be created.
 Let's declare four tables that will compose our database: Zone, Surface, Consruction, Vertex. Each tables are composed by records.



 ## tables creation

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

 Each record contains a primary key that ensure the uniqueness of each record.
 The first attribute defined in the schema is by default the primary key



 ## database creation


	class AppBuildingDb(Db):
	    models = [
	        Zone,
	        Surface,
	        Construction,
	        Vertex
	    ]



 ## instantiate and populate database: records creation


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


*out:*

	db:
	Database: AppBuildingDb
	  construction
	  surface
	  vertex
	  zone


 multiple distinct database may coexist

	db2 = instantiate_and_populate_db()

	print(f"databases contain same tables and records (db == db2: {db == db2})")
	print(f"but they are distinct (db is not db2: {db is not db2})")
	db2.zone.one("z1").ref= "new_ref"
	print(f"and their content can evolve distinctly (db == db2: {db == db2})")


*out:*

	databases contain same tables and records (db == db2: True)
	but they are distinct (db is not db2: True)
	and their content can evolve distinctly (db == db2: False)

 # Model manipulation
 ## table

 A table is a collection of records of the same type.


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


*out:*

	<table:zone>
	len: 3
	table is defined uniquely by its ref (table.ref: <bound method Table.get_ref of <table:zone>>)

	zone
	  id: z0
	  ref: z0

	zone
	  id: z1
	  ref: z1

	zone
	  id: z2
	  ref: z2

	get table fields and validation rules: {'id': <fields.String(dump_default=<marshmallow.missing>, attribute=None, validate=None, required=False, load_only=False, dump_only=True, load_default=<marshmallow.missing>, allow_none=False, error_messages={'required': 'Missing data for required field.', 'null': 'Field may not be null.', 'validator_failed': 'Invalid value.', 'invalid': 'Not a valid string.', 'invalid_utf8': 'Not a valid utf-8 string.'})>, 'ref': <fields.String(dump_default=<marshmallow.missing>, attribute=None, validate=None, required=True, load_only=False, dump_only=False, load_default=<marshmallow.missing>, allow_none=False, error_messages={'required': 'Missing data for required field.', 'null': 'Field may not be null.', 'validator_failed': 'Invalid value.', 'invalid': 'Not a valid string.', 'invalid_utf8': 'Not a valid utf-8 string.'})>}

 ## queryset

 A queryset is the result of a select query.


	qs = zones.select()
	print(f"all zones:\n{qs}\n")

	qs = zones.select(lambda x: x.ref < "z2")
	print(f"zones with refs < z2:\n{qs}\n")

	# select may also be performed on an existing queryset
	qs2 = qs.select(lambda x: x.ref > "z0")
	print(f"zones with refs > z0 and < z2:\n{qs2}\n")


*out:*

	all zones:
	<Queryset of zone: 3 records>

	zones with refs < z2:
	<Queryset of zone: 2 records>

	zones with refs > z0 and < z2:
	<Queryset of zone: 1 records>


 The obtained records can be deleted, exported.



 queryset api

	# todo [GL]: what is intended in this part? explain what are the public attributes you can get from Queryset?


 iter queryset

	for z in qs:
	    print(z)

	print(f"len(qs): {len(qs)}")
	print(f"first record: {repr(qs[0])}")
	print(f"qs == qs2: {qs == qs2}")


*out:*

	zone
	  id: z0
	  ref: z0

	zone
	  id: z1
	  ref: z1

	len(qs): 2
	first record: <Record zone 'z0'>
	qs == qs2: False

 ## record

  ### get record



 from a table

	z1 = zones.one(lambda x: x.ref == "z1")  # one syntax
	z1 = zones.one("z1")  # pk syntax: will retrieve record who's pk is 'z1'


 from a queryset

	z1 = qs.one(lambda x: x.ref == "z1")


 ### record api

	# get table
	print(f"pk: {z1.id}")
	print(f"db: {z1.get_db()}")
	print(f"table: {z1.get_table}")
	print(z1.get_table)


*out:*

	pk: z1
	db: Database: AppBuildingDb
	  construction
	  surface
	  vertex
	  zone

	table: <bound method Record.get_table of <Record zone 'z1'>>
	<bound method Record.get_table of <Record zone 'z1'>>

 ### add records


	zones.add(ref="z100")  # single add
	zones.batch_add((dict(ref="z101"), dict(ref="z102"), dict(ref="z103")))  # batch add
	print(zones.select())


*out:*

	<Queryset of zone: 7 records>

 ### remove records

	zones.one("z100").delete() # single remove, pk syntax
	zones.one(lambda x: x.ref=="z101").delete()  # single remove, one syntax
	zones.select(lambda x: x.ref in ["z102", "z103"]).delete()  # batch remove, multi syntax
	print(zones.select())


*out:*

	<Queryset of zone: 3 records>

 ### get field value

	s11 = db.surface.one("s11")
	print(s11)


*out:*

	surface
	  id: s11
	  constructions: (<omemdb.record_link.RecordLink object at 0x000001F435E362D0>, <omemdb.record_link.RecordLink object at 0x000001F435E36300>, <omemdb.record_link.RecordLink object at 0x000001F435E36330>)
	  major_zone: <zone: z1>
	  minor_zone: <zone: z2>
	  ref: s11
	  shape: rectangle
	  vertices: [[1 2 3]
	 [4 5 6]
	 [7 8 9]]


 pk

	print("pk (ref for a surface):")
	print(f"  {s11.ref}")  # getitem syntax is the most accurate syntax to access records database fields
	print(f"  {s11.id}")  # gettatr shortcut => is automatically transformed to getitem syntax



*out:*

	pk (ref for a surface):
	  s11
	  s11

 other fields

	print("\nlinks are automatically transformed to records. major_zone example:")
	print(f"  {s11.major_zone}")


*out:*


	links are automatically transformed to records. major_zone example:
	  zone
	  id: z1
	  ref: z1


 ### set field value
 simple field

	s11.ref = "s115"
	print(s11)
	s11.ref = "s11"


*out:*

	surface
	  id: s115
	  constructions: (<omemdb.record_link.RecordLink object at 0x000001F435E362D0>, <omemdb.record_link.RecordLink object at 0x000001F435E36300>, <omemdb.record_link.RecordLink object at 0x000001F435E36330>)
	  major_zone: <zone: z1>
	  minor_zone: <zone: z2>
	  ref: s115
	  shape: rectangle
	  vertices: [[1 2 3]
	 [4 5 6]
	 [7 8 9]]


 link field

	s11.major_zone = db.zone.one("z2")
	print(s11)


*out:*

	surface
	  id: s11
	  constructions: (<omemdb.record_link.RecordLink object at 0x000001F435E362D0>, <omemdb.record_link.RecordLink object at 0x000001F435E36300>, <omemdb.record_link.RecordLink object at 0x000001F435E36330>)
	  major_zone: <zone: z2>
	  minor_zone: <zone: z2>
	  ref: s11
	  shape: rectangle
	  vertices: [[1 2 3]
	 [4 5 6]
	 [7 8 9]]


 ### navigate in pointing/pointed records

	# pointed
	print(f"records pointed by s11:\n {s11.get_pointed_records}")

	# pointing
	print(f"\nrecords pointing on c0:\n {db.construction.one('c0').get_pointing_records}")


*out:*

	records pointed by s11:
	 <bound method Record.get_pointed_records of <Record surface 's11'>>

	records pointing on c0:
	 <bound method Record.get_pointing_records of <Record construction 'c0'>>

 ## export/import


	mono_path = os.path.join(work_dir_path, "mono.json")
	multi_path = os.path.join(work_dir_path, "multi")


 export to json (mono file format)

	db.to_json(mono_path)  # path style

	with open(mono_path, "w") as f:  # buffer style
	    db.to_json(f)


 it is also possible to directly dump in str

	json_str = db.to_json()
	print(f"content:\n''''\n{json_str}\n'''\n\n")


*out:*

	content:
	''''
	{
	  "__version__": null,
	  "construction": [
	    {
	      "id": "c0",
	      "ref": "c0"
	    },
	    {
	      "id": "c1",
	      "ref": "c1"
	    },
	    {
	      "id": "c2",
	      "ref": "c2"
	    }
	  ],
	  "surface": [
	    {
	      "id": "s00",
	      "ref": "s00",
	      "major_zone": "z0",
	      "minor_zone": "z1",
	      "constructions": [
	        "c0",
	        "c1",
	        "c2"
	      ],
	      "shape": "rectangle",
	      "vertices": [
	        [
	          1,
	          2,
	          3
	        ],
	        [
	          4,
	          5,
	          6
	        ],
	        [
	          7,
	          8,
	          9
	        ]
	      ]
	    },
	    {
	      "id": "s01",
	      "ref": "s01",
	      "major_zone": "z0",
	      "minor_zone": "z2",
	      "constructions": [
	        "c0",
	        "c1",
	        "c2"
	      ],
	      "shape": "rectangle",
	      "vertices": [
	        [
	          1,
	          2,
	          3
	        ],
	        [
	          4,
	          5,
	          6
	        ],
	        [
	          7,
	          8,
	          9
	        ]
	      ]
	    },
	    {
	      "id": "s02",
	      "ref": "s02",
	      "major_zone": "z0",
	      "minor_zone": null,
	      "constructions": [
	        "c0",
	        "c1",
	        "c2"
	      ],
	      "shape": "rectangle",
	      "vertices": [
	        [
	          1,
	          2,
	          3
	        ],
	        [
	          4,
	          5,
	          6
	        ],
	        [
	          7,
	          8,
	          9
	        ]
	      ]
	    },
	    {
	      "id": "s10",
	      "ref": "s10",
	      "major_zone": "z1",
	      "minor_zone": "z1",
	      "constructions": [
	        "c0",
	        "c1",
	        "c2"
	      ],
	      "shape": "rectangle",
	      "vertices": [
	        [
	          1,
	          2,
	          3
	        ],
	        [
	          4,
	          5,
	          6
	        ],
	        [
	          7,
	          8,
	          9
	        ]
	      ]
	    },
	    {
	      "id": "s11",
	      "ref": "s11",
	      "major_zone": "z2",
	      "minor_zone": "z2",
	      "constructions": [
	        "c0",
	        "c1",
	        "c2"
	      ],
	      "shape": "rectangle",
	      "vertices": [
	        [
	          1,
	          2,
	          3
	        ],
	        [
	          4,
	          5,
	          6
	        ],
	        [
	          7,
	          8,
	          9
	        ]
	      ]
	    },
	    {
	      "id": "s12",
	      "ref": "s12",
	      "major_zone": "z1",
	      "minor_zone": null,
	      "constructions": [
	        "c0",
	        "c1",
	        "c2"
	      ],
	      "shape": "rectangle",
	      "vertices": [
	        [
	          1,
	          2,
	          3
	        ],
	        [
	          4,
	          5,
	          6
	        ],
	        [
	          7,
	          8,
	          9
	        ]
	      ]
	    },
	    {
	      "id": "s20",
	      "ref": "s20",
	      "major_zone": "z2",
	      "minor_zone": "z1",
	      "constructions": [
	        "c0",
	        "c1",
	        "c2"
	      ],
	      "shape": "rectangle",
	      "vertices": [
	        [
	          1,
	          2,
	          3
	        ],
	        [
	          4,
	          5,
	          6
	        ],
	        [
	          7,
	          8,
	          9
	        ]
	      ]
	    },
	    {
	      "id": "s21",
	      "ref": "s21",
	      "major_zone": "z2",
	      "minor_zone": "z2",
	      "constructions": [
	        "c0",
	        "c1",
	        "c2"
	      ],
	      "shape": "rectangle",
	      "vertices": [
	        [
	          1,
	          2,
	          3
	        ],
	        [
	          4,
	          5,
	          6
	        ],
	        [
	          7,
	          8,
	          9
	        ]
	      ]
	    },
	    {
	      "id": "s22",
	      "ref": "s22",
	      "major_zone": "z2",
	      "minor_zone": null,
	      "constructions": [
	        "c0",
	        "c1",
	        "c2"
	      ],
	      "shape": "rectangle",
	      "vertices": [
	        [
	          1,
	          2,
	          3
	        ],
	        [
	          4,
	          5,
	          6
	        ],
	        [
	          7,
	          8,
	          9
	        ]
	      ]
	    }
	  ],
	  "vertex": [],
	  "zone": [
	    {
	      "id": "z0",
	      "ref": "z0"
	    },
	    {
	      "id": "z1",
	      "ref": "z1"
	    },
	    {
	      "id": "z2",
	      "ref": "z2"
	    }
	  ]
	}
	'''



 export to json (multi file format)

	db.to_json(multi_path, multi_files=True)  # only path file  is available in multi-mode


 import

	db_mono = AppBuildingDb.from_json(mono_path)  # buffer style is also available
	db_multi = AppBuildingDb.from_json(multi_path)

	print(f"db_mono == db: {db_mono == db}")
	print(f"db_multi == db: {db_multi == db}")


*out:*

	db_mono == db: True
	db_multi == db: True


