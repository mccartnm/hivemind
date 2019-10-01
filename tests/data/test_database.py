"""
Tests for our physical database
"""

import unittest
import tempfile
import datetime

from hivemind.util.misc import temp_dir

from hivemind.data.abstract.table import _TableLayout
from hivemind.data.abstract.field import _Field

from hivemind.data.contrib.sqlite_interface import SQLiteInterface

def _sqlite_db_wrap(func):
    """
    Helper wrapper function for creating a file based database
    for temp use.
    """
    def test_wrapper(self):
        with temp_dir():
            dirpath = tempfile.mkdtemp()
            database_name = 'test_data'
            try:
                interface = SQLiteInterface()
                interface.connect(database_name)
                func(self, interface)
            finally:
                interface.disconnect()
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

        with self.assertRaises(TypeError):
            with interface.transaction:

                sql = f"""
                INSERT INTO {TestTable.db_name()} VALUES (
                    ?, 1, NULL
                )
                """
                interface.execute(sql, values=(_Field.IdField._build_id(),))

                raise TypeError('Superficial Error')

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
