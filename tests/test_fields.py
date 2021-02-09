import unittest
import datetime as dt
import numpy as np
from omemdb.packages.oerrors.oexception_collection import OExceptionCollection
from omemdb.packages.omarsh import fields

from tests.app_fields import AppFields


class TestFields(unittest.TestCase):
    def test_custom_fields(self):
        db = AppFields()
        db.custom_fields_record.add(
            pk=0,
            date_time=dt.datetime.now(),
            date=dt.datetime.now().date(),
            time=dt.datetime.now().time(),
            time_delta=dt.timedelta(seconds=10),
            numpy_array=np.array([[1, 2, 3], [4, 5, 6]])
        )
        for custom_fields_record in db.custom_fields_record:
            self.assertIsInstance(custom_fields_record.id, int)
            self.assertIsInstance(custom_fields_record.date_time, dt.datetime)
            self.assertIsInstance(custom_fields_record.date, dt.date)
            self.assertIsInstance(custom_fields_record.time, dt.time)
            self.assertIsInstance(custom_fields_record.time_delta, dt.timedelta)
            self.assertIsInstance(custom_fields_record.numpy_array, np.ndarray)
            self.assertTrue(np.array_equal(custom_fields_record.numpy_array, np.array([[1, 2, 3], [4, 5, 6]])))

    def test_ref_field(self):
        db = AppFields()

        # check correct value
        db.ref_field_record.add(ref="hello")

        # check spaces
        with self.assertRaises(OExceptionCollection):
            db.ref_field_record.add(ref="h ello")

    def test_python_script_field(self):
        ps = fields.PythonScript(required=True)

        def times2(x): return 2*x

        deserialized = ps.deserialize(times2)

        self.assertEqual(
            "        def times2(x): return 2*x\n",
            deserialized
        )
