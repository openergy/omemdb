import unittest
import tempfile
import os

from omemdb import TableDefinitionError, RecordDoesNotExistError, \
    MultipleRecordsReturnedError
from omemdb.packages.oerrors import OExceptionCollection, ValidationError

from tests.app_simple import AppSimpleDb
from tests.app_err import AppErrDb
from tests.app_building import AppBuildingDb
from tests.app_dynamic_id import AppDynamicId


def building_standard_populate():
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
                constructions=[f"c{c_i}" for c_i in range(3)]
            )

    return db


class OmemdbTest(unittest.TestCase):
    def test_basic_operations(self):
        # create database
        db = AppSimpleDb()

        # get table
        simple_table = db.simple

        # add simple record
        r1 = simple_table.add(
            ref="r-1",
            age=-1
        )

        # add multiple records
        simple_table.batch_add([dict(ref=f"r{i}", age=i) for i in range(10)])

        # check table length
        self.assertEqual(11, len(simple_table))

        # select all
        qs = simple_table.select()

        # check qs length
        self.assertEqual(11, len(qs))

        # select record
        self.assertEqual(
            r1,
            simple_table.one(lambda x: x.ref == "r-1")
        )
        self.assertEqual(
            r1,
            simple_table.one(lambda x: x.id == "r-1")
        )
        self.assertEqual(
            r1,
            simple_table.one("r-1")
        )

        # select defined fields
        self.assertEqual(
            -1,
            r1.age
        )
        self.assertEqual(
            -1,
            r1.age
        )

        # select non defined fields
        self.assertEqual(
            None,
            r1.optional_age
        )
        self.assertEqual(
            None,
            r1.optional_age
        )

        # change r1 ref
        r1.ref = "new"
        self.assertEqual("new", r1.id)

    def test_errors(self):
        # fixme: [GL] check new error system with fields
        # table definition error
        self.assertRaises(TableDefinitionError, AppErrDb)

        # prepare app
        db = AppSimpleDb()

        # no pk error
        with self.assertRaises(OExceptionCollection):
            db.simple.add(age=-1)

        # required argument
        with self.assertRaises(OExceptionCollection):
            db.simple.add(ref="a0")

        # non existing link
        with self.assertRaises(OExceptionCollection):
            db.pointing.add(pk=1, simple="@Simple:s1")

        # create records
        db.simple.add(ref="s1", age=1)
        db.simple.add(ref="s2", age=2)

        # non unique on add
        with self.assertRaises(OExceptionCollection):
            db.simple.add(ref="s1", age=3)

        # non unique on setitem
        with self.assertRaises(ValidationError):
            db.simple.one("s2").ref = "s1"

        # check getitem on table
        self.assertRaises(
            RecordDoesNotExistError,
            lambda: db.simple.one("s10")
        )

        # check one
        self.assertRaises(
            RecordDoesNotExistError,
            db.simple.one,
            lambda x: x.id == "s10"
        )

        # check multiple
        self.assertRaises(
            MultipleRecordsReturnedError,
            db.simple.one,
            lambda x: x.ref[0] == "s"
        )

    def test_links(self):
        # create db and populate
        db = building_standard_populate()

        # check that links work
        s = db.surface.one("s01")

        # record
        self.assertEqual(
            db.zone.one("z2"),
            s.minor_zone
        )

        # tuple
        self.assertEqual(
            (db.construction.one("c0"), db.construction.one("c1"), db.construction.one("c2")),
            s.constructions
        )

        # find all surfaces pointing on c0
        c0 = db.construction.one("c0")
        self.assertEqual(
            {"s00", "s01", "s02", "s10", "s11", "s12", "s20", "s21", "s22"},
            set(s.ref for s in c0.get_pointing_records().surface)
        )
        constructions_nb = dict((s, len(s.constructions)) for s in c0.get_pointing_records().construction)

        # delete c0
        c0.delete()

        # check surfaces have less constructions
        for s in constructions_nb:
            self.assertEqual(constructions_nb[s]-1, len(s.constructions))

        # get surface s01
        s01 = db.surface.one("s01")

        # see all pointed records
        self.assertEqual(
            {db.construction.one("c1"), db.construction.one("c2")},
            set(s01.get_pointed_records().construction)
        )
        self.assertEqual(
            {db.zone.one("z0"), db.zone.one("z2")},
            set(s01.get_pointed_records().zone)
        )

        # get surface s02
        s02 = db.surface.one("s02")

        # check link is in db and is activated
        link = s02._data["major_zone"]
        self.assertIn(link, db._dev_relations_manager)
        self.assertIsNotNone(link.source_record)
        self.assertIsNotNone(link.target_record)
        links_nb = len(db._dev_relations_manager)

        # change major zone (by ref)
        s02.major_zone = "z1"

        # check link was removed and new one was created
        self.assertNotIn(link, db._dev_relations_manager)
        self.assertEqual(links_nb, len(db._dev_relations_manager))

        # change major zone (by record)
        s02.major_zone = db.zone.one("z0")

        # remove all constructions (bach remove)
        db.construction.delete()

        # check surfaces have no more constructions
        self.assertEqual(
            0,
            sum((len(s.constructions) for s in db.surface))
        )

        # check ref modification
        z0 = db.zone.one("z0")
        z0.ref = "new_z0"
        self.assertEqual(
            s02.major_zone.ref,
            "new_z0"
        )

    def test_filtering(self):
        # create and populate db
        db = building_standard_populate()

        # simple filter
        self.assertEqual(
            {db.zone.one("z0"), db.zone.one("z1")},
            set(db.zone.select(lambda x: x.ref <= "z1"))
        )

        # complex filter
        z1 = db.zone.one("z1")
        self.assertEqual(
            {"s10", "s11", "s12"},
            {s.id for s in db.surface.select(lambda x: x.major_zone == z1)}
        )

    def test_multiple_databases(self):
        db1 = building_standard_populate()
        db2 = building_standard_populate()
        self.assertEqual(db1, db2)
        db1.zone.one("z1").ref = "new_z1"
        self.assertNotEqual(db1, db2)

    def test_export_and_load(self):
        # create and populate db
        db = building_standard_populate()

        # to_json, from_json and check equality
        with tempfile.TemporaryDirectory() as dir_path:
            # mono
            mono_path = os.path.join(dir_path, "mono.json")
            db.to_json(mono_path)
            db2 = AppBuildingDb.from_json(mono_path)
            self.assertEqual(db, db2)

            # multi
            multi_path = os.path.join(dir_path, "multi")
            db.to_json(multi_path, multi_files=True)
            db2 = AppBuildingDb.from_json(multi_path)
            self.assertEqual(db, db2)

    def test_dynamic_id(self):

        db1 = AppDynamicId()
        db1.base.add(ref="b1", age=15)
        db1.base.add(ref="b2", age=15)
        db1.dynamic_id.add(base="b1", weak_ref="dpk")
        db1.dynamic_id.add(base="b1", weak_ref="dpk")

        db2 = AppDynamicId()
        db2.base.add(ref="b1", age=15)
        db2.base.add(ref="b2", age=15)
        db2.dynamic_id.add(base="b1", weak_ref="dpk")
        db2.dynamic_id.add(base="b1", weak_ref="dpk")

        self.assertDictEqual(db1.to_json_data(), db2.to_json_data())
        self.assertEqual(db1, db2)

    def test_rename(self):
        db = building_standard_populate()
        links_before = db.surface.one("s00").get_pointed_records()
        db.surface.one("s00").ref = "s00_new"
        links_after = db.surface.one("s00_new").get_pointed_records()
        self.assertEqual(links_before, links_after)

    def test_pre_delete(self):
        db = building_standard_populate()
        s = db.surface.one("s00")
        z0 = s.major_zone
        self.assertEqual(z0.ref, "z0")
        self.assertEqual(s.minor_zone.ref, "z1")
        z0.delete()
        self.assertEqual(s.major_zone.ref, "z1")
        self.assertEqual(s.minor_zone, None)

    def test_post_save(self, **kwargs):
        db = building_standard_populate()
        s = db.surface.one("s00")
        self.assertEqual(s._post_save_counter, 1)
        s.update(ref="s00_new")
        self.assertEqual(s._post_save_counter, 2)
