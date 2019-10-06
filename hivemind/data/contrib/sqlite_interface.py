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

import json
import sqlite3
import sqlparse
from decimal import Decimal
from datetime import datetime, date

from purepy import override

from hivemind.data.abstract.field import FieldTypes
from hivemind.data.abstract.scafold import _DatabaseIntegration
from hivemind.data.exceptions import DatabaseError, IntegrityError, OperationalError


class SQLiteInterface(_DatabaseIntegration):
    """
    sqlite interface. A Basic, but quick and easy interface.
    """
    name = 'sqlite'

    mapped_types = {

        # -- Numeric
        FieldTypes.TINYINT : ('INTEGER',),
        FieldTypes.SMALLINT : ('INTEGER',),
        FieldTypes.INT : ('INTEGER',),
        FieldTypes.BIGINT : ('INTEGER',),
        FieldTypes.DECIMAL: ('DECIMAL', Decimal, str),
        FieldTypes.FLOAT: ('REAL',),
        FieldTypes.REAL: ('REAL',),

        # -- DATETIME
        #
        # python auto-exposes a date and timestamp converter
        # when using sqlite3
        #
        FieldTypes.DATE: ('DATE',),
        FieldTypes.TIME: ('TEXT',), # ?? Needs work
        FieldTypes.DATETIME: ('TIMESTAMP',),

        # -- Characters
        FieldTypes.VARCHAR: ('TEXT',),
        FieldTypes.TEXT: ('TEXT',),

        FieldTypes.JSON: ('JSON', None, json.loads)
    }

    def __init__(self):
        _DatabaseIntegration.__init__(self)
        self.__db = None


    @override()
    def connect(self, **kwargs):
        """
        Connect to a single local file
        """
        database_name = kwargs.get('name', 'default')

        if not database_name == ':memory:':
            if not database_name.endswith('.db'):
                database_name += '.db'

        self.__db = sqlite3.connect(
            database_name,
            detect_types=sqlite3.PARSE_DECLTYPES # To support JSON
        )

        # We control the transactions ourselves
        self.__db.isolation_level = None

        # We have to enable FKs
        self.__db.execute("PRAGMA foreign_keys = 1;")


    @override()
    def disconnect(self):
        """
        Disconnect from the local connection
        """
        if not self.__db:
            return
        self.__db.close()


    @override()
    def execute(self, query, values=None):
        """
        Raw, low level query interface
        """
        if self.transaction.active:
            cursor = self.transaction.active
        else:
            cursor = self.get_db_cursor()
        if values is None:
            values = tuple()

        # statements = sqlparse.split(query)
        # print ('-- sql')
        # for statement in statements:
        #     print (sqlparse.format(statement, reindent=True, keyword_case='upper'))
        # print ("_values:")
        # __import__('pprint').pprint(values)
        # print ('-------------------------------------')

        try:
            return cursor.execute(query, values)
        except sqlite3.IntegrityError as e:
            raise IntegrityError(str(e))
        except sqlite3.OperationalError as e:
            raise OperationalError(str(e))
        except Exception as e:
            raise DatabaseError(str(e))


    @override()
    def get_db_cursor(self):
        """
        From our connection, snag a cursor
        """
        return self.__db.cursor()


    @override()
    def get_table_names(self):
        result = self.execute("SELECT * FROM sqlite_master WHERE type='table'")
        output = []
        for row in result.fetchall():
            output.append(row[2])
        return output


    def definition_sql(self, column):
        """
        Based on the column provided, return the SQL for building a table with
        a 
        """
        dbt = self.type_from_base(column.base_type)
        column_name = column.db_name()

        if dbt == 'FK':
            # -- Special handle for FK
            fk_table_name = column.related_class.db_name()
            fk_pk_column_name = column.related_class.pk()

            sql, _ = super().definition_sql(column)

            return sql, [
                f'CONSTRAINT fk_{column_name}_to_{fk_pk_column_name} '
                f'FOREIGN KEY({column_name}) '
                f'REFERENCES {fk_table_name}({fk_pk_column_name}) '
                f'ON DELETE {column.deletion_policy}'
            ]

        # Return the default impl if nothing else matches
        return super().definition_sql(column)


#
# Define any types in sqlite that we want to map
#
for field_type, typedef in SQLiteInterface.mapped_types.items():
    if len(typedef) > 2:
        name, to_db, from_db = typedef

        if to_db:
            sqlite3.register_adapter(name, to_db)

        if from_db:
            sqlite3.register_converter(name, from_db)
