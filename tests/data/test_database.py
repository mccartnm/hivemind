"""
Tests for our physical database
"""

import unittest
import tempfile
import datetime

from hivemind.util.misc import temp_dir

from hivemind.data.abstract.table import _TableLayout
from hivemind.data.abstract.field import _Field
from hivemind.data.exceptions import IntegrityError

from hivemind.data.contrib.sqlite_interface import SQLiteInterface

def _sqlite_db_wrap(func):
    """
    Helper wrapper function for creating a file based database
    for temp use.
    :param func: The test function that we're going to call
    :return: wrapped function
    """
    def test_wrapper(self):
        """
        The internal wrapping function. Will generate a
        sqlite database for messing around
        :param self: The instance of the TestCase that's passed to the
                     test function when running
        """
        dirpath = tempfile.mkdtemp()
        database_name = ':memory:'
        try:
            interface = SQLiteInterface()
            interface.connect(name=database_name)
            func(self, interface)
        finally:
            interface.disconnect() # Before we cleanup
    return test_wrapper


class TestTable(_TableLayout):
    """
    Table that we test with
    """
    foo = _Field.IntField(default=1)
    bar = _Field.IntField(null=True)


class TestDatabaseBasics(unittest.TestCase):

    @_sqlite_db_wrap
    def test_database_basic_table_work(self, interface):
        """
        Test that we can in fact bring up a simple database
        """
        interface.execute('CREATE TABLE foo ( bar int );')
        values = (2, 3, 4, 5)
        with interface.transaction:
            interface.execute('INSERT INTO foo (bar) VALUES (?), (?), (?), (?)',
                              values=values)
        result = interface.execute('SELECT * FROM foo')
        result = [r[0] for r in result]
        self.assertTrue(all(r in values for r in result))


    @_sqlite_db_wrap
    def test_table_to_db(self, interface):
        """
        Test that we can translate from a _TableLayout to a table
        in the database
        """
        interface._create_table(TestTable)

        res = interface.execute("SELECT * FROM sqlite_master WHERE type='table'")
        output = res.fetchall()
        self.assertEqual(len(output), 1)
        self.assertTrue(TestTable.db_name() in output[0])


    @_sqlite_db_wrap
    def test_transactions_working(self, interface):
        """
        Test that a failed transaction rolls back
        """
        interface._create_table(TestTable)

        class CustomExcept(Exception):
            """ Exception we can be sure we're not hitting in the test """
            pass

        with self.assertRaises(CustomExcept):
            with interface.transaction:

                sql = f"""
                INSERT INTO {TestTable.db_name()} VALUES (
                    ?, 1, NULL
                )
                """
                interface.execute(sql, values=(_Field.IdField._build_id(),))

                # Test that the item exists
                interface.new_query(TestTable, foo=1).get()

                raise CustomExcept('Superficial Error')

        self.assertTrue(interface.execute(
            f'SELECT * FROM {TestTable.db_name()}'
        ).fetchall() == [])


    @_sqlite_db_wrap
    def test_date_and_timestamp_fields(self, interface):
        """
        Make sure simple translations are possible
        """

        class DateTableTest(_TableLayout):
            mydate = _Field.DateField(pk=True)

        interface._create_table(DateTableTest)

        date = datetime.date.today()
        interface.execute(
            'INSERT INTO {} VALUES (?)'.format(
                DateTableTest.db_name()
            ), values=(date,)
        )

        interface.execute(f'DROP TABLE {DateTableTest.db_name()}')

        class DatetimeTableTest(_TableLayout):
            mydatetime = _Field.DatetimeField(pk=True)

        interface._create_table(DatetimeTableTest)

        datestamp = datetime.datetime.now()
        interface.execute(
            'INSERT INTO {} VALUES (?)'.format(
                DatetimeTableTest.db_name()
            ), values=(datestamp,)
        )

        from_db = interface.execute(
            'SELECT * FROM {}'.format(DatetimeTableTest.db_name())
        ).fetchone()[0]

        self.assertEqual(type(datestamp), type(from_db))
        self.assertEqual(datestamp, from_db)


    @_sqlite_db_wrap
    def test_json_field(self, interface):

        class JsonThing(_TableLayout):
            data = _Field.JSONField()

        interface._create_table(JsonThing)

        d = {"foo": "bar"}
        instance = interface.create(
            JsonThing,
            data=d
        )

        self.assertEqual(instance.data, d)


    @_sqlite_db_wrap
    def test_basic_query(self, interface):

        class MyTable(_TableLayout):
            numba = _Field.IntField()
            foo = _Field.TextField()

        interface._create_table(MyTable)

        interface.create(MyTable, numba=1, foo='bar')
        interface.create(MyTable, numba=2, foo='baz')
        interface.create(MyTable, numba=3, foo='bloog')
        interface.create(MyTable, numba=4, foo='floog')

        base_query = interface.new_query(MyTable)

        count_query = base_query.filter(MyTable.foo.equals('bar'))
        self.assertEqual(count_query.count(), 1)

        count_query = base_query.filter(MyTable.foo.startswith('b'))
        self.assertEqual(count_query.count(), 3)

        count_query = base_query.filter(MyTable.foo.endswith('oog'))
        self.assertEqual(count_query.count(), 2)

        count_query = base_query.filter(
            base_query.OR(
                MyTable.foo.startswith('b'),
                MyTable.foo.equals('floog'),
            )
        )
        self.assertEqual(count_query.count(), 4)
        self.assertEqual(count_query.average('numba'), 2.5)

        test_bitwise = base_query.filter(
            MyTable.foo.startswith('b') | MyTable.foo.equals('floog')
        )

        self.assertEqual(count_query.sql(), test_bitwise.sql())

        # Ha! This works
        objs = count_query.objects()
        self.assertEqual(len(objs), 4)
        self.assertTrue(
            all(isinstance(x, _TableLayout) for x in objs)
        )

        # Quick querying
        query = interface.new_query(MyTable, numba=1)
        self.assertEqual(query.count(), 1)

        query = interface.new_query(MyTable).filter(numba=1)
        self.assertEqual(query.count(), 1)


    @_sqlite_db_wrap
    def test_integrity_basics(self, interface):
        """
        Test that we fail when trying to create the same value
        on a unique field
        """
        class MyTable(_TableLayout):
            numba = _Field.IntField(unique=True)
            foo = _Field.TextField()

        interface._create_table(MyTable)
        interface.create(MyTable, numba=1, foo='blarg')

        with self.assertRaises(IntegrityError):
            # numba == 1 already exists
            interface.create(MyTable, numba=1, foo='bloog')

        with self.assertRaises(IntegrityError):
            # Default is NOT NULL
            interface.create(MyTable, numba=2)

        with self.assertRaises(IntegrityError):
            # Default is NOT NULL
            interface.create(MyTable, numba=2, foo=None)

        class NullOk(_TableLayout):
            blarg = _Field.TextField(null=True)

        interface._create_table(NullOk)
        interface.create(NullOk)

        query = interface.new_query(NullOk).filter(
            NullOk.blarg.is_null()
        )
        self.assertEqual(query.count(), 1)


    @_sqlite_db_wrap
    def test_delete_basics(self, interface):
        """
        Test that we can delete simple items
        """
        interface._create_table(TestTable)

        instance = interface.create(TestTable, foo=2, bar='blarg')
        query = interface.new_query(TestTable, foo=2)

        self.assertEqual(query.count(), 1)
        interface.delete(instance)
        self.assertEqual(query.count(), 0)


    @_sqlite_db_wrap
    def test_save_basics(self, interface):
        """
        Test that we can do a humble save operation
        """
        interface._create_table(TestTable)
        instance = interface.create(TestTable, foo=2, bar='blarg')

        self.assertEqual(instance.foo, 2)

        instance.foo = 5
        interface.save(instance)

        query = interface.new_query(TestTable, bar='blarg')
        self.assertEqual(query.get().foo, 5)


    @_sqlite_db_wrap
    def test_fk_basics(self, interface):
        """
        Test that we can handle 
        """
        class SomeRelation(_TableLayout):
            test = _Field.ForeignKeyField(TestTable)
            foo = _Field.TextField(null=True)

        interface._create_table(TestTable)
        interface._create_table(SomeRelation)

        test_instance = interface.create(TestTable, foo=123)

        interface.create(SomeRelation, test=test_instance)

        query = interface.new_query(SomeRelation, test=test_instance)

        self.assertEqual(query.get().foo, None)

        self.assertEqual(query.get().test, test_instance)


    @_sqlite_db_wrap
    def test_get_or_create(self, interface):
        """
        The get_or_create method is very useful for assuring items exist
        """
        interface._create_table(TestTable)

        inst, created = interface.get_or_create(
            TestTable,
            foo = 1,
            bar = 2
        )

        self.assertTrue(created)
        self.assertTrue(isinstance(inst, TestTable))

        _, created = interface.get_or_create(
            TestTable,
            foo = 1,
            bar = 2
        )

        self.assertFalse(created)


    @_sqlite_db_wrap
    def test_unqiue_contraints(self, interface):
        """
        Multiple keys having a unique constraint
        """
        class UniqueTogether(_TableLayout):
            foo = _Field.IntField()
            bar = _Field.IntField()

            @classmethod
            def unqiue_constraints(cls):
                return (('foo', 'bar'),)

        interface._create_table(UniqueTogether)

        inst1 = interface.create(
            UniqueTogether,
            foo = 1,
            bar = 2
        )

        # This should be fine
        interface.create(
            UniqueTogether,
            foo = 1,
            bar = 3   # Different
        )

        with self.assertRaises(IntegrityError):
            interface.create(
                UniqueTogether,
                foo = 1,
                bar = 2
            )

