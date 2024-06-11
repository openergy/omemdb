import unittest

from omemdb.packages.omarsh import schema, validate, fields
from omemdb.packages.oerrors import MarshValidator, validation_errors, OExceptionCollection


class MySchema(schema.Schema):
    my_float = fields.Float(validate=validate.Range(min=0, max=1, max_strict=True))
    my_string = fields.String(validate=validate.OneOf(["choice1", "choice2"]), required=False)


class TestMarsh(unittest.TestCase):
    def test_range_validator(self):
        # correct data
        mv = MarshValidator(MySchema)
        mv.validate(dict(my_float=0.5))

        # bad data
        data, oec = mv.validate(dict(my_float=1.5))
        self.assertEqual(1, len(oec))
        self.assertIsInstance(oec.exception_list()[0], validation_errors.RangeNotRespected)

    def test_oneof_validator(self):
        # correct data
        mv = MarshValidator(MySchema)
        mv.validate(dict(my_float=0.5, my_string="choice1"))

        # bad data
        data, oec = mv.validate(dict(my_float=0.5, my_string="unavailable choice"))
        self.assertEqual(1, len(oec))
        self.assertIsInstance(oec.exception_list()[0], validation_errors.InvalidChoice)
