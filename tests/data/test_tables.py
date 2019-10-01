"""
Tests for basic table usage
"""
import unittest

from hivemind.data.abstract.table import _TableLayout
from hivemind.data.abstract.field import _Field


class TestTableBasics(unittest.TestCase):
    """
    Testing the table declaration component of the database
    """

    def test_declare_table(self):
        """
        Test some initial table declarations and confirm that
        we can use _Field subclasses only
        """
        class MyTable(_TableLayout):
            foo = _Field.IntField(default=1)
            baz = _Field.IntField(default=2)

        with self.assertRaises(TypeError):
            class MyTable(_TableLayout):
                foo = _Field.IntField(default=1)
                baz = _Field() # No can do
