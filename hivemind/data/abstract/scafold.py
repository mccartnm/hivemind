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
Abstract interface for the database api
"""
import sqlparse
from purepy import pure_virtual

from .field import FieldTypes, _Field
from .table import _TableLayout

from hivemind.util.misc import PV_SimpleRegistry, cd
from hivemind.data.db import TransactionManager
from hivemind.data.query import Query


class _DatabaseIntegration(metaclass=PV_SimpleRegistry):
    """
    Overload per database api
    """
    name = None

    # Overload where required to map base types (FieldTypes)
    # to their corresponding type in the database
    # e.x. { FieldTypes.JSON : 'jsonb' }
    mapped_types = {}

    # Overload where required to map from query filters to
    # their respective items
    overloaded_operators = {}


    def __init__(self):
        self.__tm = TransactionManager(self)

    # -- Virtual Interface

    @pure_virtual
    def connect(self, **kwargs):
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


    @pure_virtual
    def get_table_names(self):
        """
        Obtain known table names
        """
        raise NotImplementedError()


    def to_values(self,
                  table: _TableLayout,
                  sql: str,
                  values: tuple,
                  fields: list) -> list:
        """
        Given a set of fields (_Field | str), obtain all the values
        for any rows that match our search
        """
        output = []
        table_name = table.db_name()

        full_field_names = []
        fiels_names_to_zip = []

        for field in fields:
            if isinstance(field, str):
                full_field_names.append(f'"{table_name}"."{field}"')
                fiels_names_to_zip.append(field)

            elif isinstance(field, _Field):
                fdb_name = table.db_column_name(field)
                full_field_names.append(f'"{table_name}"."{fdb_name}"')
                fiels_names_to_zip.append(
                    f"{table.__name__}.{field.field_name}"
                )

            else:
                raise TypeError('field must be _Field or str')

        full_sql = (f'SELECT {", ".join(full_field_names)} '
                    f'FROM {table_name}')

        if sql:
            full_sql += ' WHERE ' + sql

        for row in self.execute(full_sql, values):
            output.append(dict(zip(fiels_names_to_zip, row)))
        return output


    def to_objects(self, table: _TableLayout, sql: str, values: tuple) -> list:
        """
        Given a sql statement and the values that we want to
        apply to our query, execute the statement and construct
        logical objects out of the results.
        """
        objects = []
        full_sql = 'SELECT * FROM ' + table.db_name()

        if sql:
            full_sql += ' WHERE ' + sql

        for row in self.execute(full_sql, values):
            objects.append(table._create_from_values(self, row))
        return objects


    # -- SQL Operations
    #    These may be overloaded at a per-integration level

    def begin_sql(self, term=False):
        return 'BEGIN' + (';' if term else '')


    def commit_sql(self, term=False):
        return 'COMMIT' + (';' if term else '')


    def rollback_sql(self, term=False):
        return 'ROLLBACK' + (';' if term else '')


    def definition_sql(self, column):
        """
        :return: The default SQL required to build a column. Overload this
                 for custom fields or select relationship fields.
        """
        sql = f'{column.db_name()} {column.db_type(self)}' + \
            (' PRIMARY KEY' if column._pk else '') + \
            (' UNIQUE' if column._unique else '') + \
            ('' if column._null else ' NOT NULL')

        if column._default and not callable(column._default):
            sql += f' DEFAULT ({column.default_for_sql()})'

        return sql, []

    # -- Public Interface

    @classmethod
    def start_database(cls, database_settings):
        database_type = database_settings.get('type')
        if database_type not in cls._simple_registry:
            raise ValueError(f'The database integration: {database_type} not found.')

        interface = cls._simple_registry[database_type]()
        interface.connect(**database_settings)
        return interface


    @property
    def transaction(self):
        """
        :return: The TransactionManager that goes along with this database
        """
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
                values.append(column.prep_for_db(kwargs[attr]))
            elif column.has_default:
                values.append(column.prep_for_db(
                    column.generate_default()
                ))
            else:
                values.append(None)

            if column.pk:
                pk_column = attr
                # Breaks with db auto incr! What should we do?
                id_ = values[-1]

        sql = f'INSERT INTO {cls.db_name()} VALUES ('
        for i, v in enumerate(values):
            sql += '?' + (', ' if (i + 1) != len(values) else '')
        sql += ');'
        self.execute(sql, values=values)

        # -- We need better error handling
        return self.new_query(
            cls, getattr(cls, pk_column).equals(id_)
        ).objects()[0]


    def get_or_create(self, cls, **kwargs) -> tuple:
        """
        Get an instance of an object that matches the kwargs or, if it doesn't
        exist, create it and return that instance.

        :return: tuple(cls instance, created:bool)
        """
        try:
            return self.new_query(cls, **kwargs).get(), False
        except cls.DoesNotExist:
            return self.create(cls, **kwargs), True


    def delete(self, instance) -> None:
        """
        Destroy an item in the database
        :param instance: The item to remove
        """
        table_name = instance.db_name()
        pk_column = instance.pk()
        pk_field = instance.pk_field()

        sql = f'DELETE FROM "{table_name}" WHERE "{pk_column}" = ?'
        self.execute(sql, values=(instance.pk_value,))


    def save(self, instance):
        """
        Based on the changes to the instance, we save the respective values.
        """
        table_name = instance.db_name()
        pk_column = instance.pk()
        pk_field = instance.pk_field()

        db_instance = self.new_query(
            instance.__class__,
            **{pk_field.field_name : instance.pk_value}
        ).get()

        fields_to_update = []
        values = []
        for attr, column in instance.columns():
            db_value = getattr(db_instance, attr)
            this_value = getattr(instance, attr)

            if db_value != this_value:
                fields_to_update.append(f'"{column.db_name()}" = ?')
                values.append(column.prep_for_db(this_value))

        set_sql = ', '.join(fields_to_update)
        values.append(instance.pk_value)

        sql = f'UPDATE "{table_name}" SET {set_sql} WHERE "{pk_column}" = ?'
        self.execute(sql, values=tuple(values))


    def new_query(self, cls: _TableLayout, *filters, **eq_filters) -> Query:
        """
        Start a new Query on a given class
        :param cls: _TableLayout that we're looking to query
        """
        return Query(cls,
                     filters=filters,
                     database=self,
                     **eq_filters)

    # -- Private Interface

    def _create_table(self, table_layout: _TableLayout) -> None:
        """
        Create a table in our database. Raise an error if it already
        exists.
        :param table_layout: TableLayout subclass
        :return: None
        """
        sql = f'CREATE TABLE {table_layout.db_name()} ('

        columns = table_layout.columns()
        column_sql = []
        all_constraints = []
        for i, column in enumerate(columns):

            attr, column = column

            col_sql, constraints = self.definition_sql(column)
            column_sql.append(col_sql)
            all_constraints.extend(constraints)

        for constrain_together_fields in table_layout.unqiue_constraints():
            field_names = [table_layout.get_field(f).db_name() for f in constrain_together_fields]
            all_constraints.append(f'UNIQUE({", ".join(field_names)})')

        sql += ', '.join(column_sql)

        if all_constraints:
            sql += ', ' + ', '.join(all_constraints)

        sql += ')'

        # import sqlparse
        # statements = sqlparse.split(sql)
        # print ('-- sql')
        # for statement in statements:
        #     print (sqlparse.format(statement, reindent=True, keyword_case='upper'))

        self.execute(sql)
