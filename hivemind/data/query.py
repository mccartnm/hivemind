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
from __future__ import annotations

import functools

from purepy import PureVirtualMeta, pure_virtual, override

from .exceptions import MultipleResultsError

class QueryOperators(object):
    """
    Initial operators that we support no matter what. This
    doesn't mean that all fields will be able to utilize
    all operators, but we can at least build the SQL for it.

    We'll probably have to keep digging on this.
    """
    basic_operators = {
        'equals'     : ('= ?', True),
        'not_equals' : ('<> ?', True),
        'lt'         : ('< ?', True),
        'lt_or_eq'   : ('<= ?', True),
        'gt'         : ('> ?', True),
        'gt_or_eq'   : ('>= ?', True),
        'startswith' : ("LIKE ?", True, lambda x: x + "%"),
        'endswith'   : ("LIKE ?", True, lambda x: "%" + x),
        'contains'   : ("LIKE ?", True, lambda x: "%" + x + "%"),
        'one_of'     : ('IN ?', True),
        'not_one_of' : ('NOT IN ?', True),
        'is_null'    : ('IS NULL', False),
        'is_not_null': ('IS NOT NULL', False),
    }


class _QueryItemBase(object, metaclass=PureVirtualMeta):
    """
    Abstract query object that can contain both filter and logic
    operators
    """
    def __init__(self):
        pass

    @pure_virtual
    def sql(self, interface) -> tuple:
        """
        Overload to make sure we can produce the query
        """
        raise NotImplementedError()


class _QueryFilterGroup(_QueryItemBase):
    """
    SQL Grouping (AND, OR) base to centralize the logic
    """
    op = None

    def __init__(self, *filters, **eq_filters):
        _QueryItemBase.__init__(self)
        self._filters = filters

        for field_name, value in eq_filters.items():
            field = self._cls.get_field(field_name)
            self._filters.append(field.equals(value))        


    @override()
    def sql(self, interface) -> tuple:
        """
        Based on the op, we want to wrap our filters as required
        """
        output = '('

        filter_sql = []
        values = []
        for filter_ in self._filters:
            this_filter_sql, this_filter_values = filter_.sql(interface)
            filter_sql.append(this_filter_sql)
            values.extend(list(this_filter_values))

        output += self.op.join(filter_sql)
        output += ')'
        return output, values



class QueryAnd(_QueryFilterGroup):
    op = ' AND '


class QueryOr(_QueryFilterGroup):
    op = ' OR '


class QueryFilter(_QueryItemBase):
    """
    Specific query filter
    """
    def __init__(self, table, field, operator, value=None):
        _QueryItemBase.__init__(self)

        self._table = table
        self._field = field
        self._operator = operator
        self._value = value


    def __and__(self, other):
        return QueryAnd(self, other)


    def __or__(self, other):
        return QueryOr(self, other)


    @classmethod
    def factory(cls, table, field, operator):
        """
        :return: A callable that constructs a QueryFilter given a value
        """
        return functools.partial(cls, table, field, operator)


    @override()
    def sql(self, interface) -> tuple:
        """
        Build the proper SQL in order to 
        """
        db_col = self._table.db_column_name(self._field.field_name)
        values = tuple()

        expect_val = True
        comp = None

        op = self._operator # ...
        if self._operator in interface.overloaded_operators:
            op, expect_val, *comp = interface.overloaded_operators[self._operator]

        elif self._operator in QueryOperators.basic_operators:
            op, expect_val, *comp = QueryOperators.basic_operators[self._operator]

        elif hasattr(self._field, self._operator):
            op, expect_val, *comp = getattr(self._field, self._operator)()

        if expect_val and self._value:
            v = self._value
            if comp:
                v = comp[0](v)

            values = (self._field.prep_for_db(v),)

        return (
            f'\"{self._table.db_name()}\".\"{db_col}\" {op}',
            values
        )


class Query(object):
    """
    Query utilities for the data layer. This is where we can construct
    and insert filters as required for various objects. Currently, we
    don't have any kind of caching but that could be arranged.

    This object supports the lazy loading of items because, while building
    it, unless a specific execution function is called (e.g. count()),
    it's just a filter container

    .. code-block:: python

        # database is a _DatabaseInterface instance
        my_query = database.new_query(MyTable)

        # get all objects
        all_my_table_objects = my_query.objects()

        # get the number of objects
        my_table_count = my_query.count()

        # Get a filtered query
        filtered_query = my_query.filter(MyTable.some_field.equals("foo"))

        # Basic equalative filtering on local fields
        quick_local_query = my_query.filter(some_field="foo")

    """
    AND = QueryAnd
    OR = QueryOr

    def __init__(self, cls, filters=None, database=None, **eq_filters):

        self._cls = cls
        self._filters = filters or []

        for field_name, value in eq_filters.items():
            field = self._cls.get_field(field_name)
            self._filters.append(field.equals(value))

        self._database = database


    def get_fiters(self) -> list:
        """
        :return: All filters within this query
        """
        return self._filters


    def filter(self, query_item: (_QueryItemBase, None) = None, **eq_filters) -> Query:
        """
        Filter this query a little bit
        :param query_item: The query filter that we want to add
        """
        return Query(
            self._cls,
            filters=self._filters + ([query_item] if query_item else []),
            database=self._database,
            **eq_filters
        )


    def sql(self) -> tuple:
        """
        Obtain the sql statement. This is augmented based on the
        database type.
        :return: tuple(sql_string, values)
        """
        output = ''
        values = tuple()

        if len(self._filters) > 1:
            output, values = self.AND(*self._filters).sql(self._database)
        elif self._filters:
            output, values = self._filters[0].sql(self._database)
        return (output, values)

    # -- Execution Queries

    def values(self, *fields) -> list:
        """
        Given a set of fields to lookup, snag the values of them and
        return them in the order listed
        """
        sql_string, values = self.sql()
        return self._database.to_values(
            self._cls,
            sql_string,
            values,
            fields
        )


    def objects(self) -> list:
        """
        Use this query to construct instances of the query class.
        :return: list[_TableLayout instances]
        """
        sql_string, values = self.sql()
        return self._database.to_objects(
            self._cls,
            sql_string,
            values
        )

    def get(self) -> _TableLayout:
        """
        Obtain a single item at the end of this query. Raise an error
        if it does not exist _or_ there are more than one result
        """
        res = self.objects()
        if len(res) == 0:
            raise self._cls.DoesNotExist(
                f'Cannot find matching {self._cls.__name__}'
            )
        elif len(res) > 1:
            raise MultipleResultsError(
                f'More than 1 {self._cls.__name__} found! (Got: {len(res)})'
            )
        else:
            return res[0]


    def get_or_null(self) -> (_TableLayout, None):
        """
        Obtain either the object or return None if it cannot be found.
        We still raise an exception if multiple results come back
        """
        try:
            return self.get()
        except self._cls.DoesNotExist:
            return None


    # -- Algorithms

    def _run_algo(self, algo: str, field: str = None) -> (int, float):
        """
        Run a simple math
        :param algo: The algorithm to execute
        :return: int
        """
        field_name = field or self._cls.pk()
        table = self._cls.db_name()
        sql_string, values = self.sql()
        field_name = f'"{table}"."{field_name}"'

        return self._database.execute(
            f'SELECT {algo}({field_name}) FROM {table} WHERE {sql_string}',
            values
        ).fetchone()[0]


    def count(self) -> int:
        """
        Execute the query and return the number of items
        in the results.
        :reutrn: Number of rows matching the query
        """
        return self._run_algo('COUNT')


    def average(self, field=None) -> (int, float):
        """
        Average the values together
        """
        return self._run_algo('AVG', field)


    def sum(self, field=None) -> (int, float):
        """
        Add all values together
        """
        return self._run_algo('SUM', field)
