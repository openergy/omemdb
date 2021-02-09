import unittest

from omemdb.packages.omarsh import schema, validate, fields
from omemdb.packages.oerrors import MarshValidator, validation_errors, OExceptionCollection


class MySchema(schema.Schema):
    my_float = fields.Float(validate=validate.Range(min=0, max=1, max_strict=True))


class TestMarsh(unittest.TestCase):
    def test_range_validator(self):
        # correct data
        mv = MarshValidator(MySchema)
        mv.validate(dict(my_float=0.5))

        # bad data
        data, oec = mv.validate(dict(my_float=1.5))
        self.assertEqual(1, len(oec))
        self.assertIsInstance(oec.exception_list()[0], validation_errors.RangeNotRespected)

