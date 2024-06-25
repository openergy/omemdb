![GitHub](https://img.shields.io/github/license/openergy/omemdb?color=brightgreen)
[![test-and-publish](https://github.com/openergy/omemdb/actions/workflows/opypackage-standard.yml/badge.svg?branch=develop)](https://github.com/openergy/omemdb/actions/workflows/opypackage-standard.yml)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/omemdb)
![PyPI](https://img.shields.io/pypi/v/omemdb)

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

Field validation is based on [Marshmallow v3 framework](https://marshmallow.readthedocs.io/en/stable/).
