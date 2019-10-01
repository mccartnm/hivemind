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

# --
Abstract inteface for the database api
"""
import sqlparse
from purepy import pure_virtual

from .field import FieldTypes
from .table import _TableLayout

from hivemind.util.misc import PV_SimpleRegistry
from hivemind.data.db import TransactionManager

class _DatabaseIntegration(metaclass=PV_SimpleRegistry):
    """
    Overload per database api
    """
    name = None

    # Overload where required to map base types (FieldTypes)
    # to their corresponding type in the database
    # e.x. { FieldTypes.JSON : 'jsonb' }
    mapped_types = {}


    def __init__(self):
        self.__tm = TransactionManager(self)

    # -- Virtual Interface

    @pure_virtual
    def connect(self, database_name, **kwargs):
        """
        Connect to a given database
        """
        raise NotImplementedError()


    @pure_virtual
    def disconnect(self):
        """
        Disconnect from a database
        """
        raise NotImplementedError()


    @pure_virtual
    def execute(self, query, values=None):
        """
        Execute a query
        """
        raise NotImplementedError()


    @pure_virtual
    def get_db_cursor(self):
        """
        Obtain a database cursor
        """
        raise NotImplementedError()


    # -- SQL Operations
    #    These may be overloaded at a per-integration level

    def begin_sql(self, term=False):
        return 'BEGIN' + (';' if term else '')


    def commit_sql(self, term=False):
        return 'COMMIT' + (';' if term else '')


    def rollback_sql(self, term=False):
        return 'ROLLBACK' + (';' if term else '')


    # -- Public Interface

    @property
    def transaction(self):
        return self.__tm


    def type_from_base(self, base_type) -> str:
        """
        Based on the FieldType that we're supplied, return the
        underlying type that the database understands
        :param base_type: The FieldType that we're working with
        :return: str
        """
        if base_type in self.mapped_types:
            return self.mapped_types[base_type][0]
        return base_type.value


    def create(self, cls, **kwargs):
        """
        Create an object in the database
        """
        values = []

        pk_column = None
        id_ = None

        # - Columns will maintain their db order
        for attr, column in cls.columns():
            if attr in kwargs:
                values.append(kwargs[attr])
                values[-1] = column.prep_for_db(values[-1])
            elif column.has_default:
                values.append(column.generate_default())
                values[-1] = column.prep_for_db(values[-1])
            else:
                values.append(None)

            if column.pk:
                pk_column = attr
                id_ = values[-1] # Breaks with auto incr! What should we do?

        sql = f'INSERT INTO {cls.db_name()} VALUES ('
        for i, v in enumerate(values):
            sql += '?' + (', ' if (i + 1) != len(values) else '')
        sql += ');'
        self.execute(sql, values=values)

        return self.query_for_one(cls, **{ pk_column : id_ })


    def query_for_one(self, cls, **kwargs):
        """
        Query for a single item
        :param cls: The _TableLayout that we're searching for
        :return: _TableLayout instance
        """
        return self.query(cls, **kwargs)[0]


    def query(self, cls, **kwargs):
        """
        Query for an object. We'll be making great strides to improve this
        but let's start with something simple.
        """
        values = []
        sql = f'SELECT * FROM {cls.db_name()}'

        filters = []
        for key, value in kwargs.items():
            filters.append(cls.db_column_name(key) + ' = ?')
            values.append(value)

        if filters:
            sql += ' WHERE (' + ' AND '.join(filters) + ')'
        sql += ';'

        output = []
        for row in self.execute(sql, tuple(values)).fetchall():
            output.append(cls._create_from_values(row))
        return output

    # -- Private Interface

    def _init_database(self):
        """
        
        """
        self._create_table(MigrationTable)
        self._create_table(DataStoreTable)


    def _create_table(self, table_layout: _TableLayout) -> None:
        """
        Create a table in our database. Raise an error if it already
        exists.
        :param table_layout: TableLayout subclass
        :return: None
        """
        sql = f'CREATE TABLE {table_layout.db_name()} ('

        columns = table_layout.columns()
        for i, column in enumerate(columns):

            attribute_name, column = column
            cname = table_layout.db_column_name(attribute_name)
            dbt = column.db_type(self)

            sql += f'  "{cname}" ' + column.definition_sql(dbt)
            if i + 1 != len(columns):
                sql += ', '

        sql += ')'

        # with self.__tm: # Tables cannot be created in a transaction
        self.execute(sql)
