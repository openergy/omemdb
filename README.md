


# Omemdb 
Omemdb is a in memory Object Relational Mapper giving the ability to write queries and manipulate data using an object oriented paradigm. 
It enables to deal with a database based on you own language.

More specifically, it allows to:
- Create a model database containing tables containing records
- Manipulate simply your data and create field validations
- Store/retrieve your data to/from json

To install omemdb, run: "pip install omemdb" or "conda install omemdb"

### Documentation
Documentation is available in the doc folder.
To ensure the examples in the documentation remain up to date, they are tested by running
the `odocgen` script in omemdb doc directory.

#### users documentation
    
see [doc-users.md](doc/doc-users.md) (use doc-users.py to modify)

#### developer documentation

see [doc-developers.md](doc/doc-developers.md)

Field validation is based on [Marshmallow v2.x framework](https://marshmallow.readthedocs.io/en/2.x-line/).
