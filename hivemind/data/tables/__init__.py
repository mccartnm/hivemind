"""
Copyright (c) 2019 Michael McCartney, Kevin McLoughlin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


from hivemind.data.abstract.table import _TableLayout
from hivemind.data.abstract.field import _Field


class TableDefinition(_TableLayout):
    """
    Table describing the migrations that we've gone through for our
    tables.
    """
    table_name = _Field.TextField()
    table_layout = _Field.JSONField()

    @classmethod
    def register_table(cls, interface, table: _TableLayout) -> None:
        """
        Based on the layout of the table, we have to convert everything
        to json
        """
        interface.create(TableDefinition,
                         table_name=table.db_name(),
                         table_layout=table.db_layout())


class NodeRegister(_TableLayout):
    """
    Table to identify nodes
    """
    name = _Field.TextField(unique=True)
    status = _Field.TextField()
    ip = _Field.TextField(default='127.0.0.1')
    port = _Field.IntField()

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)


class NodeMeta(_TableLayout):
    """
    Table to assign metadata to nodes. This makes

    """
    node = _Field.ForeignKeyField(NodeRegister)
    key = _Field.TextField()
    value = _Field.TextField(null=True)


RequiredTables = [
    [TableDefinition.db_name(), TableDefinition],
    [NodeRegister.db_name(), NodeRegister],
    [NodeMeta.db_name(), NodeMeta]
]