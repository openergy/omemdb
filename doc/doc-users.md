 # omemdb

 ## use marshmallow docs

 we are using marshmallow v2.x
 docs: https://marshmallow.readthedocs.io/en/2.x-line/

 ## imports

	import os
	from obat.packages.omemdb import Record, Schema, fields, Db


 ## database

 A database is a collection of tables containg records.

 ### declare schema


	# declare tables

	class Zone(Record):
	    class Schema(Schema):  # marshmallow schema, see docs
	        ref = fields.String()

	    class TableMeta:
	        pk = "ref"  # define a field as primary key, if none is specified, an _auto_pk is automatically created and
	                    # managed by the dB

	    @property
	    def surfaces(self):  # we create our reverse links
	        return self.pointing_records.select(lambda x: (x.major_zone == self) or (x.minor_zone == self))


	class Surface(Record):
	    class Schema(Schema):
	        ref = fields.String()  # no need to specify as unique and
	        major_zone = fields.Link("Zone", required=True)  # Link: point on other table of db
	        minor_zone = fields.Link("Zone")
	        constructions = fields.Tuple(fields.Link("Construction"))  # Tuple is authorised (including tuple of links)
	        shape = fields.String(missing="rectangle")  # !! use 'missing' keyword for defaults, not 'default'
	        vertices = fields.NumpyArray(required=True)  # There is a special type to store NumpyArrays

	    class TableMeta:
	        pk = "ref"


	class Construction(Record):
	    class Schema(Schema):
	        ref = fields.String()

	    class TableMeta:
	        pk = "ref"

	    @property
	    def surfaces(self):  # we create our reverse links
	        return self.pointed_records.select(lambda x: self in x.constructions)


	def _increment(cls):
	    current = cls.last_id
	    cls.last_id += 1
	    return current


	class Vertex(Record):
	    last_id = 0

	    class Schema(Schema):
	        id = fields.String()  # it is mandatory for the pk to be a string
	        x = fields.Integer(required=True)
	        y = fields.Integer(required=True)
	        z = fields.Integer(required=True)

	    class TableMeta:
	        pk = "id"
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

	# declare database

	class AppBuildingDb(Db):
	    models = [
	        Zone,
	        Surface,
	        Construction,
	        Vertex
	    ]



 ### instantiate and populate database


	def instantiate_and_populate_db():
	    db = AppBuildingDb()

	    # populate
	    for c_i in range(3):
	        db["Construction"].add(ref=f"c{c_i}")

	    # create zones (batch)
	    db["Zone"].batch_add((dict(ref=f"z{z_i}") for z_i in range(3)))

	    for z_i in range(3):
	        # create surfaces
	        for s_i in range(3):
	            db["Surface"].add(
	                ref=f"s{z_i}{s_i}",
	                major_zone=f"@Zone::z{z_i}",
	                minor_zone=None if s_i == 2 else f"@Zone::z{s_i+1}",
	                constructions=[f"@Construction::c{c_i}" for c_i in range(3)],
	                vertices=[[1, 2, 3], [4, 5, 6], [7, 8, 9]]
	            )

	    return db


	db = instantiate_and_populate_db()
	print(f"db:\n{db}")

	# multiple distinct database may coexist
	db2 = instantiate_and_populate_db()

	print(f"databases contain same tables and records (db == db2: {db == db2})")
	print(f"but they are distinct (db is not db2: {db is not db2})")
	db2["Zone"]["z1"]["ref"] = "new_ref"
	print(f"and their content can evolve distinctly (db == db2: {db == db2})")


*out:*

	db:
	Database: AppBuildingDb
	  Construction
	  Surface
	  Vertex
	  Zone

	databases contain same tables and records (db == db2: True)
	but they are distinct (db is not db2: True)
	and their content can evolve distinctly (db == db2: False)

 ## table

 A table is a collection of records of the same type.


	# get zones table
	zones = db["Zone"]  # get table by ref
	print(f"{zones}")
	print(f"len: {len(zones)}")
	print(f"table is defined uniquely by its ref (table.ref: {zones.ref})\n")

	# iter zones
	for z in zones:
	    print(z)


*out:*

	<table:Zone>
	len: 3
	table is defined uniquely by its ref (table.ref: Zone)

	Zone
	  ref: z0

	Zone
	  ref: z1

	Zone
	  ref: z2


 ## queryset

 A queryset is the result of a select query.


	qs = zones.select()
	print(f"all zones:\n{qs}\n")

	qs = zones.select(lambda x: x["ref"] < "z2")
	print(f"zones with refs < z2:\n{qs}\n")

	# select may also be performed on an existing queryset
	qs2 = qs.select(lambda x: x["ref"] > "z0")
	print(f"zones with refs > z0 and < z2:\n{qs2}\n")


*out:*

	all zones:
	Queryset:
	  <Zone: z0>
	  <Zone: z1>
	  <Zone: z2>

	zones with refs < z2:
	Queryset:
	  <Zone: z0>
	  <Zone: z1>

	zones with refs > z0 and < z2:
	Queryset:
	  <Zone: z1>


 queryset api


	# iter queryset
	for z in qs:
	    print(z)

	print(f"len(qs): {len(qs)}")
	print(f"first record: {repr(qs[0])}")
	print(f"qs == qs2: {qs == qs2}")


*out:*

	Zone
	  ref: z0

	Zone
	  ref: z1

	len(qs): 2
	first record: <Zone: z0>
	qs == qs2: False

 ## record

  ### get record


	# from a table
	z1 = zones.one(lambda x: x["ref"] == "z1")  # one syntax
	z1 = zones["z1"]  # pk syntax: will retrieve record who's pk is 'z1'

	# from a queryset
	z1 = qs.one(lambda x: x["ref"] == "z1")


 ### record api

	# get table
	print(f"identifier: {z1.identifier}")
	print(f"db: {z1.db}")
	print(f"table: {z1.table}")
	print(z1.table)


*out:*

	identifier: @Zone::z1
	db: Database: AppBuildingDb
	  Construction
	  Surface
	  Vertex
	  Zone

	table: <table:Zone>
	<table:Zone>

 ### add records


	zones.add(ref="z100")  # single add
	zones.batch_add((dict(ref="z101"), dict(ref="z102"), dict(ref="z103")))  # batch add
	print(zones.select())


*out:*

	Queryset:
	  <Zone: z0>
	  <Zone: z100>
	  <Zone: z101>
	  <Zone: z102>
	  <Zone: z103>
	  <Zone: z1>
	  <Zone: z2>

 ### remove records

	zones.remove(zones["z100"])  # single remove, record syntax
	zones.remove("z101")  # single remove, pk syntax
	zones.remove(("z102", zones["z103"]))  # batch remove, multi syntax
	print(zones.select())


*out:*

	Queryset:
	  <Zone: z0>
	  <Zone: z1>
	  <Zone: z2>

 ### get field value

	s11 = db["Surface"]["s11"]
	print(s11)

	# pk
	print("pk (ref for a surface):")
	print(f"  {s11['ref']}")  # getitem syntax is the most accurate syntax to access records database fields
	print(f"  {s11.my_pk}")  # .my_pk shortcut => is automatically transformed to ['ref']
	print(f"  {s11.ref}")  # gettatr shortcut => is automatically transformed to getitem syntax (if .ref was not defined as a field or method)

	# other fields
	print("\nlinks are automatically transformed to records. major_zone example:")
	print(f"  {s11['major_zone']}")
	print(f"  {s11.major_zone}")



*out:*

	Surface
	  constructions: (<Link: @Construction::c0>, <Link: @Construction::c1>, <Link: @Construction::c2>)
	  major_zone: <Link: @Zone::z1>
	  minor_zone: <Link: @Zone::z2>
	  ref: s11
	  shape: rectangle
	  vertices: [[1 2 3]
	 [4 5 6]
	 [7 8 9]]

	pk (ref for a surface):
	  s11
	  s11
	  s11

	links are automatically transformed to records. major_zone example:
	  Zone
	  ref: z1

	  Zone
	  ref: z1


 ### set field value

	# simple field
	s11["ref"] = "s115"
	print(s11)
	s11["ref"] = "s11"

	# link field
	s11["major_zone"] = db["Zone"]["z2"]
	print(s11)


*out:*

	Surface
	  constructions: (<Link: @Construction::c0>, <Link: @Construction::c1>, <Link: @Construction::c2>)
	  major_zone: <Link: @Zone::z1>
	  minor_zone: <Link: @Zone::z2>
	  ref: s115
	  shape: rectangle
	  vertices: [[1 2 3]
	 [4 5 6]
	 [7 8 9]]

	Surface
	  constructions: (<Link: @Construction::c0>, <Link: @Construction::c1>, <Link: @Construction::c2>)
	  major_zone: <Link: @Zone::z2>
	  minor_zone: <Link: @Zone::z2>
	  ref: s11
	  shape: rectangle
	  vertices: [[1 2 3]
	 [4 5 6]
	 [7 8 9]]


 ### navigate in pointing/pointed records

	# pointed
	print(f"records pointed by s11:\n {s11.pointed_records}")

	# pointing
	print(f"\nrecords pointing on c0:\n {db['Construction']['c0'].pointing_records}")


*out:*

	records pointed by s11:
	 Queryset:
	  <Construction: c0>
	  <Construction: c1>
	  <Construction: c2>
	  <Zone: z2>

	records pointing on c0:
	 Queryset:
	  <Surface: s00>
	  <Surface: s01>
	  <Surface: s02>
	  <Surface: s10>
	  <Surface: s11>
	  <Surface: s12>
	  <Surface: s20>
	  <Surface: s21>
	  <Surface: s22>

 ## export/import


	mono_path = os.path.join(work_dir_path, "mono.json")
	multi_path = os.path.join(work_dir_path, "multi")

	# export to json (mono file format)
	db.to_json(mono_path)  # path style

	with open(mono_path, "w") as f:  # buffer style
	    db.to_json(f)

	# it is also possible to directly dump in str
	json_str = db.to_json()
	print(f"content:\n''''\n{json_str}\n'''\n\n")

	# export to json (multi file format)
	db.to_json(multi_path, multi_files=True)  # only path file  is available in multi-mode

	# import
	db_mono = AppBuildingDb.from_json(mono_path)  # buffer style is also available
	db_multi = AppBuildingDb.from_json(multi_path)

	print(f"db_mono == db: {db_mono == db}")
	print(f"db_multi == db: {db_multi == db}")


*out:*

	content:
	''''
	{
	  "Construction": [
	    {
	      "ref": "c0"
	    },
	    {
	      "ref": "c1"
	    },
	    {
	      "ref": "c2"
	    }
	  ],
	  "Surface": [
	    {
	      "ref": "s00",
	      "constructions": [
	        "@Construction::c0",
	        "@Construction::c1",
	        "@Construction::c2"
	      ],
	      "major_zone": "@Zone::z0",
	      "minor_zone": "@Zone::z1",
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
	      "ref": "s01",
	      "constructions": [
	        "@Construction::c0",
	        "@Construction::c1",
	        "@Construction::c2"
	      ],
	      "major_zone": "@Zone::z0",
	      "minor_zone": "@Zone::z2",
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
	      "ref": "s02",
	      "constructions": [
	        "@Construction::c0",
	        "@Construction::c1",
	        "@Construction::c2"
	      ],
	      "major_zone": "@Zone::z0",
	      "minor_zone": null,
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
	      "ref": "s10",
	      "constructions": [
	        "@Construction::c0",
	        "@Construction::c1",
	        "@Construction::c2"
	      ],
	      "major_zone": "@Zone::z1",
	      "minor_zone": "@Zone::z1",
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
	      "ref": "s11",
	      "constructions": [
	        "@Construction::c0",
	        "@Construction::c1",
	        "@Construction::c2"
	      ],
	      "major_zone": "@Zone::z2",
	      "minor_zone": "@Zone::z2",
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
	      "ref": "s12",
	      "constructions": [
	        "@Construction::c0",
	        "@Construction::c1",
	        "@Construction::c2"
	      ],
	      "major_zone": "@Zone::z1",
	      "minor_zone": null,
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
	      "ref": "s20",
	      "constructions": [
	        "@Construction::c0",
	        "@Construction::c1",
	        "@Construction::c2"
	      ],
	      "major_zone": "@Zone::z2",
	      "minor_zone": "@Zone::z1",
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
	      "ref": "s21",
	      "constructions": [
	        "@Construction::c0",
	        "@Construction::c1",
	        "@Construction::c2"
	      ],
	      "major_zone": "@Zone::z2",
	      "minor_zone": "@Zone::z2",
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
	      "ref": "s22",
	      "constructions": [
	        "@Construction::c0",
	        "@Construction::c1",
	        "@Construction::c2"
	      ],
	      "major_zone": "@Zone::z2",
	      "minor_zone": null,
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
	  "Vertex": [],
	  "Zone": [
	    {
	      "ref": "z0"
	    },
	    {
	      "ref": "z1"
	    },
	    {
	      "ref": "z2"
	    }
	  ]
	}
	'''


	db_mono == db: True
	db_multi == db: True


